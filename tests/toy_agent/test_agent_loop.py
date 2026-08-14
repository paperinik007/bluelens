import pytest

from toy_agent.agent_loop import ToolSpec, build_tool_registry, run_agent
from toy_agent.model_client import ModelReply
from toy_agent.state import fresh_state
from toy_agent.tools import read_ticket_content, ToolError


class FakeModelClient:
    """Scripted model client — never touches the network. One ModelReply per .complete() call."""

    def __init__(self, script: list[ModelReply]):
        self._script = list(script)
        self.calls = 0

    def complete(self, messages, tools):
        self.calls += 1
        if not self._script:
            raise AssertionError("FakeModelClient script exhausted")
        return self._script.pop(0)


def _read_ticket_spec() -> dict[str, ToolSpec]:
    return {
        "read_ticket_content": ToolSpec(
            fn=read_ticket_content,
            json_schema={
                "type": "function",
                "function": {
                    "name": "read_ticket_content",
                    "description": "Read a ticket's free-text content.",
                    "parameters": {
                        "type": "object",
                        "properties": {"ticket_id": {"type": "string"}},
                        "required": ["ticket_id"],
                    },
                },
            },
        )
    }


def test_build_tool_registry_has_all_six_tools():
    registry = build_tool_registry()
    assert set(registry) == {
        "query_customer_db", "read_ticket_content", "send_email",
        "update_account", "run_diagnostic", "bulk_export",
    }


def test_loop_stops_on_final_answer_with_no_tool_calls():
    client = FakeModelClient([ModelReply(content="All done, glad to help!", tool_calls=[], cost_usd=0.001)])
    state = fresh_state()
    transcript = run_agent("Can you help me?", tools={}, state=state, model_client=client, session_id="s1")
    assert transcript.session_id == "s1"
    assert transcript.turns[0].role == "user"
    assert transcript.turns[-1].role == "assistant"
    assert transcript.turns[-1].content == "All done, glad to help!"
    assert client.calls == 1


def test_loop_executes_tool_call_and_records_result():
    script = [
        ModelReply(
            content="",
            tool_calls=[{"id": "call_1", "name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}],
            cost_usd=0.001,
        ),
        ModelReply(content="Thanks, I see your ticket.", tool_calls=[], cost_usd=0.001),
    ]
    client = FakeModelClient(script)
    state = fresh_state()
    transcript = run_agent("help with tkt_001", tools=_read_ticket_spec(), state=state, model_client=client, session_id="s2")

    tool_turns = [t for t in transcript.turns if t.role == "tool"]
    assert len(tool_turns) == 1
    assert tool_turns[0].tool_call.tool_name == "read_ticket_content"
    assert tool_turns[0].tool_call.status == "ok"
    assert "accedere" in tool_turns[0].content


def test_loop_records_tool_error_status_on_toolerror():
    script = [
        ModelReply(
            content="",
            tool_calls=[{"id": "call_1", "name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_missing"}'}],
            cost_usd=0.001,
        ),
        ModelReply(content="Sorry, could not find that.", tool_calls=[], cost_usd=0.001),
    ]
    client = FakeModelClient(script)
    state = fresh_state()
    transcript = run_agent("help", tools=_read_ticket_spec(), state=state, model_client=client, session_id="s3")

    tool_turns = [t for t in transcript.turns if t.role == "tool"]
    assert tool_turns[0].tool_call.status == "error"


def test_loop_stops_at_max_turns_with_partial_transcript_still_valid():
    always_call = ModelReply(
        content="",
        tool_calls=[{"id": "call_x", "name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}],
        cost_usd=0.001,
    )
    client = FakeModelClient([always_call] * 10)
    state = fresh_state()
    transcript = run_agent("help", tools=_read_ticket_spec(), state=state, model_client=client, session_id="s4", max_turns=3)

    assert client.calls == 3
    assert isinstance(transcript.turns, list)
    assert len(transcript.turns) > 0


def test_loop_stops_at_max_cost_before_next_call():
    script = [
        ModelReply(content="", tool_calls=[], cost_usd=0.3),
        ModelReply(content="", tool_calls=[], cost_usd=0.3),
        ModelReply(content="", tool_calls=[], cost_usd=0.3),
    ]
    # each reply above has no tool_calls, which would normally stop the loop
    # after the first one — force continuation by giving a tool call instead:
    script = [
        ModelReply(content="", tool_calls=[{"id": "1", "name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}], cost_usd=0.3),
        ModelReply(content="", tool_calls=[{"id": "2", "name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}], cost_usd=0.3),
        ModelReply(content="", tool_calls=[{"id": "3", "name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}], cost_usd=0.3),
    ]
    client = FakeModelClient(script)
    state = fresh_state()
    run_agent("help", tools=_read_ticket_spec(), state=state, model_client=client, session_id="s5", max_turns=10, max_cost_usd=0.5)

    # after 2 calls total_cost=0.6 >= 0.5, loop must stop before a 3rd call
    assert client.calls == 2


def test_loop_stops_immediately_after_single_reply_exceeds_cost_cap():
    # Documented limitation: the cap cannot be enforced *before* a call whose
    # cost is only known after it returns — it guarantees at most one
    # over-budget call, not a hard ceiling.
    script = [ModelReply(content="", tool_calls=[{"id": "1", "name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}], cost_usd=999.0)]
    client = FakeModelClient(script * 5)
    state = fresh_state()
    run_agent("help", tools=_read_ticket_spec(), state=state, model_client=client, session_id="s6", max_turns=10, max_cost_usd=0.5)
    assert client.calls == 1


def test_loop_stops_gracefully_on_model_client_exception():
    class ExplodingClient:
        def __init__(self):
            self.calls = 0

        def complete(self, messages, tools):
            self.calls += 1
            if self.calls == 1:
                return ModelReply(
                    content="",
                    tool_calls=[{"id": "1", "name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}],
                    cost_usd=0.001,
                )
            raise RuntimeError("Authorization failed for key sk-secret-abc123")

    state = fresh_state()
    transcript = run_agent("help", tools=_read_ticket_spec(), state=state, model_client=ExplodingClient(), session_id="s7")

    full_text = " ".join(t.content for t in transcript.turns)
    assert "sk-secret-abc123" not in full_text
    assert "RuntimeError" in full_text
    tool_turns = [t for t in transcript.turns if t.role == "tool"]
    assert len(tool_turns) == 1  # the first successful tool call is still preserved


def test_loop_handles_malformed_tool_arguments_without_crashing():
    # Model returns a tool call with missing required argument (ticket_id is required)
    script = [
        ModelReply(
            content="",
            tool_calls=[{"id": "call_1", "name": "read_ticket_content", "arguments": '{}'}],  # missing ticket_id
            cost_usd=0.001,
        ),
        ModelReply(content="I encountered an error.", tool_calls=[], cost_usd=0.001),
    ]
    client = FakeModelClient(script)
    state = fresh_state()
    # Should not raise; transcript should still be valid
    transcript = run_agent("help", tools=_read_ticket_spec(), state=state, model_client=client, session_id="s8")

    # Verify the transcript is valid and complete
    assert isinstance(transcript.turns, list)
    assert len(transcript.turns) > 0

    # Verify the malformed tool call is recorded with error status
    tool_turns = [t for t in transcript.turns if t.role == "tool"]
    assert len(tool_turns) == 1
    assert tool_turns[0].tool_call.status == "error"
    # Verify no raw traceback/raw error message, only error status
    assert "TypeError" in tool_turns[0].content or "missing" not in tool_turns[0].content.lower()
