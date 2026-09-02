from __future__ import annotations

import argparse
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import evidence, provenance
from .dataset import load_dataset
from .metrics import compute_metrics, is_reclassified, is_ground_truth_unknown
from .orchestrator import CommandRunner, VENDOR_DETECTOR_CONFIG, default_command_runner, run_test_case
from .preflight import preflight_check_models
from .report import render_report
from .schema import TestCase
from .sequence import BatchResult, CloseStep, CommandStep, OpenStep, execute_sequence, known_containers_for

AGENT_TIMEOUT_S = 120.0
DETECTOR_TIMEOUT_S = 180.0
BREAKER_THRESHOLD = 3
MAX_TRANSCRIPT_UNUSABLE_FRACTION = 0.10
MAX_COST_USD_DEFAULT = 5.00  # Costo reale misurato per LlamaFirewall (Task 17,
                              # 2026-08-28): $0.0318/31 casi ($0.00102/caso);
                              # aidr: $0.0136/31 casi ($0.00044/caso) - circa
                              # 2.3x piu' caro per caso, stesso ordine di
                              # grandezza. Confermato ampiamente conservativo
                              # (>150x il costo osservato per l'intero run) -
                              # vedi docs/design/registro-limiti-aperti.md.

# Vendor -> host env var holding that vendor's OpenRouter key. run_batch.py
# runs on the host, not inside a container — the active vendor's key must
# be exported here too (same convention already documented for
# DETECTOR_OPENROUTER_API_KEY, now extended).
API_KEY_ENV_VAR_BY_VENDOR: dict[str, str] = {
    "aidr": "DETECTOR_OPENROUTER_API_KEY",
    "llamafirewall": "LLAMAFIREWALL_OPENROUTER_API_KEY",
    "llamafirewall-combined": "LLAMAFIREWALL_OPENROUTER_API_KEY",
}


def _default_sequence(dataset: list[TestCase], container_lifecycle: str, vendor: str) -> list:
    """The whole-dataset sequence is never hand-written (design doc, 'Il
    caso comune non si scrive a mano') — generated here from the dataset and
    the chosen lifecycle. 'reused' and 'per-case' are the two mechanical
    extremes of the same open/command/close spectrum a hand-written script
    (Gap 15 mode 2) also uses, not a third category."""
    containers = known_containers_for(vendor)
    if container_lifecycle == "reused":
        return (
            [OpenStep(containers=containers)]
            + [CommandStep(case_id=c.case_id, counts_toward_metric=True) for c in dataset]
            + [CloseStep(containers=containers)]
        )
    if container_lifecycle == "per-case":
        steps: list = []
        for c in dataset:
            steps.append(OpenStep(containers=containers))
            steps.append(CommandStep(case_id=c.case_id, counts_toward_metric=True))
            steps.append(CloseStep(containers=containers))
        return steps
    raise ValueError(f"unknown container_lifecycle: {container_lifecycle!r}")


def execute_batch(
    dataset: list[TestCase],
    run_output_dir: Path,
    *,
    vendor: str,
    container_lifecycle: str = "reused",
    agent_timeout_s: float = AGENT_TIMEOUT_S,
    detector_timeout_s: float = DETECTOR_TIMEOUT_S,
    breaker_threshold: int = BREAKER_THRESHOLD,
    max_cost_usd: float | None = None,
    api_key: str = "",
    run_test_case_fn: Callable[..., dict] = run_test_case,
    collect_case_evidence_fn: Callable = evidence.collect_case_evidence,
    collect_thin_proxy_log_fn: Callable = evidence.collect_thin_proxy_log,
    run_command: CommandRunner = default_command_runner,
    progress_fn: Callable[[str], None] | None = None,
) -> BatchResult:
    """Builds the default sequence for a whole-dataset run and delegates to
    execute_sequence (sequence.py) — the sequence-aware core. Kept as a thin
    wrapper so run_batch.py's public signature does not break (design doc,
    touch point 2)."""
    dataset_by_case_id = {c.case_id: c for c in dataset}
    steps = _default_sequence(dataset, container_lifecycle, vendor)
    return execute_sequence(
        steps, dataset_by_case_id, run_output_dir,
        vendor=vendor,
        agent_timeout_s=agent_timeout_s, detector_timeout_s=detector_timeout_s,
        breaker_threshold=breaker_threshold, max_cost_usd=max_cost_usd, api_key=api_key,
        run_test_case_fn=run_test_case_fn,
        collect_case_evidence_fn=collect_case_evidence_fn,
        collect_thin_proxy_log_fn=collect_thin_proxy_log_fn,
        run_command=run_command,
        progress_fn=progress_fn,
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
    if result.cost_breaker_tripped:
        notes.insert(
            0,
            f"cost circuit breaker tripped after {result.executed_count}/{result.total_count} cases "
            f"executed; cumulative cost ${result.cumulative_cost_usd:.4f} exceeded the --max-cost-usd threshold",
        )
    shortcut_tools = find_malicious_only_tools(result.metric_cases)
    if not shortcut_tools:
        notes.append(
            "tool->label shortcut check: passed on this run's observed transcripts "
            "(contingent on this run's model sampling, not a permanent property of the dataset)"
        )
    return " | ".join(notes)


def _working_tree_root() -> Path | None:
    """The checkout root for the process's current working directory, found
    by walking up from cwd until src/toy_agent/__init__.py is seen — the
    marker that distinguishes a real checkout from an arbitrary cwd. Returns
    None when launched from outside any checkout (the guard below treats this
    as a refusal — the project convention is to run from the repository root)."""
    start = Path.cwd().resolve()
    for candidate in (start, *start.parents):
        if (candidate / "src" / "toy_agent" / "__init__.py").is_file():
            return candidate
    return None


def _assert_running_from_this_working_tree() -> None:
    """Refuse to run when the imported toy_agent package is not the one in
    the working tree we were launched from. An editable install (pip install
    -e .) records a single absolute path — the main checkout — so launching
    'python -m toy_agent.run_batch' from a worktree silently executes the
    main checkout's code (two full batch runs were wasted this way before the
    trap was diagnosed). This guard turns that silent failure into an
    explicit refusal (SPIRIT.md, principle 8): the code fails loudly instead
    of trusting the operator to remember PYTHONPATH.

    Not called in run_case.py — that module runs inside the agent Docker
    container where the code is baked into the image at build time, so the
    editable-install trap does not apply."""
    here = Path(__file__).resolve()
    root = _working_tree_root()
    if root is None:
        print(
            "refusing to run: could not locate the working tree "
            "(no src/toy_agent/__init__.py found walking up from the current "
            "directory). Run from the repository root.",
            file=sys.stderr,
        )
        sys.exit(1)
    expected = (root / "src" / "toy_agent").resolve()
    if here.parent != expected:
        print(
            "refusing to run: toy_agent was imported from a different checkout "
            "than the one you launched from.\n"
            f"  imported from: {here.parent}\n"
            f"  working tree:  {expected}\n"
            "An editable install points at one absolute path (the main checkout), so a "
            "worktree launch silently runs the wrong code. Force the working tree's "
            "src/ onto the path and re-run:\n"
            f"  PYTHONPATH={root / 'src'} python -m toy_agent.run_batch <dataset_dir> <run_output_dir>",
            file=sys.stderr,
        )
        sys.exit(1)


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
    _assert_running_from_this_working_tree()
    args = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="python -m toy_agent.run_batch")
    parser.add_argument("dataset_dir")
    parser.add_argument("run_output_dir")
    parser.add_argument(
        "--vendor", choices=list(VENDOR_DETECTOR_CONFIG), required=True,
        help="which detector vendor to audit — always explicit, never persisted in .env (principio 8, SPIRIT.md)",
    )
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
    parser.add_argument(
        "--max-cost-usd", type=float, default=MAX_COST_USD_DEFAULT,
        help="cumulative proxy cost (USD) above which the batch is interrupted (not the single case) — "
             "default measured and confirmed conservative on a real run (Task 17): LlamaFirewall "
             "$0.0318/31 cases, aidr $0.0136/31 cases, both >150x below this default",
    )
    parsed = parser.parse_args(args)

    vendor = parsed.vendor
    detector_config = VENDOR_DETECTOR_CONFIG[vendor]

    dataset_dir = Path(parsed.dataset_dir)
    run_output_dir = Path(parsed.run_output_dir)

    dataset = load_dataset(dataset_dir)
    api_key_env_var = API_KEY_ENV_VAR_BY_VENDOR[vendor]
    api_key = os.environ.get(api_key_env_var, "")
    agent_api_key = os.environ.get("AGENT_OPENROUTER_API_KEY", "")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
    run_dir = run_output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    log_path = run_dir / "run.log"
    log_fh = log_path.open("a", encoding="utf-8")
    def progress(line: str) -> None:
        print(line, file=sys.stderr, flush=True)
        log_fh.write(line + "\n")
        log_fh.flush()

    prov = provenance.collect_provenance(os.environ, vendor=vendor)
    prov["run_id"] = run_id
    provenance.write_provenance(prov, run_dir)

    progress("=== agentic-security-audits — run ===")
    progress(f"run_id: {run_id}")
    progress(f"vendor: {vendor}")
    progress(f"dataset: {dataset_dir} ({len(dataset)} cases)")
    progress(f"output:  {run_dir}")
    progress(
        f"measurer: {prov.get('measurer_commit', 'unknown')} "
        f"({'dirty' if prov.get('measurer_dirty') else 'clean'})   "
        f"vendor_commit: {prov.get('vendor_commit') or prov.get('vendor_pip_version') or 'unknown'}"
    )
    progress(f"agent: {prov.get('agent_model', 'unknown')}")
    progress(f"lifecycle: {parsed.container_lifecycle}")

    if not api_key:
        progress(f"refusing to run: {api_key_env_var} is not set in the host shell for --vendor {vendor}")
        sys.exit(1)

    progress("--- preflight ---")
    preflight_failures = preflight_check_models(os.environ, api_key, vendor=vendor, agent_api_key=agent_api_key)
    if preflight_failures:
        for failure in preflight_failures:
            progress(f"preflight model check failed: {failure}")
        sys.exit(1)
    progress("checking models...  OK")
    progress("--- containers ---")

    result = execute_batch(
        dataset, run_dir,
        vendor=vendor,
        container_lifecycle=parsed.container_lifecycle,
        max_cost_usd=parsed.max_cost_usd,
        api_key=api_key,
        progress_fn=progress,
    )

    by_cause: dict[str, int] = {}
    for cause in result.transcript_unusable.values():
        by_cause[cause] = by_cause.get(cause, 0) + 1
    causes = ", ".join(f"{k}={v}" for k, v in sorted(by_cause.items()))
    progress("=== summary ===")
    progress(
        f"{result.executed_count} cases: {len(result.metric_cases)} judged, "
        f"{len(result.transcript_unusable)} excluded ({causes})"
    )
    progress(f"cumulative in_tokens: {result.total_in_tokens}")
    progress(f"circuit breaker: {'tripped' if result.breaker_tripped else 'not tripped'}")

    try:
        latest = run_output_dir / "latest"
        if latest.is_symlink() or latest.exists():
            latest.unlink()
        latest.symlink_to(run_dir.name, target_is_directory=True)
    except OSError:
        # Windows senza developer mode / permessi: si salta. L'ordinamento per
        # nome copre la scoperta dell'ultimo run (design §2.3).
        pass

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
    report = render_report(
        result.cases,
        result.verdicts,
        metrics,
        tool_name=detector_config.tool_name,
        vendor=vendor,
        setup_notes=setup_notes,
        transcript_unusable=result.transcript_unusable,
        provenance=prov,
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    progress(f"report.md written to {run_dir}")
    log_fh.close()


if __name__ == "__main__":
    main()
