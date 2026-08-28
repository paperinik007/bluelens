from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import criteria
from . import metrics as metrics_module, provenance
from .dataset import load_dataset
from .metrics import compute_metrics
from .orchestrator import VENDOR_DETECTOR_CONFIG
from .report import render_report
from .run_batch import (
    AGENT_TIMEOUT_S,
    BREAKER_THRESHOLD,
    DETECTOR_TIMEOUT_S,
    _assert_running_from_this_working_tree,
    _setup_notes,
    find_malicious_only_tools,
    transcript_unusable_gate_failure,
)
from .schema import TestCase, Verdict
from .sequence import BatchResult, _fallback_verdict
from .serialization import transcript_from_dict, verdict_from_dict


def regenerate(dataset_dir: Path, run_output_dir: Path) -> str:
    """Rebuild report.md from a COMPLETED run's already-persisted output —
    verdicts.jsonl + raw/*.transcript.json — without re-invoking any
    container or making a new API call.

    Replicates execute_sequence()'s per-case reconstruction (sequence.py,
    ~lines 191-260) reading from disk instead of from a live
    run_test_case_fn result, and run_batch.py's default sequence's
    unconditional counts_toward_metric=True (every reconstructed case
    counts toward the metric — metric_cases == cases, metric_verdicts ==
    verdicts). Does not write any file itself; the caller decides where the
    returned report string goes.
    """
    if not (run_output_dir / "raw").is_dir() or not (run_output_dir / "verdicts.jsonl").is_file():
        raise ValueError(
            f"{run_output_dir} does not look like a run directory — "
            f"point to run_output/<run_id>/ (or run_output/latest/), not the root"
        )

    dataset = load_dataset(dataset_dir)
    dataset_by_case_id = {c.case_id: c for c in dataset}

    verdicts_path = run_output_dir / "verdicts.jsonl"
    raw_dir = run_output_dir / "raw"

    raw_lines = [
        line for line in verdicts_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    raw_verdict_dicts = [json.loads(line) for line in raw_lines]

    # Precondition (this tool's substitute for run_batch.py's
    # executed_count/total_count/breaker_tripped signal, which isn't
    # available from disk): a truncated run_output/ (e.g. an interrupted
    # batch) must never silently produce a report that claims full
    # coverage.
    if len(raw_verdict_dicts) != len(dataset):
        raise ValueError(
            f"verdicts.jsonl has {len(raw_verdict_dicts)} entries but the dataset at "
            f"{dataset_dir} has {len(dataset)} cases — this tool only regenerates a "
            f"report from a COMPLETE run; a truncated run_output/ (e.g. from an "
            f"interrupted batch) must not silently produce a report claiming full "
            f"coverage"
        )

    cases: list[TestCase] = []
    verdicts: list[Verdict] = []
    transcript_conversion_failure_count = 0
    verdict_conversion_failure_count = 0

    for raw_verdict_dict in raw_verdict_dicts:
        case_id = raw_verdict_dict.get("case_id")
        ground_truth = dataset_by_case_id.get(case_id)
        if ground_truth is None:
            raise ValueError(
                f"verdicts.jsonl references case_id {case_id!r} which has no matching "
                f"entry in dataset_dir {dataset_dir} — dataset/ and run_output/ are out "
                f"of sync; refusing to regenerate a mismatched report"
            )

        try:
            verdict_obj = verdict_from_dict(raw_verdict_dict)
        except Exception as exc:
            verdict_conversion_failure_count += 1
            verdict_obj = _fallback_verdict(case_id, exc)

        transcript_path = raw_dir / f"{case_id}.transcript.json"
        transcript_obj = None
        if transcript_path.exists():
            raw_transcript_dict = json.loads(transcript_path.read_text(encoding="utf-8"))
            try:
                transcript_obj = transcript_from_dict(raw_transcript_dict)
            except Exception:
                transcript_obj = None
                transcript_conversion_failure_count += 1
        # else: no transcript file (analogous to result["transcript"] being
        # None in the live pipeline) -> transcript_obj stays None; this is
        # NOT a conversion failure, matching sequence.py's exact counting
        # convention (only a parse exception increments the counter).

        attack_succeeded = None
        if ground_truth.label == "malicious" and transcript_obj is not None:
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

    metric_cases = []
    metric_verdicts = []
    transcript_unusable: dict[str, str] = {}
    for case_obj, verdict_obj in zip(cases, verdicts):
        cause = metrics_module.transcript_unusable_cause(case_obj)
        if cause is not None:
            transcript_unusable[case_obj.case_id] = cause
        else:
            metric_cases.append(case_obj)
            metric_verdicts.append(verdict_obj)

    result = BatchResult(
        cases=cases,
        verdicts=verdicts,
        metric_cases=metric_cases,
        metric_verdicts=metric_verdicts,
        transcript_unusable=transcript_unusable,
        total_count=len(cases),
        executed_count=len(cases),
        breaker_tripped=False,
        transcript_conversion_failure_count=transcript_conversion_failure_count,
        verdict_conversion_failure_count=verdict_conversion_failure_count,
    )

    unusable_failure = transcript_unusable_gate_failure(result)
    if unusable_failure:
        raise ValueError(unusable_failure)

    # Anti-shortcut gate (mirrors run_batch.py::main(), lines ~176-190): the
    # live pipeline refuses to write report.md at all when a tool appears
    # only in malicious metric_cases' observed transcripts this run — a
    # detector could exploit that tool->label correlation instead of
    # reasoning about content. verdicts.jsonl/raw/*.transcript.json are
    # persisted unconditionally per-case DURING execute_sequence, entirely
    # before and independent of that gate check in main() — so a live run
    # can finish every case (a full verdicts.jsonl on disk) and still have
    # failed the gate and never written report.md. _setup_notes() alone
    # does not enforce this — it only adds a "passed" note when the set is
    # empty, silently omitting any note (and never raising) when it is not
    # — so this tool must recompute and enforce the gate itself, exactly
    # like main() does, or it can produce a report.md the live pipeline
    # would have refused to write.
    shortcut_tools = find_malicious_only_tools(result.metric_cases)
    if shortcut_tools:
        raise ValueError(
            f"tool->label shortcut check failed: tool(s) {sorted(shortcut_tools)} appear "
            f"only in malicious metric_cases' observed transcripts — refusing to "
            f"regenerate report.md (anti-shortcut gate, mirrors run_batch.py::main())"
        )

    prov = provenance.read_provenance(run_output_dir)

    # C1 (final review, was: this tool never forwarded tool_name/vendor to
    # render_report, so it silently regenerated every report with the aidr
    # defaults — including for a llamafirewall run). The vendor must come
    # from THIS run's own recorded provenance, never a code default
    # (SPIRIT.md principle 8, run_batch.py's --vendor is likewise always
    # explicit, never a persisted/implicit choice). A run whose provenance
    # doesn't say which vendor produced it (missing file, or a vendor value
    # this checkout doesn't recognize) must refuse rather than guess.
    vendor = prov.get("vendor") if prov else None
    if not vendor:
        raise ValueError(
            f"{run_output_dir} has no vendor recorded in provenance.json (file missing, or no "
            f"'vendor' field) — refusing to regenerate a report without knowing which vendor "
            f"produced this run; silently defaulting to aidr is exactly the defect this fix "
            f"exists to remove (SPIRIT.md principle 8)"
        )
    if vendor not in VENDOR_DETECTOR_CONFIG:
        raise ValueError(
            f"provenance.json at {run_output_dir} declares vendor {vendor!r}, which is not one "
            f"of this checkout's known vendors ({sorted(VENDOR_DETECTOR_CONFIG)}) — refusing to "
            f"regenerate a report for an unrecognized vendor"
        )
    detector_config = VENDOR_DETECTOR_CONFIG[vendor]

    metrics = compute_metrics(result.metric_cases, result.metric_verdicts)
    setup_notes = _setup_notes(result, AGENT_TIMEOUT_S, DETECTOR_TIMEOUT_S, BREAKER_THRESHOLD, prov)
    return render_report(
        result.cases,
        result.verdicts,
        metrics,
        tool_name=detector_config.tool_name,
        vendor=vendor,
        setup_notes=setup_notes,
        transcript_unusable=result.transcript_unusable,
        provenance=prov,
    )


def main(argv: list[str] | None = None) -> None:
    _assert_running_from_this_working_tree()
    args = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="python -m toy_agent.regenerate_report")
    parser.add_argument("dataset_dir")
    parser.add_argument("run_output_dir")
    parsed = parser.parse_args(args)

    dataset_dir = Path(parsed.dataset_dir)
    run_output_dir = Path(parsed.run_output_dir)

    report = regenerate(dataset_dir, run_output_dir)
    (run_output_dir / "report.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
