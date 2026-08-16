import pytest

aidr = pytest.importorskip("aidr", reason="aidr is only installed inside the detector container (docker/detector/Dockerfile)")

from detector_adapter.adapter import transcript_dict_to_agent_event

_TRANSCRIPT = {
    "session_id": "case_007",
    "turns": [
        {"seq": 0, "role": "user", "content": "Please disable my account.", "tool_call": None},
        {
            "seq": 1, "role": "tool", "content": "account cust_001 field 'status' updated",
            "tool_call": {
                "tool_name": "update_account",
                "arguments": {"customer_id": "cust_001", "field": "status", "value": "disabled"},
                "result": "account cust_001 field 'status' updated",
                "status": "ok",
            },
        },
        {"seq": 2, "role": "assistant", "content": "Done, your account is now disabled.", "tool_call": None},
    ],
    "stop_reason": "completed",
}


def test_agent_event_carries_session_id_and_declares_toy_support():
    ev = transcript_dict_to_agent_event(_TRANSCRIPT)
    assert ev.session_id == "case_007"
    assert ev.declared_servers == ["toy_support"]


def test_tool_turn_produces_dotted_tool_name_and_a_result_message():
    ev = transcript_dict_to_agent_event(_TRANSCRIPT)
    calling = [m for m in ev.messages if m.message_type == "tool_calling"]
    assert len(calling) == 1
    usage = calling[0].tool_calls[0]
    assert usage.tool_name == "toy_support.update_account"
    assert usage.server_name == "toy_support"
    result_messages = [m for m in ev.messages if m.message_type == "tool_result"]
    assert result_messages[0].content == "account cust_001 field 'status' updated"


def test_transcript_string_contains_the_dotted_tool_name():
    # This is the exact signal Inspector's SourceLens step relies on (Gap 4) —
    # verified once empirically against a live Inspector in Plan 3, Task 6;
    # this test only pins the string-formatting contract that makes that
    # verification meaningful.
    ev = transcript_dict_to_agent_event(_TRANSCRIPT)
    assert "toy_support.update_account" in ev.transcript()
