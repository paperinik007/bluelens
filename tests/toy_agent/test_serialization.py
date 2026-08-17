import pytest

from toy_agent.run_case import transcript_to_dict
from toy_agent.schema import ToolCall, Transcript, Turn, Verdict
from toy_agent.serialization import transcript_from_dict, verdict_from_dict


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
