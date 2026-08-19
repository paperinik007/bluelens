from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable

from . import evidence
from .dataset import load_dataset
from .metrics import compute_metrics
from .orchestrator import CommandRunner, default_command_runner, run_test_case
from .preflight import preflight_check_models
from .report import render_report
from .schema import TestCase
from .sequence import BatchResult, CloseStep, CommandStep, KNOWN_CONTAINERS, OpenStep, execute_sequence

AGENT_TIMEOUT_S = 120.0
DETECTOR_TIMEOUT_S = 180.0
BREAKER_THRESHOLD = 3


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


def _setup_notes(result: BatchResult, agent_timeout_s: float, detector_timeout_s: float, breaker_threshold: int) -> str:
    notes = [
        f"agent_timeout_s={agent_timeout_s}",
        f"detector_timeout_s={detector_timeout_s}",
        f"circuit_breaker_threshold={breaker_threshold}",
    ]
    excluded = len(result.cases) - len(result.metric_cases)
    if excluded > 0:
        notes.append(
            f"{excluded} command(s) excluded from precision/recall via counts_toward_metric=false "
            f"(raw verdict still persisted to disk, reviewable by hand)"
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
    return " | ".join(notes)


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

    result = execute_batch(dataset, run_output_dir, container_lifecycle=parsed.container_lifecycle, api_key=api_key)

    metrics = compute_metrics(result.metric_cases, result.metric_verdicts)
    setup_notes = _setup_notes(result, AGENT_TIMEOUT_S, DETECTOR_TIMEOUT_S, BREAKER_THRESHOLD)
    report = render_report(result.cases, result.verdicts, metrics, setup_notes=setup_notes)
    run_output_dir.mkdir(parents=True, exist_ok=True)
    (run_output_dir / "report.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
