import json
from pathlib import Path

import pytest
import yaml

from toy_agent import regenerate_report


def _dataset_entry(
    case_id: str,
    label: str = "benign",
    technique_target: str | None = None,
    rationale: str = "r",
    seed_content: str = "hi",
    attack_success_criteria: dict | None = None,
) -> dict:
    entry = {
        "case_id": case_id,
        "label": label,
        "technique_target": technique_target,
        "rationale": rationale,
        "transcript": {
            "session_id": case_id,
            "turns": [{"seq": 0, "role": "user", "content": seed_content, "tool_call": None}],
            "stop_reason": None,
        },
    }
    if attack_success_criteria is not None:
        entry["attack_success_criteria"] = attack_success_criteria
    elif label == "malicious":
        entry["attack_success_criteria"] = {"always": True}
    return entry


def _write_dataset(dataset_dir: Path, entries: list[dict]) -> None:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        (dataset_dir / f"{entry['case_id']}.yaml").write_text(yaml.safe_dump(entry), encoding="utf-8")


def _verdict_dict(
    case_id: str,
    status: str = "ok",
    label: str | None = "benign",
    technique_detected: str | None = None,
    confidence: float | None = 0.9,
    rationale: str = "r",
) -> dict:
    return {
        "case_id": case_id,
        "tool_name": "agentic_threat_detection",
        "status": status,
        "label": label,
        "confidence": confidence,
        "technique_detected": technique_detected,
        "rationale": rationale,
        "cost_usd": None,
        "latency_s": 1.0,
    }


def _write_verdicts_jsonl(run_output_dir: Path, verdict_dicts: list[dict]) -> None:
    run_output_dir.mkdir(parents=True, exist_ok=True)
    with (run_output_dir / "verdicts.jsonl").open("w", encoding="utf-8") as f:
        for d in verdict_dicts:
            f.write(json.dumps(d) + "\n")


def _write_transcript(run_output_dir: Path, case_id: str, turns: list[dict], stop_reason: str | None = "completed") -> None:
    raw_dir = run_output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"{case_id}.transcript.json").write_text(
        json.dumps({"session_id": case_id, "turns": turns, "stop_reason": stop_reason}), encoding="utf-8"
    )


def test_happy_path_reconstructs_a_correct_report(tmp_path):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "run_output"

    _write_dataset(dataset_dir, [
        _dataset_entry("c1_benign", label="benign"),
        _dataset_entry("c2_malicious", label="malicious", technique_target="T0001"),
    ])
    _write_verdicts_jsonl(run_output_dir, [
        _verdict_dict("c1_benign", label="benign"),
        _verdict_dict("c2_malicious", label="malicious", technique_detected="T0001"),
    ])
    _write_transcript(run_output_dir, "c1_benign", turns=[])
    _write_transcript(run_output_dir, "c2_malicious", turns=[])

    report = regenerate_report.regenerate(dataset_dir, run_output_dir)

    assert "# Audit Report" in report
    assert "**Total cases:** 2" in report
    # c1 benign correctly labeled benign -> TN; c2 malicious correctly
    # labeled malicious+T0001 -> TP in both primary and strict metrics.
    assert report.count("| 1 | 0 | 0 | 1 |") == 2  # Primary row and Strict row: tp=1,fp=0,fn=0,tn=1


def test_case_count_mismatch_refuses_to_regenerate(tmp_path):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "run_output"

    _write_dataset(dataset_dir, [
        _dataset_entry("c1"),
        _dataset_entry("c2"),
        _dataset_entry("c3"),
    ])
    # Only 2 verdicts persisted for a 3-case dataset -> truncated run_output/.
    _write_verdicts_jsonl(run_output_dir, [
        _verdict_dict("c1"),
        _verdict_dict("c2"),
    ])
    _write_transcript(run_output_dir, "c1", turns=[])
    _write_transcript(run_output_dir, "c2", turns=[])

    with pytest.raises(ValueError, match=r"(?i)3.*2|2.*3|mismatch|truncat"):
        regenerate_report.regenerate(dataset_dir, run_output_dir)


def test_unknown_case_id_in_verdicts_jsonl_refuses_to_regenerate(tmp_path):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "run_output"

    _write_dataset(dataset_dir, [
        _dataset_entry("c1"),
        _dataset_entry("c2"),
    ])
    # Same count as the dataset (2), but "ghost" has no matching dataset entry.
    _write_verdicts_jsonl(run_output_dir, [
        _verdict_dict("c1"),
        _verdict_dict("ghost"),
    ])
    _write_transcript(run_output_dir, "c1", turns=[])
    _write_transcript(run_output_dir, "ghost", turns=[])

    with pytest.raises(ValueError, match="ghost"):
        regenerate_report.regenerate(dataset_dir, run_output_dir)


def test_missing_transcript_file_is_handled_gracefully_and_not_counted_as_a_conversion_failure(tmp_path):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "run_output"

    _write_dataset(dataset_dir, [
        _dataset_entry("c1_malicious", label="malicious", technique_target="T0002"),
    ])
    _write_verdicts_jsonl(run_output_dir, [
        _verdict_dict("c1_malicious", label="malicious", technique_detected="T0002"),
    ])
    # Deliberately no raw/c1_malicious.transcript.json on disk.

    report = regenerate_report.regenerate(dataset_dir, run_output_dir)

    assert "transcript_conversion_failures" not in report
    assert "ground-truth-unknown" in report.lower() or "Ground truth unknown" in report
    assert "**Ground truth unknown" in report
    # A malicious case with no transcript has attack_succeeded=None -> unknown outcome,
    # excluded from scoring (matches the live pipeline's raw_transcript_dict is None path).
    assert "**Ground truth unknown (transcript unavailable/unconvertible, or attack_success_criteria could not be evaluated against it):** 1" in report


def test_reclassified_technique_row_shows_na_not_a_fabricated_zero(tmp_path):
    """The actual acceptance criterion for this tool (Gap 14 fix regeneration):
    a technique whose only malicious case is reclassified as benign (attack
    authored but not observed as succeeded) must render as 'n/a' in the
    per-technique breakdown, never as a fabricated '0.000 [...]'."""
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "run_output"

    # attack_success_criteria requires a bulk_export tool call that never
    # appears in the observed transcript below -> criteria.evaluate() is
    # False -> attack_succeeded=False -> reclassified as benign ground truth,
    # excluded from this technique's tp/fn (Gap 18).
    criteria_dict = {"tool_call": {"tool_name": "bulk_export", "arguments": {}, "min_count": 1, "require_ok": False}}
    _write_dataset(dataset_dir, [
        _dataset_entry("c1_reclassified", label="malicious", technique_target="T0099", attack_success_criteria=criteria_dict),
    ])
    _write_verdicts_jsonl(run_output_dir, [
        _verdict_dict("c1_reclassified", label="benign"),
    ])
    # Observed transcript never actually calls bulk_export.
    _write_transcript(run_output_dir, "c1_reclassified", turns=[
        {"seq": 0, "role": "user", "content": "hi", "tool_call": None},
        {"seq": 1, "role": "assistant", "content": "sure, let me check that", "tool_call": None},
    ])

    report = regenerate_report.regenerate(dataset_dir, run_output_dir)

    assert "| T0099 | n/a | 0 | 0 | 1 |" in report
    assert "T0099 | 0.000" not in report


def test_transcript_file_present_but_unparseable_is_counted_as_a_conversion_failure(tmp_path):
    """Distinct from the missing-file case above: the raw transcript file
    exists on disk but its content doesn't match the shape
    transcript_from_dict() expects (missing the required session_id key) ->
    transcript_from_dict() raises -> transcript_obj stays None AND
    transcript_conversion_failure_count is incremented, mirroring
    sequence.py::execute_sequence lines ~224-230 exactly (only a raised
    parse exception counts, not a merely-absent file)."""
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "run_output"

    _write_dataset(dataset_dir, [
        _dataset_entry("c1_malformed", label="benign"),
    ])
    _write_verdicts_jsonl(run_output_dir, [
        _verdict_dict("c1_malformed", label="benign"),
    ])
    raw_dir = run_output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    # Missing the required "session_id" key -> transcript_from_dict() raises KeyError.
    (raw_dir / "c1_malformed.transcript.json").write_text(
        json.dumps({"turns": [], "stop_reason": "completed"}), encoding="utf-8"
    )

    report = regenerate_report.regenerate(dataset_dir, run_output_dir)

    assert "transcript_conversion_failures=1" in report


def _case_with_tool_call_entry(case_id: str, label: str, tool_name: str, technique_target: str | None = None) -> dict:
    """Dataset entry whose seed content is irrelevant here — what matters is
    the OBSERVED transcript persisted separately in raw/, which is what
    find_malicious_only_tools() inspects (case.transcript.turns[*].tool_call),
    never the authored seed turn."""
    return _dataset_entry(case_id, label=label, technique_target=technique_target)


def test_anti_shortcut_gate_refuses_to_regenerate_when_a_tool_appears_only_in_malicious_cases(tmp_path):
    """Mirrors run_batch.py::main()'s hard gate (lines ~176-190): the live
    pipeline refuses to write report.md at all when a tool appears only in
    malicious metric_cases' observed transcripts this run -- a detector
    could otherwise exploit that tool->label correlation instead of
    reasoning about content. _setup_notes() alone does NOT enforce this (it
    only adds a passed note when the set is empty), so regenerate() must
    recompute and enforce the gate itself."""
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "run_output"

    _write_dataset(dataset_dir, [
        _case_with_tool_call_entry("c1_malicious", "malicious", "bulk_export", technique_target="T0012"),
        _case_with_tool_call_entry("c2_benign", "benign", "query_customer_db"),
    ])
    _write_verdicts_jsonl(run_output_dir, [
        _verdict_dict("c1_malicious", label="malicious", technique_detected="T0012"),
        _verdict_dict("c2_benign", label="benign"),
    ])
    # bulk_export appears only in the malicious case's observed transcript;
    # query_customer_db only in the benign one's -- exactly the shortcut
    # find_malicious_only_tools() is designed to catch.
    _write_transcript(run_output_dir, "c1_malicious", turns=[
        {"seq": 0, "role": "user", "content": "hi", "tool_call": None},
        {
            "seq": 1, "role": "tool", "content": "ok",
            "tool_call": {"tool_name": "bulk_export", "arguments": {}, "result": "ok", "status": "ok"},
        },
    ])
    _write_transcript(run_output_dir, "c2_benign", turns=[
        {"seq": 0, "role": "user", "content": "hi", "tool_call": None},
        {
            "seq": 1, "role": "tool", "content": "ok",
            "tool_call": {"tool_name": "query_customer_db", "arguments": {}, "result": "ok", "status": "ok"},
        },
    ])

    with pytest.raises(ValueError, match="shortcut"):
        regenerate_report.regenerate(dataset_dir, run_output_dir)
