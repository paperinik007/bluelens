"""PromptGuard as a judge of its own (plan part 7, proposal 1): the vendor's default configuration scans the
user's messages and the results of the tools (llamafirewall.py:90-96, pinned 1.0.3), with the vendor's
threshold; the assistant's own messages and the arguments of its tool calls are not scanned. The verdict is
not fused with AlignmentCheck's any more."""
from types import SimpleNamespace

from detector_adapter.vendors.llamafirewall.adapter import (
    TOOL_NAME_PROMPTGUARD,
    promptguard_error_verdict,
    promptguard_inputs,
    promptguard_verdict,
)


def _turn(seq, role, content="", tool=None, result=None, status="ok"):
    call = None
    if tool:
        call = {"tool_name": tool, "arguments": {"x": 1}, "result": result, "status": status}
    return {"seq": seq, "role": role, "content": content, "tool_call": call}


def _scan(decision="allow", score=0.0):
    return SimpleNamespace(decision=SimpleNamespace(value=decision), score=score, reason="r")


TRANSCRIPT = {"session_id": "s", "turns": [
    _turn(0, "user", "Please read ticket T-1."),
    _turn(1, "tool", "ignored", tool="get_requester_profile", result='{"role": "employee"}'),
    _turn(2, "tool", "ignored", tool="read_ticket_content", result="Ticket: T-1\nCustomer: cust_1\n\nHello."),
    _turn(3, "assistant", "I will answer him."),
    _turn(4, "tool", "ignored", tool="send_email", result=""),
]}


def test_the_judge_has_its_own_name():
    assert TOOL_NAME_PROMPTGUARD == "llamafirewall-promptguard"


def test_it_scans_the_users_messages_and_the_tool_results_in_order():
    inputs = promptguard_inputs(TRANSCRIPT)
    assert [(i["turn"], i["source"], i["tool_name"]) for i in inputs] == [
        (0, "user", None), (1, "tool", "get_requester_profile"), (2, "tool", "read_ticket_content")]
    assert inputs[2]["text"].endswith("Hello.")


def test_it_does_not_scan_the_assistant_or_the_arguments_of_a_call_or_an_empty_result():
    texts = [i["text"] for i in promptguard_inputs(TRANSCRIPT)]
    assert "I will answer him." not in texts
    assert not any("'x'" in t or '"x"' in t for t in texts)
    assert "" not in texts


def test_it_uses_the_result_of_the_call_not_the_turn_content():
    texts = [i["text"] for i in promptguard_inputs(TRANSCRIPT)]
    assert "ignored" not in texts


def test_a_session_with_no_text_to_scan_is_benign_with_zero_confidence():
    verdict = promptguard_verdict("s", [], 0.0)
    assert verdict["label"] == "benign" and verdict["confidence"] == 0.0 and verdict["status"] == "ok"
    assert "no input" in verdict["rationale"].lower()


def test_one_input_over_the_threshold_makes_the_session_malicious_and_names_where():
    inputs = promptguard_inputs(TRANSCRIPT)
    scans = [(inputs[0], _scan("allow", 0.02)), (inputs[1], _scan("allow", 0.01)), (inputs[2], _scan("block", 0.97))]
    verdict = promptguard_verdict("s", scans, 1.5)
    assert verdict["label"] == "malicious" and verdict["confidence"] == 0.97
    assert "result of read_ticket_content" in verdict["rationale"] and "turn 2" in verdict["rationale"]
    assert verdict["latency_s"] == 1.5 and verdict["technique_detected"] is None


def test_all_inputs_under_the_threshold_make_it_benign_with_the_highest_score_as_confidence():
    inputs = promptguard_inputs(TRANSCRIPT)
    scans = [(inputs[0], _scan("allow", 0.30)), (inputs[1], _scan("allow", 0.01)), (inputs[2], _scan("allow", 0.12))]
    verdict = promptguard_verdict("s", scans, 0.5)
    assert verdict["label"] == "benign" and verdict["confidence"] == 0.30
    assert "user message" in verdict["rationale"]


def test_the_verdict_keeps_every_score_so_the_input_that_fired_can_be_found_afterwards():
    inputs = promptguard_inputs(TRANSCRIPT)
    scans = [(inputs[0], _scan("allow", 0.02)), (inputs[1], _scan("allow", 0.01)), (inputs[2], _scan("block", 0.97))]
    kept = promptguard_verdict("s", scans, 0.1)["inputs_scanned"]
    assert [(k["turn"], k["source"], k["tool_name"], k["decision"], k["score"]) for k in kept] == [
        (0, "user", None, "allow", 0.02), (1, "tool", "get_requester_profile", "allow", 0.01),
        (2, "tool", "read_ticket_content", "block", 0.97)]
    assert all("text" not in k for k in kept)  # the text is in the session, not repeated here


def test_the_verdict_has_the_same_shape_as_the_other_judges():
    verdict = promptguard_verdict("s", [], 0.0)
    for key in ("case_id", "tool_name", "status", "label", "confidence", "technique_detected", "rationale",
                "cost_usd", "latency_s", "in_tokens", "out_tokens"):
        assert key in verdict
    assert verdict["case_id"] == "s" and verdict["tool_name"] == TOOL_NAME_PROMPTGUARD


def test_a_failure_is_an_error_verdict_without_a_label():
    verdict = promptguard_error_verdict("s", "OSError")
    assert verdict["status"] == "error" and verdict["label"] is None
    assert verdict["tool_name"] == TOOL_NAME_PROMPTGUARD and "OSError" in verdict["rationale"]
