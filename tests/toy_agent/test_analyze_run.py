import json
from pathlib import Path

import pytest
import yaml

from toy_agent.analyze_run import analyze_run, render_analysis


def _write_dataset(dataset_dir: Path, entries: list[dict]) -> None:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        (dataset_dir / f"{entry['case_id']}.yaml").write_text(
            yaml.safe_dump(entry), encoding="utf-8"
        )


def _write_verdicts_jsonl(run_dir: Path, verdicts: list[dict]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "verdicts.jsonl").open("w", encoding="utf-8") as f:
        for v in verdicts:
            f.write(json.dumps(v) + "\n")


def _write_transcript(run_dir: Path, case_id: str, turns: list[dict]) -> None:
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"{case_id}.transcript.json").write_text(
        json.dumps({"session_id": case_id, "turns": turns, "stop_reason": "completed"}),
        encoding="utf-8",
    )


# --- Intent-based classification ---

def test_intent_metrics_group_by_dataset_label(tmp_path):
    dataset_dir = tmp_path / "dataset"
    run_dir = tmp_path / "run"
    _write_dataset(
        dataset_dir,
        [
            {
                "case_id": "m1",
                "label": "malicious",
                "technique_target": "T0001",
                "rationale": "r",
                "attack_success_criteria": {"always": True},
                "transcript": {
                    "session_id": "m1",
                    "turns": [{"seq": 0, "role": "user", "content": "hi"}],
                    "stop_reason": None,
                },
            },
            {
                "case_id": "b1",
                "label": "benign",
                "technique_target": None,
                "rationale": "r",
                "transcript": {
                    "session_id": "b1",
                    "turns": [{"seq": 0, "role": "user", "content": "hi"}],
                    "stop_reason": None,
                },
            },
        ],
    )
    _write_verdicts_jsonl(
        run_dir,
        [
            {"case_id": "m1", "tool_name": "agentic_threat_detection", "status": "ok", "label": "malicious", "technique_detected": "T0001"},
            {"case_id": "b1", "tool_name": "agentic_threat_detection", "status": "ok", "label": "benign"},
        ],
    )
    _write_transcript(run_dir, "m1", turns=[])
    _write_transcript(run_dir, "b1", turns=[])

    data = analyze_run(dataset_dir, run_dir)

    assert data["intent"]["tp"] == 1
    assert data["intent"]["fp"] == 0
    assert data["intent"]["fn"] == 0
    assert data["intent"]["tn"] == 1
    assert data["intent"]["precision"] == 1.0


def test_intent_records_fn_when_detector_misses_a_malicious_label(tmp_path):
    dataset_dir = tmp_path / "dataset"
    run_dir = tmp_path / "run"
    _write_dataset(
        dataset_dir,
        [
            {
                "case_id": "m1",
                "label": "malicious",
                "technique_target": "T0001",
                "rationale": "r",
                "attack_success_criteria": {"always": True},
                "transcript": {
                    "session_id": "m1",
                    "turns": [{"seq": 0, "role": "user", "content": "hi"}],
                    "stop_reason": None,
                },
            },
        ],
    )
    _write_verdicts_jsonl(run_dir, [
        {"case_id": "m1", "tool_name": "agentic_threat_detection", "status": "ok", "label": "benign"},
    ])
    _write_transcript(run_dir, "m1", turns=[])

    data = analyze_run(dataset_dir, run_dir)

    assert data["intent"]["tp"] == 0
    assert data["intent"]["fn"] == 1


# --- Effect-based classification ---

def test_effect_reclassifies_fp_when_attack_was_refused(tmp_path):
    dataset_dir = tmp_path / "dataset"
    run_dir = tmp_path / "run"
    # attack_success_criteria requires a tool call that never happens
    _write_dataset(
        dataset_dir,
        [
            {
                "case_id": "m1",
                "label": "malicious",
                "technique_target": "T0003",
                "rationale": "r",
                "attack_success_criteria": {
                    "tool_call": {"tool_name": "send_email", "arguments": {}, "min_count": 1},
                },
                "transcript": {
                    "session_id": "m1",
                    "turns": [{"seq": 0, "role": "user", "content": "hi"}],
                    "stop_reason": None,
                },
            },
        ],
    )
    _write_verdicts_jsonl(run_dir, [
        {"case_id": "m1", "tool_name": "agentic_threat_detection", "status": "ok", "label": "malicious", "technique_detected": "T0007"},
    ])
    _write_transcript(
        run_dir, "m1",
        turns=[{"seq": 0, "role": "user", "content": "hi"}],
    )

    data = analyze_run(dataset_dir, run_dir)

    # intent says TP (label=malevolo + detector=malevolo)
    assert data["intent"]["tp"] == 1
    # effect says FP: attack never succeeded, but detector flagged it anyway
    assert data["effect"]["tp"] == 0
    assert data["effect"]["fp"] == 1
    assert data["effect"]["tn"] == 0
    assert data["effect"]["fn"] == 0

    # divergence table must include this case
    diverged = [p for p in data["divergence"] if p["case_id"] == "m1"]
    assert len(diverged) == 1
    assert diverged[0]["intent_class"] == "TP"
    assert diverged[0]["effect_class"] == "FP"


def test_effect_tp_when_attack_succeeded_and_detector_agrees(tmp_path):
    dataset_dir = tmp_path / "dataset"
    run_dir = tmp_path / "run"
    _write_dataset(
        dataset_dir,
        [
            {
                "case_id": "m1",
                "label": "malicious",
                "technique_target": "T0001",
                "rationale": "r",
                "attack_success_criteria": {"always": True},
                "transcript": {
                    "session_id": "m1",
                    "turns": [{"seq": 0, "role": "user", "content": "hi"}],
                    "stop_reason": None,
                },
            },
        ],
    )
    _write_verdicts_jsonl(run_dir, [
        {"case_id": "m1", "tool_name": "agentic_threat_detection", "status": "ok", "label": "malicious", "technique_detected": "T0001"},
    ])
    _write_transcript(run_dir, "m1", turns=[])

    data = analyze_run(dataset_dir, run_dir)

    assert data["effect"]["tp"] == 1
    assert data["effect"]["tp_strict"] == 1


def test_effect_fn_when_attack_succeeded_but_detector_missed(tmp_path):
    dataset_dir = tmp_path / "dataset"
    run_dir = tmp_path / "run"
    _write_dataset(
        dataset_dir,
        [
            {
                "case_id": "m1",
                "label": "malicious",
                "technique_target": "T0012",
                "rationale": "r",
                "attack_success_criteria": {"always": True},
                "transcript": {
                    "session_id": "m1",
                    "turns": [{"seq": 0, "role": "user", "content": "hi"}],
                    "stop_reason": None,
                },
            },
        ],
    )
    _write_verdicts_jsonl(run_dir, [
        {"case_id": "m1", "tool_name": "agentic_threat_detection", "status": "ok", "label": "benign"},
    ])
    _write_transcript(run_dir, "m1", turns=[])

    data = analyze_run(dataset_dir, run_dir)

    assert data["effect"]["tp"] == 0
    assert data["effect"]["fn"] == 1


# --- Benign cases ---

def test_benign_case_counts_as_tn_in_both_metrics(tmp_path):
    dataset_dir = tmp_path / "dataset"
    run_dir = tmp_path / "run"
    _write_dataset(
        dataset_dir,
        [
            {
                "case_id": "b1",
                "label": "benign",
                "technique_target": None,
                "rationale": "r",
                "transcript": {
                    "session_id": "b1",
                    "turns": [{"seq": 0, "role": "user", "content": "hi"}],
                    "stop_reason": None,
                },
            },
        ],
    )
    _write_verdicts_jsonl(run_dir, [
        {"case_id": "b1", "tool_name": "agentic_threat_detection", "status": "ok", "label": "benign"},
    ])
    _write_transcript(run_dir, "b1", turns=[])

    data = analyze_run(dataset_dir, run_dir)

    assert data["intent"]["tn"] == 1
    assert data["effect"]["tn"] == 1


# --- Edge cases ---

def test_missing_verdicts_jsonl_raises(tmp_path):
    dataset_dir = tmp_path / "dataset"
    run_dir = tmp_path / "run"
    _write_dataset(
        dataset_dir,
        [
            {
                "case_id": "m1",
                "label": "malicious",
                "technique_target": "T0001",
                "rationale": "r",
                "attack_success_criteria": {"always": True},
                "transcript": {"session_id": "m1", "turns": [], "stop_reason": None},
            },
        ],
    )
    with pytest.raises(ValueError, match="verdicts.jsonl"):
        analyze_run(dataset_dir, run_dir)


def test_missing_transcript_does_not_crash(tmp_path):
    dataset_dir = tmp_path / "dataset"
    run_dir = tmp_path / "run"
    _write_dataset(
        dataset_dir,
        [
            {
                "case_id": "m1",
                "label": "malicious",
                "technique_target": "T0001",
                "rationale": "r",
                "attack_success_criteria": {"always": True},
                "transcript": {"session_id": "m1", "turns": [{"seq": 0, "role": "user", "content": "hi"}], "stop_reason": None},
            },
        ],
    )
    _write_verdicts_jsonl(run_dir, [
        {"case_id": "m1", "tool_name": "agentic_threat_detection", "status": "ok", "label": "benign"},
    ])
    # no _write_transcript call — transcript file missing on disk

    data = analyze_run(dataset_dir, run_dir)

    assert data["effect"]["fn"] == 0  # attack_succeeded stays False
    assert data["cases"][0]["transcript_error"] == "transcript file missing"


# --- Render output ---

def test_render_output_mentions_both_metrics():
    data = {
        "run_dir": "/tmp/run",
        "total_cases": 0,
        "total_malicious": 0,
        "total_benign": 0,
        "attacks_succeeded": 0,
        "effect": {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "tp_strict": 0, "precision": None, "recall": None},
        "intent": {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "precision": None, "recall": None},
        "divergence": [],
        "cases": [],
    }
    out = render_analysis(data)
    assert "Effect-based" in out
    assert "Intent-based" in out
    assert "Where intent and effect diverge" in out