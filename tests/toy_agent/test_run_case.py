import json
import uuid

import pytest

from toy_agent.model_client import ModelReply
from toy_agent.run_case import _extract_scenario, main, run_case, transcript_to_dict
from toy_agent.schema import Transcript, Turn, ToolCall
from toy_agent.serialization import transcript_from_dict


class FakeModelClient:
    def __init__(self, script):
        self._script = list(script)
        self.calls = 0

    def complete(self, messages, tools):
        self.calls += 1
        if not self._script:
            raise AssertionError("FakeModelClient script exhausted")
        return self._script.pop(0)


_SEED_INPUT = {
    "case_id": "case_001",
    "transcript": {
        "session_id": "case_001",
        "turns": [{"seq": 0, "role": "user", "content": "Can you help me?", "tool_call": None}],
        "stop_reason": None,
    },
    "label": "benign",
    "technique_target": None,
    "rationale": "smoke test seed",
}


def test_extract_scenario_reads_case_id_and_seed_content():
    case_id, scenario = _extract_scenario(_SEED_INPUT)
    assert case_id == "case_001"
    assert scenario == "Can you help me?"


def test_extract_scenario_rejects_missing_case_id():
    bad = {**_SEED_INPUT, "case_id": ""}
    with pytest.raises(ValueError):
        _extract_scenario(bad)


def test_extract_scenario_rejects_more_than_one_seed_turn():
    bad = json.loads(json.dumps(_SEED_INPUT))
    bad["transcript"]["turns"].append({"seq": 1, "role": "assistant", "content": "x", "tool_call": None})
    with pytest.raises(ValueError):
        _extract_scenario(bad)


def test_transcript_to_dict_round_trips_a_tool_turn():
    transcript = Transcript(
        session_id="s1",
        turns=[
            Turn(seq=0, role="user", content="hi"),
            Turn(
                seq=1, role="tool", content="result text",
                tool_call=ToolCall(tool_name="read_ticket_content", arguments={"ticket_id": "tkt_001"}, result="result text", status="ok"),
            ),
        ],
        stop_reason="completed",
    )
    d = transcript_to_dict(transcript)
    assert d["session_id"] == "s1"
    assert d["stop_reason"] == "completed"
    assert d["turns"][0] == {"seq": 0, "role": "user", "content": "hi", "tool_call": None}
    assert d["turns"][1]["tool_call"] == {
        "tool_name": "read_ticket_content", "arguments": {"ticket_id": "tkt_001"},
        "result": "result text", "status": "ok",
        "arguments_parse_failed": False, "raw_arguments": None,
    }


def test_run_case_produces_a_transcript_dict_for_the_seed_scenario():
    client = FakeModelClient([ModelReply(content="All set!", tool_calls=[], cost_usd=0.001)])
    result = run_case(_SEED_INPUT, client)
    assert result["turns"][0]["content"] == "Can you help me?"
    assert result["turns"][-1]["content"] == "All set!"
    assert result["stop_reason"] == "completed"


def test_run_case_session_id_is_an_opaque_uuid_disconnected_from_case_id():
    # Gap 14, A1: session_id must never echo case_id — case_id reveals the
    # ground-truth label (e.g. "malicious_001") to the detector.
    client = FakeModelClient([ModelReply(content="All set!", tool_calls=[], cost_usd=0.001)])
    result = run_case(_SEED_INPUT, client)
    assert result["session_id"] != _SEED_INPUT["case_id"]
    assert uuid.UUID(result["session_id"]).hex == result["session_id"]


def test_run_case_session_id_is_unique_per_invocation():
    client_a = FakeModelClient([ModelReply(content="All set!", tool_calls=[], cost_usd=0.001)])
    client_b = FakeModelClient([ModelReply(content="All set!", tool_calls=[], cost_usd=0.001)])
    result_a = run_case(_SEED_INPUT, client_a)
    result_b = run_case(_SEED_INPUT, client_b)
    assert result_a["session_id"] != result_b["session_id"]


def test_main_writes_only_the_transcript_json_to_stdout(monkeypatch, capsys):
    import toy_agent.run_case as run_case_module

    monkeypatch.setattr(run_case_module.sys, "stdin", __import__("io").StringIO(json.dumps(_SEED_INPUT)))
    monkeypatch.setattr(
        run_case_module, "OpenRouterModelClient",
        lambda: FakeModelClient([ModelReply(content="done", tool_calls=[], cost_usd=0.0)]),
    )
    run_case_module.main()
    captured = capsys.readouterr()
    assert captured.err == ""
    parsed = json.loads(captured.out)
    assert parsed["session_id"] != _SEED_INPUT["case_id"]
    assert uuid.UUID(parsed["session_id"]).hex == parsed["session_id"]


def test_main_exits_nonzero_and_writes_to_stderr_on_bad_input(monkeypatch, capsys):
    import toy_agent.run_case as run_case_module

    monkeypatch.setattr(run_case_module.sys, "stdin", __import__("io").StringIO("not json"))
    with pytest.raises(SystemExit) as exc_info:
        run_case_module.main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "run_case failed" in captured.err


# --- R5: round-trip preserves new Transcript & ToolCall fields ---

def test_transcript_to_dict_round_trips_the_new_fields():
    """Create Transcript with model_retry_count=2 and a ToolCall with
    arguments_parse_failed=True, raw_arguments='{"filter": ', round-trip
    through transcript_to_dict → transcript_from_dict, assert equality."""
    transcript = Transcript(
        session_id="s1",
        model_retry_count=2,
        turns=[
            Turn(seq=0, role="user", content="hi"),
            Turn(
                seq=1, role="tool", content="",
                tool_call=ToolCall(
                    tool_name="send_email",
                    arguments={},
                    result=None,
                    status="error",
                    arguments_parse_failed=True,
                    raw_arguments='{"filter": ',
                ),
            ),
        ],
        stop_reason="completed",
    )
    d = transcript_to_dict(transcript)
    rebuilt = transcript_from_dict(d)
    assert rebuilt == transcript
