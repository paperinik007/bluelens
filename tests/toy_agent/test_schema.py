import pytest

from toy_agent.schema import ToolCall, Turn, Transcript, TestCase, Verdict, validate_unique_case_ids


def _transcript() -> Transcript:
    return Transcript(session_id="sess_1", turns=[Turn(seq=0, role="user", content="hello")])


def test_tool_call_valid_status():
    tc = ToolCall(tool_name="query_customer_db", arguments={"customer_id": "cust_001"}, result="ok", status="ok")
    assert tc.status == "ok"


def test_tool_call_rejects_invalid_status():
    with pytest.raises(ValueError):
        ToolCall(tool_name="x", arguments={}, result=None, status="weird")


def test_turn_rejects_invalid_role():
    with pytest.raises(ValueError):
        Turn(seq=0, role="system", content="x")


def test_turn_tool_role_requires_tool_call():
    with pytest.raises(ValueError):
        Turn(seq=0, role="tool", content="x")


def test_turn_non_tool_role_rejects_tool_call():
    tc = ToolCall(tool_name="x", arguments={}, result=None, status="ok")
    with pytest.raises(ValueError):
        Turn(seq=0, role="user", content="x", tool_call=tc)


def test_testcase_benign_requires_no_technique_target():
    with pytest.raises(ValueError):
        TestCase(case_id="c1", transcript=_transcript(), label="benign", technique_target="T0002", rationale="r")


def test_testcase_malicious_requires_technique_target():
    with pytest.raises(ValueError):
        TestCase(case_id="c1", transcript=_transcript(), label="malicious", technique_target=None, rationale="r")


def test_testcase_requires_nonempty_rationale():
    with pytest.raises(ValueError):
        TestCase(case_id="c1", transcript=_transcript(), label="benign", technique_target=None, rationale="   ")


def test_verdict_error_status_requires_no_label():
    with pytest.raises(ValueError):
        Verdict(case_id="c1", tool_name="toy_support", status="error", label="benign")


def test_verdict_ok_status_requires_label():
    with pytest.raises(ValueError):
        Verdict(case_id="c1", tool_name="toy_support", status="ok", label=None)


def test_verdict_confidence_out_of_range_rejected():
    with pytest.raises(ValueError):
        Verdict(case_id="c1", tool_name="toy_support", status="ok", label="benign", confidence=1.5)


def test_verdict_negative_cost_rejected():
    with pytest.raises(ValueError):
        Verdict(case_id="c1", tool_name="toy_support", status="ok", label="benign", cost_usd=-1.0)


def test_verdict_valid_error_case():
    v = Verdict(case_id="c1", tool_name="toy_support", status="error")
    assert v.label is None


def test_validate_unique_case_ids_detects_duplicates():
    cases = [
        TestCase(case_id="c1", transcript=_transcript(), label="benign", technique_target=None, rationale="r"),
        TestCase(case_id="c1", transcript=_transcript(), label="benign", technique_target=None, rationale="r2"),
    ]
    with pytest.raises(ValueError):
        validate_unique_case_ids(cases)


def test_validate_unique_case_ids_accepts_distinct_ids():
    cases = [
        TestCase(case_id="c1", transcript=_transcript(), label="benign", technique_target=None, rationale="r"),
        TestCase(case_id="c2", transcript=_transcript(), label="benign", technique_target=None, rationale="r2"),
    ]
    validate_unique_case_ids(cases)  # must not raise
