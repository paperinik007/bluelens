import json
from pathlib import Path

import pytest

from toy_agent.prepare_judge_input import judge_input, prepare

REAL = Path(__file__).resolve().parents[2] / "docs/research/2026-10-22-prova-generale-agente/sessioni"


def _session(case_id="v3_x01", sid="a1b2", version="honest", content="hello"):
    return {"case_id": case_id, "third_party_version": version, "state_after": {"secret": 1}, "call_log": [{"m": 1}],
            "transcript": {"session_id": sid, "turns": [{"seq": 0, "role": "user", "content": content}], "stop_reason": "completed"}}


def test_the_judge_reads_the_transcript_at_the_top_level_plus_the_integration_version_and_nothing_else():
    data = judge_input(_session(version="compromised_data"))
    assert set(data) == {"session_id", "turns", "stop_reason", "third_party_version"}
    assert data["third_party_version"] == "compromised_data"


def test_the_case_id_state_and_call_log_never_reach_the_judge():
    text = json.dumps(judge_input(_session()))
    for hidden in ("v3_x01", "secret", "call_log", "state_after", "case_id"):
        assert hidden not in text


def test_a_case_id_that_leaks_into_the_transcript_stops_the_preparation():
    with pytest.raises(ValueError, match="appears"):
        judge_input(_session(content="this is v3_x01"))


def test_prepare_writes_one_file_per_opaque_id_and_the_map_outside_the_judge_folder(tmp_path):
    src = tmp_path / "s"; src.mkdir()
    (src / "v3_x01_1.json").write_text(json.dumps(_session(sid="aaa")))
    (src / "v3_x01_2.json").write_text(json.dumps(_session(sid="bbb")))
    out = tmp_path / "judge"
    mapping = prepare(src, out, tmp_path / "map.json")
    assert sorted(p.name for p in out.glob("*.json")) == ["aaa.json", "bbb.json"]
    assert mapping["aaa"] == {"case_id": "v3_x01", "file": "v3_x01_1.json"}
    assert json.loads((tmp_path / "map.json").read_text())["bbb"]["file"] == "v3_x01_2.json"


def test_the_map_cannot_be_written_inside_the_judge_folder(tmp_path):
    src = tmp_path / "s"; src.mkdir()
    (src / "a.json").write_text(json.dumps(_session()))
    with pytest.raises(ValueError, match="inside"):
        prepare(src, tmp_path / "judge", tmp_path / "judge" / "map.json")


def test_two_sessions_with_the_same_id_stop_the_preparation(tmp_path):
    src = tmp_path / "s"; src.mkdir()
    (src / "a.json").write_text(json.dumps(_session(sid="same")))
    (src / "b.json").write_text(json.dumps(_session(sid="same")))
    with pytest.raises(ValueError, match="share"):
        prepare(src, tmp_path / "judge", tmp_path / "map.json")


@pytest.mark.skipif(not REAL.exists(), reason="rehearsal sessions not present")
def test_all_174_rehearsal_sessions_prepare_without_a_leak(tmp_path):
    mapping = prepare(REAL, tmp_path / "judge", tmp_path / "map.json")
    assert len(mapping) == 174
