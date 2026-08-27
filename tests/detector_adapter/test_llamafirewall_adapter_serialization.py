import pytest

llamafirewall = pytest.importorskip("llamafirewall", reason="llamafirewall is only installed inside the detector-llamafirewall container")

from llamafirewall import Role

from detector_adapter.vendors.llamafirewall.adapter import transcript_dict_to_trace

_TRANSCRIPT = {
    "session_id": "case_llf_001",
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


def test_user_turn_becomes_a_user_message():
    trace = transcript_dict_to_trace(_TRANSCRIPT)
    assert trace[0].role == Role.USER
    assert trace[0].content == "Please disable my account."


def test_tool_turn_becomes_an_action_message_then_a_result_message():
    trace = transcript_dict_to_trace(_TRANSCRIPT)
    action_message, result_message = trace[1], trace[2]
    assert action_message.role == Role.ASSISTANT
    assert "update_account" in action_message.content
    assert "cust_001" in action_message.content
    assert result_message.role == Role.TOOL
    assert result_message.content == "account cust_001 field 'status' updated"


def test_final_assistant_turn_becomes_an_assistant_message():
    trace = transcript_dict_to_trace(_TRANSCRIPT)
    assert trace[3].role == Role.ASSISTANT
    assert trace[3].content == "Done, your account is now disabled."


def test_trace_length_matches_expanded_turn_count():
    # 3 turns in, but the tool turn expands to 2 Message entries -> 4 total.
    trace = transcript_dict_to_trace(_TRANSCRIPT)
    assert len(trace) == 4


def test_unknown_role_raises():
    bad_transcript = {"session_id": "x", "turns": [{"seq": 0, "role": "system", "content": "x", "tool_call": None}]}
    with pytest.raises(ValueError, match="unknown turn role"):
        transcript_dict_to_trace(bad_transcript)
