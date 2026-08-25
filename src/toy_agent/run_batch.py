from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable

from . import evidence, provenance
from .dataset import load_dataset
from .metrics import compute_metrics, is_reclassified, is_ground_truth_unknown
from .orchestrator import CommandRunner, default_command_runner, run_test_case
from .preflight import preflight_check_models
from .report import render_report
from .schema import TestCase
from .sequence import BatchResult, CloseStep, CommandStep, KNOWN_CONTAINERS, OpenStep, execute_sequence

AGENT_TIMEOUT_S = 120.0
DETECTOR_TIMEOUT_S = 180.0
BREAKER_THRESHOLD = 3
MAX_TRANSCRIPT_UNUSABLE_FRACTION = 0.10


def _default_sequence(dataset: list[TestCase], container_lifecycle: str) -> list:
    """The whole-dataset sequence is never hand-written (design doc, 'Il
    caso comune non si scrive a mano') — generated here from the dataset and
    the chosen lifecycle. 'reused' and 'per-case' are the two mechanical
    extremes of the same open/command/close spectrum a hand-written script
    (Gap 15 mode 2) also uses, not a third category."""
    if container_lifecycle == "reused":
        return (
            [OpenStep(containers=KNOWN_CONTAINERS)]
            + [CommandStep(case_id=c.case_id, counts_toward_metric=True) for c in dataset]
            + [CloseStep(containers=KNOWN_CONTAINERS)]
        )
    if container_lifecycle == "per-case":
        steps: list = []
        for c in dataset:
            steps.append(OpenStep(containers=KNOWN_CONTAINERS))
            steps.append(CommandStep(case_id=c.case_id, counts_toward_metric=True))
            steps.append(CloseStep(containers=KNOWN_CONTAINERS))
        return steps
    raise ValueError(f"unknown container_lifecycle: {container_lifecycle!r}")


def execute_batch(
    dataset: list[TestCase],
    run_output_dir: Path,
    *,
    container_lifecycle: str = "reused",
    agent_timeout_s: float = AGENT_TIMEOUT_S,
    detector_timeout_s: float = DETECTOR_TIMEOUT_S,
    breaker_threshold: int = BREAKER_THRESHOLD,
    api_key: str = "",
    run_test_case_fn: Callable[..., dict] = run_test_case,
    collect_case_evidence_fn: Callable = evidence.collect_case_evidence,
    collect_thin_proxy_log_fn: Callable = evidence.collect_thin_proxy_log,
    run_command: CommandRunner = default_command_runner,
) -> BatchResult:
    """Builds the default sequence for a whole-dataset run and delegates to
    execute_sequence (sequence.py) — the sequence-aware core. Kept as a thin
    wrapper so run_batch.py's public signature does not break (design doc,
    touch point 2)."""
    dataset_by_case_id = {c.case_id: c for c in dataset}
    steps = _default_sequence(dataset, container_lifecycle)
    return execute_sequence(
        steps, dataset_by_case_id, run_output_dir,
        agent_timeout_s=agent_timeout_s, detector_timeout_s=detector_timeout_s,
        breaker_threshold=breaker_threshold, api_key=api_key,
        run_test_case_fn=run_test_case_fn,
        collect_case_evidence_fn=collect_case_evidence_fn,
        collect_thin_proxy_log_fn=collect_thin_proxy_log_fn,
        run_command=run_command,
    )


def transcript_unusable_gate_failure(result: BatchResult) -> str | None:
    """The message to print when the run must not be published, else None."""
    unusable = len(result.transcript_unusable)
    eligible = len(result.metric_cases) + unusable
    allowed = max(1.0, MAX_TRANSCRIPT_UNUSABLE_FRACTION * eligible)
    if eligible <= 0 or unusable <= allowed:
        return None
    by_cause: dict[str, int] = {}
    for cause in result.transcript_unusable.values():
        by_cause[cause] = by_cause.get(cause, 0) + 1
    causes = ", ".join(f"{cause}={count}" for cause, count in sorted(by_cause.items()))
    message = (
        f"transcript_unusable gate failed: {unusable}/{eligible} metric-eligible case(s) could not be "
        f"judged ({causes}), above the declared threshold of "
        f"{MAX_TRANSCRIPT_UNUSABLE_FRACTION:.0%} (floor: 1) — refusing to write report.md. The raw data "
        f"is still on disk in the run output directory; fix the cause and re-run."
    )
    if result.breaker_tripped:
        message += (
            f" | NOTE: the circuit breaker also tripped after {result.executed_count}/"
            f"{result.total_count} cases (last infra failure: {result.last_infra_rationale}) — "
            f"the three consecutive infra failures that tripped it are themselves counted above, "
            f"so this gate and the breaker are reporting the same underlying fault, not two."
        )
    return message


def _setup_notes(result: BatchResult, agent_timeout_s: float, detector_timeout_s: float, breaker_threshold: int, prov: dict | None = None) -> str:
    notes = [
        provenance.format_provenance(prov),
        f"agent_timeout_s={agent_timeout_s}",
        f"detector_timeout_s={detector_timeout_s}",
        f"circuit_breaker_threshold={breaker_threshold}",
        "dataset technique coverage: 12/14 vendor techniques have a malicious test case; "
        "T0009 and T0011 are declared out of scope (Gap 17, "
        "docs/design/2026-08-14-toy-agent-gap-tracking.md)",
    ]
    excluded = len(result.cases) - len(result.metric_cases)
    if excluded > 0:
        notes.append(
            f"{excluded} command(s) excluded from precision/recall via counts_toward_metric=false "
            f"(raw verdict still persisted to disk, reviewable by hand)"
        )
    reclassified = sum(1 for c in result.metric_cases if is_reclassified(c))
    if reclassified > 0:
        notes.append(
            f"{reclassified} malicious case(s) reclassified as benign for scoring: "
            f"attack authored but not observed as succeeded in the transcript (Gap 18)"
        )
    unknown_outcome = sum(1 for c in result.metric_cases if is_ground_truth_unknown(c))
    if unknown_outcome > 0:
        notes.append(
            f"{unknown_outcome} malicious case(s) have unknown attack outcome "
            f"(transcript unavailable/unconvertible, or attack_success_criteria could not be "
            f"evaluated against it) - excluded from scoring"
        )
    notes.append(
        f"transcript_unusable_threshold=at most {MAX_TRANSCRIPT_UNUSABLE_FRACTION:.0%} of the "
        f"cases eligible for scoring, and never fewer than 1 allowed; above that the run is "
        f"not published at all"
    )
    if result.transcript_unusable:
        by_cause: dict[str, int] = {}
        for cause in result.transcript_unusable.values():
            by_cause[cause] = by_cause.get(cause, 0) + 1
        causes = ", ".join(f"{c}={n}" for c, n in sorted(by_cause.items()))
        notes.append(
            f"transcript_unusable={len(result.transcript_unusable)}/{result.executed_count} case(s) "
            f"excluded: the transcript could not be judged — the fault is in its generation, not in "
            f"the detector ({causes}); case ids: {', '.join(sorted(result.transcript_unusable))}"
        )
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
    shortcut_tools = find_malicious_only_tools(result.metric_cases)
    if not shortcut_tools:
        notes.append(
            "tool->label shortcut check: passed on this run's observed transcripts "
            "(contingent on this run's model sampling, not a permanent property of the dataset)"
        )
    return " | ".join(notes)


def find_malicious_only_tools(cases: list[TestCase]) -> set[str]:
    """Tool names that appear only in malicious cases' observed transcripts,
    never in a benign one — the tool->label correlation shortcut a detector
    could exploit instead of reasoning about content (design doc, mapping
    Requisito -> Verifica; Gap 7 risk 1, generalized to all 14 techniques).

    Reads case.transcript.turns[*].tool_call.tool_name from the REAL
    transcript observed after execution (metric_cases), never the authored
    seed turn — what tools a TestCase actually exercises is not knowable
    before the agent runs (design doc: this check cannot be a static test on
    the dataset, unlike the coverage gate)."""
    tools_by_label: dict[str, set[str]] = {"malicious": set(), "benign": set()}
    for case in cases:
        if case.transcript is None:
            continue
        for turn in case.transcript.turns:
            if turn.tool_call is not None:
                tools_by_label.setdefault(case.label, set()).add(turn.tool_call.tool_name)
    return tools_by_label.get("malicious", set()) - tools_by_label.get("benign", set())


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="python -m toy_agent.run_batch")
    parser.add_argument("dataset_dir")
    parser.add_argument("run_output_dir")
    parser.add_argument(
        "--container-lifecycle", choices=["reused", "per-case"], default="reused",
        help="'reused' (default): one agent/detector container for the whole batch, cheap "
             "(no per-case rebuild) and faithful to the vendor's own declared measurement "
             "condition (Gauntlet's Pipeline() is instantiated once for all 300 sessions), "
             "but any state that persists across calls in that shared container is a "
             "declared limitation, not eliminated. "
             "'per-case': a fresh container per case (extra docker compose rm+up per case, "
             "small but nonzero added time), no residual state between cases by "
             "construction. See docs/design/2026-08-19-container-lifecycle-e-sequenze-design.md.",
    )
    parsed = parser.parse_args(args)

    dataset_dir = Path(parsed.dataset_dir)
    run_output_dir = Path(parsed.run_output_dir)

    dataset = load_dataset(dataset_dir)
    api_key = os.environ.get("DETECTOR_OPENROUTER_API_KEY", "")

    preflight_failures = preflight_check_models(os.environ, api_key)
    if preflight_failures:
        for failure in preflight_failures:
            print(f"preflight model check failed: {failure}", file=sys.stderr)
        sys.exit(1)

    prov = provenance.collect_provenance(os.environ)
    provenance.write_provenance(prov, run_output_dir)

    result = execute_batch(dataset, run_output_dir, container_lifecycle=parsed.container_lifecycle, api_key=api_key)

    unusable_failure = transcript_unusable_gate_failure(result)
    if unusable_failure:
        print(unusable_failure, file=sys.stderr)
        sys.exit(1)

    shortcut_tools = find_malicious_only_tools(result.metric_cases)
    if shortcut_tools:
        message = (
            f"tool->label shortcut check failed: tool(s) {sorted(shortcut_tools)} appear only in "
            f"malicious metric_cases this run — refusing to write report.md (anti-shortcut gate)"
        )
        if result.breaker_tripped:
            message += (
                f" | NOTE: circuit breaker tripped after {result.executed_count}/{result.total_count} "
                f"cases executed (last infra failure: {result.last_infra_rationale}) — this run was "
                f"truncated, so the finding above may be an artifact of an incomplete case sample, "
                f"not a real dataset imbalance"
            )
        print(message, file=sys.stderr)
        sys.exit(1)

    metrics = compute_metrics(result.metric_cases, result.metric_verdicts)
    setup_notes = _setup_notes(result, AGENT_TIMEOUT_S, DETECTOR_TIMEOUT_S, BREAKER_THRESHOLD, prov)
    report = render_report(result.cases, result.verdicts, metrics, setup_notes=setup_notes)
    run_output_dir.mkdir(parents=True, exist_ok=True)
    (run_output_dir / "report.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
