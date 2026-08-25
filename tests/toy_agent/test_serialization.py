import json
from pathlib import Path

import pytest

from toy_agent.run_case import transcript_to_dict
from toy_agent.schema import ToolCall, Transcript, Turn, Verdict
from toy_agent.serialization import _tool_call_from_dict, transcript_from_dict, verdict_from_dict


def test_transcript_round_trips_through_dict():
    original = Transcript(
        session_id="sess_1",
        turns=[
            Turn(seq=0, role="user", content="hello"),
            Turn(
                seq=1,
                role="tool",
                content="",
                tool_call=ToolCall(tool_name="query_customer_db", arguments={"id": "1"}, result="ok", status="ok"),
            ),
        ],
        stop_reason="completed",
    )
    rebuilt = transcript_from_dict(transcript_to_dict(original))
    assert rebuilt == original


def test_transcript_from_dict_defaults_stop_reason_to_none():
    t = transcript_from_dict({"session_id": "s1", "turns": []})
    assert t.stop_reason is None
    assert t.turns == []


def test_verdict_from_dict_builds_an_ok_verdict():
    d = {
        "case_id": "c1", "tool_name": "agentic_threat_detection", "status": "ok",
        "label": "malicious", "confidence": 0.9, "technique_detected": "T0001",
        "rationale": "r", "cost_usd": None, "latency_s": 1.2,
    }
    v = verdict_from_dict(d)
    assert v.case_id == "c1"
    assert v.confidence == 0.9
    assert v.latency_s == 1.2


def test_verdict_from_dict_ignores_extra_keys_not_in_the_schema():
    d = {
        "case_id": "c1", "tool_name": "agentic_threat_detection", "status": "error",
        "error_kind": "infra", "rationale": "boom",
        "in_tokens": 100, "out_tokens": 50,
    }
    v = verdict_from_dict(d)
    assert v.status == "error"
    assert v.rationale == "boom"
    assert not hasattr(v, "error_kind")
    assert not hasattr(v, "in_tokens")


def test_verdict_from_dict_raises_on_out_of_range_confidence():
    d = {"case_id": "c1", "tool_name": "x", "status": "ok", "label": "malicious", "confidence": 1.5}
    with pytest.raises(ValueError):
        verdict_from_dict(d)


# --- R5: new fields in ToolCall & Transcript serialization ---

def test_tool_call_from_dict_defaults_the_new_fields_when_absent():
    """Dict without the new fields → arguments_parse_failed=False, raw_arguments=None."""
    d = {"tool_name": "x", "arguments": {}, "result": None, "status": "ok"}
    tc = _tool_call_from_dict(d)
    assert tc.arguments_parse_failed is False
    assert tc.raw_arguments is None


def test_tool_call_from_dict_reads_the_new_fields_when_present():
    """Dict with the new fields → values are read."""
    d = {
        "tool_name": "x", "arguments": {}, "result": None, "status": "error",
        "arguments_parse_failed": True, "raw_arguments": '{"filter": ',
    }
    tc = _tool_call_from_dict(d)
    assert tc.arguments_parse_failed is True
    assert tc.raw_arguments == '{"filter": '


def test_transcript_from_dict_defaults_model_retry_count_when_absent():
    """Dict without model_retry_count → defaults to 0."""
    t = transcript_from_dict({"session_id": "s1", "turns": []})
    assert t.model_retry_count == 0


def test_every_published_transcript_still_converts_after_the_schema_change():
    """All 31 raw transcripts must be readable; new fields default correctly."""
    raw_dir = Path("docs/reports/agentic-threat-detection-2026-08-19/raw")
    files = sorted(raw_dir.glob("*.transcript.json"))
    assert len(files) == 31, f"expected 31 transcripts, found {len(files)}"
    for path in files:
        d = json.loads(path.read_text())
        t = transcript_from_dict(d)
        assert t.model_retry_count == 0, f"{path.name}: model_retry_count should default to 0"
        for turn in t.turns:
            tc = turn.tool_call
            if tc is not None:
                assert tc.arguments_parse_failed is False, (
                    f"{path.name}: arguments_parse_failed should default to False"
                )
                assert tc.raw_arguments is None, (
                    f"{path.name}: raw_arguments should default to None"
                )
