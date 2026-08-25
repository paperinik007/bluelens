from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Union

from . import criteria, evidence, metrics
from .orchestrator import CommandRunner, default_command_runner, run_test_case
from .schema import TestCase, Verdict
from .serialization import transcript_from_dict, verdict_from_dict

# Only agent/detector are part of the sequence vocabulary — egress-proxy is
# shared infrastructure, never managed by a sequence (design doc, "Meccanica
# Docker per open/close").
KNOWN_CONTAINERS = ("agent", "detector")


@dataclass(frozen=True)
class OpenStep:
    containers: tuple[str, ...]


@dataclass(frozen=True)
class CommandStep:
    case_id: str
    counts_toward_metric: bool


@dataclass(frozen=True)
class CloseStep:
    containers: tuple[str, ...]


SequenceStep = Union[OpenStep, CommandStep, CloseStep]

OPEN_CLOSE_TIMEOUT_S = 30.0


def _open_container(service: str, run_command: CommandRunner) -> None:
    """Auto-healing open (design doc, 'Meccanica Docker per open/close';
    council-risk finding, crash dell'orchestratore a metà sequenza): the
    best-effort rm before up recovers from any residual state regardless of
    what happened before it — a crashed prior run included, not only the
    path where everything went cleanly."""
    run_command(["docker", "compose", "rm", "-f", "-s", "-v", service], b"", OPEN_CLOSE_TIMEOUT_S)
    run_command(["docker", "compose", "up", "-d", service], b"", OPEN_CLOSE_TIMEOUT_S)


def _close_container(service: str, run_command: CommandRunner) -> None:
    """Real removal, never a bare stop (design doc, 'Meccanica Docker per
    open/close'): rm -f -s -v deletes the container's writable layer by
    Docker's own command contract — that contract is the guarantee, not an
    empirical check of what's left on disk.

    The CommandResult's returncode is not checked here — same best-effort
    discipline orchestrator.py already applies to its own cleanup calls
    (the pkill fallbacks). A failed rm/up is not silently hidden forever: a
    container that's still broken will make the next docker compose exec in
    the sequence fail too, which run_test_case classifies as an infra error
    and the circuit breaker will trip on within a bounded number of
    commands (council-risk finding, this plan's checkpoint)."""
    run_command(["docker", "compose", "rm", "-f", "-s", "-v", service], b"", OPEN_CLOSE_TIMEOUT_S)


def validate_sequence(steps: list[SequenceStep], known_case_ids: set[str]) -> None:
    """Fail-fast static validation (design doc, 'Validazione statica') — a
    scan over `steps` tracking which containers are open, before any Docker
    or LLM call is issued. Mirrors CASE_ID_PATTERN/validate_unique_case_ids
    in dataset.py: cheap, structural checks first, never a wasted real call
    on a malformed sequence."""
    open_containers: set[str] = set()
    for step in steps:
        if isinstance(step, OpenStep):
            already_open = open_containers & set(step.containers)
            if already_open:
                raise ValueError(f"open step re-opens already-open containers: {sorted(already_open)}")
            open_containers |= set(step.containers)
        elif isinstance(step, CommandStep):
            missing = set(KNOWN_CONTAINERS) - open_containers
            if missing:
                raise ValueError(
                    f"command step {step.case_id!r} requires containers not open: {sorted(missing)}"
                )
            if step.case_id not in known_case_ids:
                raise ValueError(f"command step references unknown case_id: {step.case_id!r}")
        elif isinstance(step, CloseStep):
            not_open = set(step.containers) - open_containers
            if not_open:
                raise ValueError(f"close step closes containers not open: {sorted(not_open)}")
            open_containers -= set(step.containers)
        else:
            raise TypeError(f"unknown sequence step type: {type(step).__name__}")
    if open_containers:
        raise ValueError(f"sequence ends with containers still open: {sorted(open_containers)}")


@dataclass
class BatchResult:
    cases: list[TestCase]
    verdicts: list[Verdict]
    total_count: int
    executed_count: int
    breaker_tripped: bool
    last_infra_rationale: Optional[str] = None
    transcript_conversion_failure_count: int = 0
    verdict_conversion_failure_count: int = 0
    metric_cases: list[TestCase] = field(default_factory=list)
    metric_verdicts: list[Verdict] = field(default_factory=list)
    transcript_unusable: dict[str, str] = field(default_factory=dict)


def _agent_input(case: TestCase) -> dict:
    """Reduced dict sent to run_test_case(): only case_id and the seed turn's
    content — never label/technique_target/rationale, and never the Gap 18
    ground-truth fields attack_success_criteria/attack_succeeded (design doc
    decision 2, Plan 4). The dict is built by whitelist, so a new TestCase
    field is excluded by construction; this enumeration is documentation of
    that, not the mechanism enforcing it."""
    seed = case.transcript.turns[0]
    return {
        "case_id": case.case_id,
        "transcript": {"turns": [{"seq": seed.seq, "role": seed.role, "content": seed.content, "tool_call": None}]},
    }


def _fallback_verdict(case_id: str, exc: Exception) -> Verdict:
    return Verdict(
        case_id=case_id,
        tool_name="agentic_threat_detection",
        status="error",
        rationale=f"dict-to-dataclass conversion failed: {type(exc).__name__}",
    )


def _append_jsonl(path: Path, obj: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj) + "\n")


def execute_sequence(
    steps: list[SequenceStep],
    dataset_by_case_id: dict[str, TestCase],
    run_output_dir: Path,
    *,
    agent_timeout_s: float = 120.0,
    detector_timeout_s: float = 180.0,
    breaker_threshold: int = 3,
    api_key: str = "",
    run_test_case_fn: Callable[..., dict] = run_test_case,
    collect_case_evidence_fn: Callable = evidence.collect_case_evidence,
    collect_thin_proxy_log_fn: Callable = evidence.collect_thin_proxy_log,
    run_command: CommandRunner = default_command_runner,
) -> BatchResult:
    """Drive `steps` through open/command/close (design doc, 'Esecuzione') —
    the sequence-aware core that execute_batch (run_batch.py) generates its
    default whole-dataset sequence on top of. Never imports detector_adapter
    or aidr, same boundary run_test_case already declares."""
    validate_sequence(steps, set(dataset_by_case_id.keys()))

    raw_dir = run_output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    verdicts_path = run_output_dir / "verdicts.jsonl"
    verdicts_path.write_text("", encoding="utf-8")

    cases: list[TestCase] = []
    verdicts: list[Verdict] = []
    metric_cases: list[TestCase] = []
    metric_verdicts: list[Verdict] = []
    transcript_unusable: dict[str, str] = {}
    open_containers: set[str] = set()
    consecutive_infra = 0
    last_infra_rationale: Optional[str] = None
    breaker_tripped = False
    transcript_conversion_failure_count = 0
    verdict_conversion_failure_count = 0
    total_count = sum(1 for step in steps if isinstance(step, CommandStep))

    try:
        for step_index, step in enumerate(steps):
            if isinstance(step, OpenStep):
                for service in step.containers:
                    _open_container(service, run_command)
                    open_containers.add(service)
                continue

            if isinstance(step, CloseStep):
                for service in step.containers:
                    _close_container(service, run_command)
                    open_containers.discard(service)
                continue

            ground_truth = dataset_by_case_id[step.case_id]
            case_id = ground_truth.case_id
            result = run_test_case_fn(
                _agent_input(ground_truth),
                command_index=step_index,
                agent_timeout_s=agent_timeout_s,
                detector_timeout_s=detector_timeout_s,
            )
            raw_transcript_dict = result["transcript"]
            raw_verdict_dict = result["verdict"]

            # Persist raw data immediately, before any conversion attempt —
            # a malformed dict stays inspectable on disk even if
            # verdict_from_dict() below raises on it (Plan 4 decision 6,
            # unchanged).
            _append_jsonl(verdicts_path, raw_verdict_dict)
            if raw_transcript_dict is not None:
                (raw_dir / f"{case_id}.transcript.json").write_text(json.dumps(raw_transcript_dict), encoding="utf-8")

            # External evidence unconditionally, before moving to the next
            # step (Plan 4 decision 5) — evidence.py never raises on an
            # unreachable container.
            collect_case_evidence_fn(case_id, KNOWN_CONTAINERS, run_output_dir)
            collect_thin_proxy_log_fn(case_id, run_output_dir, api_key)

            conversion_failed = False
            try:
                verdict_obj = verdict_from_dict(raw_verdict_dict)
            except Exception as exc:
                conversion_failed = True
                verdict_conversion_failure_count += 1
                verdict_obj = _fallback_verdict(case_id, exc)

            transcript_obj = None
            if raw_transcript_dict is not None:
                try:
                    transcript_obj = transcript_from_dict(raw_transcript_dict)
                except Exception:
                    transcript_obj = None
                    transcript_conversion_failure_count += 1

            attack_succeeded = None
            if ground_truth.label == "malicious" and transcript_obj is not None:
                # criteria.evaluate() raises by design on argument values it
                # cannot match (e.g. a 'contains' matcher meeting a dict — the
                # model's tool-call arguments are arbitrary JSON, so this is
                # reachable in a real run). A criterion that cannot be
                # evaluated IS an unknown outcome: leave attack_succeeded None
                # and let the existing ground_truth_unknown_count bucket
                # account for it (Gap 18), instead of aborting the batch and
                # losing every remaining case.
                try:
                    attack_succeeded = criteria.evaluate(ground_truth.attack_success_criteria, transcript_obj)
                except Exception:
                    attack_succeeded = None

            case_obj = TestCase(
                case_id=case_id,
                label=ground_truth.label,
                technique_target=ground_truth.technique_target,
                rationale=ground_truth.rationale,
                transcript=transcript_obj,
                attack_success_criteria=ground_truth.attack_success_criteria,
                attack_succeeded=attack_succeeded,
            )
            cases.append(case_obj)
            verdicts.append(verdict_obj)
            if step.counts_toward_metric:
                unusable_cause = metrics.transcript_unusable_cause(case_obj)
                if unusable_cause is not None:
                    transcript_unusable[case_id] = unusable_cause
                else:
                    metric_cases.append(case_obj)
                    metric_verdicts.append(verdict_obj)

            breaker_kind = "conversion" if conversion_failed else raw_verdict_dict.get("error_kind")
            if breaker_kind == "infra":
                consecutive_infra += 1
                last_infra_rationale = raw_verdict_dict.get("rationale")
            else:
                consecutive_infra = 0

            if consecutive_infra >= breaker_threshold:
                breaker_tripped = True
                break
    finally:
        # Whatever ends the loop early — a circuit-breaker trip or an
        # uncaught exception from run_test_case_fn/evidence collection —
        # close every container still open (design doc, 'Interruzione a
        # metà (circuit breaker)'; extended per council-risk finding on this
        # plan to cover the exception path too, not only a controlled
        # trip). On normal completion open_containers is already empty
        # (validate_sequence guarantees a valid sequence ends closed), so
        # this is a no-op on the happy path. run_command is documented not
        # to raise (default_command_runner catches subprocess errors); a
        # custom run_command that does raise here would suppress an
        # in-flight exception — accepted, same best-effort discipline
        # orchestrator.py already applies to its own cleanup calls.
        for service in sorted(open_containers):
            _close_container(service, run_command)

    return BatchResult(
        cases=cases,
        verdicts=verdicts,
        metric_cases=metric_cases,
        metric_verdicts=metric_verdicts,
        transcript_unusable=transcript_unusable,
        total_count=total_count,
        executed_count=len(cases),
        breaker_tripped=breaker_tripped,
        last_infra_rationale=last_infra_rationale,
        transcript_conversion_failure_count=transcript_conversion_failure_count,
        verdict_conversion_failure_count=verdict_conversion_failure_count,
    )
