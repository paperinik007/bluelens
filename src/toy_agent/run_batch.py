from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import evidence
from .dataset import load_dataset
from .metrics import compute_metrics
from .orchestrator import run_test_case
from .report import render_report
from .schema import TestCase, Verdict
from .serialization import transcript_from_dict, verdict_from_dict

AGENT_TIMEOUT_S = 120.0
DETECTOR_TIMEOUT_S = 180.0
BREAKER_THRESHOLD = 3
SERVICES = ("agent", "detector")


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


def _agent_input(case: TestCase) -> dict:
    """Reduced dict sent to run_test_case(): only case_id and the seed turn's
    content — never label/technique_target/rationale (design doc decision 2)."""
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


def execute_batch(
    dataset: list[TestCase],
    run_output_dir: Path,
    *,
    agent_timeout_s: float = AGENT_TIMEOUT_S,
    detector_timeout_s: float = DETECTOR_TIMEOUT_S,
    breaker_threshold: int = BREAKER_THRESHOLD,
    api_key: str = "",
    run_test_case_fn: Callable[..., dict] = run_test_case,
    collect_case_evidence_fn: Callable = evidence.collect_case_evidence,
    collect_thin_proxy_log_fn: Callable = evidence.collect_thin_proxy_log,
) -> BatchResult:
    """Drive `dataset` through run_test_case_fn one case at a time (design doc,
    'Orchestrazione del run', Plan 4 decisions 2, 5, 6, 8, 14).

    Never imports detector_adapter or aidr — same boundary orchestrator.py
    already declares."""
    raw_dir = run_output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    verdicts_path = run_output_dir / "verdicts.jsonl"
    # Truncate at the start of each run (not append-forever) — a rerun of the
    # same run_output_dir (natural after a circuit-breaker trip or an infra
    # fix) must not desync verdicts.jsonl from report.md/raw/*.json, which
    # are already overwritten rather than accumulated on rerun (Finding 2,
    # final review).
    verdicts_path.write_text("", encoding="utf-8")

    cases: list[TestCase] = []
    verdicts: list[Verdict] = []
    consecutive_infra = 0
    last_infra_rationale: Optional[str] = None
    breaker_tripped = False
    transcript_conversion_failure_count = 0
    verdict_conversion_failure_count = 0

    for ground_truth in dataset:
        case_id = ground_truth.case_id
        result = run_test_case_fn(
            _agent_input(ground_truth),
            agent_timeout_s=agent_timeout_s,
            detector_timeout_s=detector_timeout_s,
        )
        raw_transcript_dict = result["transcript"]
        raw_verdict_dict = result["verdict"]

        # Persist raw data immediately (decision 6) — before any conversion
        # attempt, so a malformed dict is still inspectable on disk even if
        # verdict_from_dict() below raises on it.
        _append_jsonl(verdicts_path, raw_verdict_dict)
        if raw_transcript_dict is not None:
            (raw_dir / f"{case_id}.transcript.json").write_text(json.dumps(raw_transcript_dict), encoding="utf-8")

        # External evidence, unconditionally, before moving to the next case
        # (decision 5) — evidence.py itself never raises on an unreachable
        # container (Task 3 fix), so this is not wrapped here.
        collect_case_evidence_fn(case_id, SERVICES, run_output_dir)
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

        cases.append(TestCase(
            case_id=case_id,
            label=ground_truth.label,
            technique_target=ground_truth.technique_target,
            rationale=ground_truth.rationale,
            transcript=transcript_obj,
        ))
        verdicts.append(verdict_obj)

        breaker_kind = "conversion" if conversion_failed else raw_verdict_dict.get("error_kind")
        if breaker_kind == "infra":
            consecutive_infra += 1
            last_infra_rationale = raw_verdict_dict.get("rationale")
        else:
            consecutive_infra = 0

        if consecutive_infra >= breaker_threshold:
            breaker_tripped = True
            break

    return BatchResult(
        cases=cases,
        verdicts=verdicts,
        total_count=len(dataset),
        executed_count=len(cases),
        breaker_tripped=breaker_tripped,
        last_infra_rationale=last_infra_rationale,
        transcript_conversion_failure_count=transcript_conversion_failure_count,
        verdict_conversion_failure_count=verdict_conversion_failure_count,
    )


def _setup_notes(result: BatchResult, agent_timeout_s: float, detector_timeout_s: float, breaker_threshold: int) -> str:
    notes = [
        f"agent_timeout_s={agent_timeout_s}",
        f"detector_timeout_s={detector_timeout_s}",
        f"circuit_breaker_threshold={breaker_threshold}",
    ]
    if result.transcript_conversion_failure_count > 0:
        notes.append(f"transcript_conversion_failures={result.transcript_conversion_failure_count}")
    if result.verdict_conversion_failure_count > 0:
        notes.append(f"verdict_conversion_failures={result.verdict_conversion_failure_count}")
    if result.breaker_tripped:
        notes.insert(
            0,
            f"circuit breaker tripped after {result.executed_count}/{result.total_count} cases executed; "
            f"last infra failure: {result.last_infra_rationale}",
        )
    return " | ".join(notes)


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: python -m toy_agent.run_batch <dataset_dir> <run_output_dir>", file=sys.stderr)
        raise SystemExit(2)

    dataset_dir = Path(args[0])
    run_output_dir = Path(args[1])

    dataset = load_dataset(dataset_dir)
    api_key = os.environ.get("DETECTOR_OPENROUTER_API_KEY", "")
    result = execute_batch(dataset, run_output_dir, api_key=api_key)

    metrics = compute_metrics(result.cases, result.verdicts)
    setup_notes = _setup_notes(result, AGENT_TIMEOUT_S, DETECTOR_TIMEOUT_S, BREAKER_THRESHOLD)
    report = render_report(result.cases, result.verdicts, metrics, setup_notes=setup_notes)
    run_output_dir.mkdir(parents=True, exist_ok=True)
    (run_output_dir / "report.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
