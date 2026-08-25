import json

import pytest

from toy_agent.agent_loop import ToolSpec, build_tool_registry, run_agent
from toy_agent.model_client import ModelReply
from toy_agent.state import fresh_state
from toy_agent.tools import bulk_export, read_ticket_content, ToolError


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
    assert transcript.stop_reason == "completed"


def test_loop_executes_tool_call_and_records_result():
    script = [
        ModelReply(
            content="",
            tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}}],
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


def test_loop_preserves_assistant_reasoning_text_on_tool_call_turn():
    # C2 regression guard: reasoning text preceding a tool call must land in
    # the returned Transcript, not just in the internal messages list.
    script = [
        ModelReply(
            content="Let me check that ticket for you.",
            tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}}],
            cost_usd=0.001,
        ),
        ModelReply(content="Thanks, I see your ticket.", tool_calls=[], cost_usd=0.001),
    ]
    client = FakeModelClient(script)
    state = fresh_state()
    transcript = run_agent("help with tkt_001", tools=_read_ticket_spec(), state=state, model_client=client, session_id="s2b")

    assistant_turns = [t for t in transcript.turns if t.role == "assistant"]
    assert any(t.content == "Let me check that ticket for you." for t in assistant_turns)


def test_loop_records_tool_error_status_on_toolerror():
    script = [
        ModelReply(
            content="",
            tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_missing"}'}}],
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
        tool_calls=[{"id": "call_x", "type": "function", "function": {"name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}}],
        cost_usd=0.001,
    )
    client = FakeModelClient([always_call] * 10)
    state = fresh_state()
    transcript = run_agent("help", tools=_read_ticket_spec(), state=state, model_client=client, session_id="s4", max_turns=3)

    assert client.calls == 3
    assert isinstance(transcript.turns, list)
    assert len(transcript.turns) > 0
    assert transcript.stop_reason == "max_turns"


def test_loop_stops_at_max_cost_before_next_call():
    script = [
        ModelReply(content="", tool_calls=[], cost_usd=0.3),
        ModelReply(content="", tool_calls=[], cost_usd=0.3),
        ModelReply(content="", tool_calls=[], cost_usd=0.3),
    ]
    # each reply above has no tool_calls, which would normally stop the loop
    # after the first one — force continuation by giving a tool call instead:
    script = [
        ModelReply(content="", tool_calls=[{"id": "1", "type": "function", "function": {"name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}}], cost_usd=0.3),
        ModelReply(content="", tool_calls=[{"id": "2", "type": "function", "function": {"name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}}], cost_usd=0.3),
        ModelReply(content="", tool_calls=[{"id": "3", "type": "function", "function": {"name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}}], cost_usd=0.3),
    ]
    client = FakeModelClient(script)
    state = fresh_state()
    transcript = run_agent("help", tools=_read_ticket_spec(), state=state, model_client=client, session_id="s5", max_turns=10, max_cost_usd=0.5)

    # after 2 calls total_cost=0.6 >= 0.5, loop must stop before a 3rd call
    assert client.calls == 2
    assert transcript.stop_reason == "max_cost"


def test_loop_stops_immediately_after_single_reply_exceeds_cost_cap():
    # Documented limitation: the cap cannot be enforced *before* a call whose
    # cost is only known after it returns — it guarantees at most one
    # over-budget call, not a hard ceiling.
    script = [ModelReply(content="", tool_calls=[{"id": "1", "type": "function", "function": {"name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}}], cost_usd=999.0)]
    client = FakeModelClient(script * 5)
    state = fresh_state()
    transcript = run_agent("help", tools=_read_ticket_spec(), state=state, model_client=client, session_id="s6", max_turns=10, max_cost_usd=0.5)
    assert client.calls == 1
    assert transcript.stop_reason == "max_cost"


def test_loop_stops_gracefully_on_model_client_exception():
    class ExplodingClient:
        def __init__(self):
            self.calls = 0

        def complete(self, messages, tools):
            self.calls += 1
            if self.calls == 1:
                return ModelReply(
                    content="",
                    tool_calls=[{"id": "1", "type": "function", "function": {"name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}}],
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
    assert transcript.stop_reason == "model_error"


def test_loop_handles_malformed_tool_arguments_without_crashing():
    # Model returns a tool call with missing required argument (ticket_id is required)
    script = [
        ModelReply(
            content="",
            tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "read_ticket_content", "arguments": '{}'}}],  # missing ticket_id
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


def test_system_prompt_declares_the_bulk_export_guardrail():
    from toy_agent.agent_loop import _SYSTEM_PROMPT
    assert "bulk_export is the only sanctioned way" in _SYSTEM_PROMPT
    assert "query_customer_db repeatedly" in _SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Retry-count transcript tests (Task 4)
# ---------------------------------------------------------------------------


class RetryCountingFakeClient(FakeModelClient):
    def __init__(self, script, retry_count):
        super().__init__(script)
        self.retry_count = retry_count


def test_the_transcript_carries_the_retry_count_out_of_the_loop():
    client = RetryCountingFakeClient([ModelReply(content="done", tool_calls=[], cost_usd=0.001)], retry_count=3)
    transcript = run_agent("hi", tools={}, state=fresh_state(), model_client=client, session_id="s1")
    assert transcript.model_retry_count == 3
    assert transcript.stop_reason == "completed"


def test_a_client_without_a_retry_counter_yields_zero():
    client = FakeModelClient([ModelReply(content="done", tool_calls=[], cost_usd=0.001)])
    transcript = run_agent("hi", tools={}, state=fresh_state(), model_client=client, session_id="s1")
    assert transcript.model_retry_count == 0


# ---------------------------------------------------------------------------
# Helpers for parse-failure tests (Task 2)
# ---------------------------------------------------------------------------


def _bulk_export_spec() -> dict[str, ToolSpec]:
    return {
        "bulk_export": ToolSpec(
            fn=bulk_export,
            json_schema={
                "type": "function",
                "function": {
                    "name": "bulk_export",
                    "description": "Export matching customer records.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filter": {"type": "object"},
                            "format": {"type": "string"},
                        },
                        "required": ["format"],
                    },
                },
            },
        )
    }


def _one_bulk_export_call(arguments):
    return ModelReply(
        content="",
        tool_calls=[
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "bulk_export", "arguments": arguments},
            }
        ],
        cost_usd=0.001,
    )


# ---------------------------------------------------------------------------
# Task 2: parse-failure tests
# ---------------------------------------------------------------------------


class TestParseArguments:
    """Tests for _parse_arguments and the parse-failure guard in the agent loop."""

    def test_unparsable_arguments_never_execute_the_tool(self):
        """Feed incomplete JSON; the tool must never be called."""
        script = [
            _one_bulk_export_call('{"filter": '),  # incomplete JSON
            ModelReply(content="Done.", tool_calls=[], cost_usd=0.001),
        ]
        client = FakeModelClient(script)
        state = fresh_state()
        transcript = run_agent(
            "export please",
            tools=_bulk_export_spec(),
            state=state,
            model_client=client,
            session_id="s_parse_1",
        )

        tool_turns = [t for t in transcript.turns if t.role == "tool"]
        assert len(tool_turns) == 1
        tc = tool_turns[0].tool_call
        assert tc.arguments_parse_failed is True
        assert tc.status == "error"
        assert tc.arguments == {}
        assert tc.raw_arguments == '{"filter": '
        # No customer data must leak into the result
        assert "alice.rossi@example.com" not in tc.result
        assert "cust_001" not in tc.result

    @pytest.mark.parametrize("raw_json", ["null", "[1,2]", "5", '"a string"', "true"])
    def test_valid_json_that_is_not_an_object_is_treated_as_a_parse_failure(self, raw_json):
        """Each non-object JSON value must produce arguments_parse_failed=True."""
        script = [
            _one_bulk_export_call(raw_json),
            ModelReply(content="Done.", tool_calls=[], cost_usd=0.001),
        ]
        client = FakeModelClient(script)
        state = fresh_state()
        transcript = run_agent(
            "export please",
            tools=_bulk_export_spec(),
            state=state,
            model_client=client,
            session_id=f"s_parse_nonobj_{raw_json[:10]}",
        )

        tool_turns = [t for t in transcript.turns if t.role == "tool"]
        assert len(tool_turns) == 1
        tc = tool_turns[0].tool_call
        assert tc.arguments_parse_failed is True
        assert tc.status == "error"
        assert "alice.rossi@example.com" not in tc.result
        assert "cust_001" not in tc.result

    def test_a_genuine_tool_error_is_not_flagged_as_a_parse_failure(self):
        """read_ticket_content with non-existent tkt_999 is a tool error, not a parse failure."""
        script = [
            ModelReply(
                content="",
                tool_calls=[
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_ticket_content",
                            "arguments": '{"ticket_id": "tkt_999"}',
                        },
                    }
                ],
                cost_usd=0.001,
            ),
            ModelReply(content="Done.", tool_calls=[], cost_usd=0.001),
        ]
        client = FakeModelClient(script)
        state = fresh_state()
        transcript = run_agent(
            "check tkt_999",
            tools=_read_ticket_spec(),
            state=state,
            model_client=client,
            session_id="s_genuine_error",
        )

        tool_turns = [t for t in transcript.turns if t.role == "tool"]
        assert len(tool_turns) == 1
        tc = tool_turns[0].tool_call
        assert tc.status == "error"
        assert tc.arguments_parse_failed is False
        assert tc.raw_arguments is None
        assert "unknown ticket_id" in tc.result

    def test_the_message_returned_to_the_model_is_capped_but_the_evidence_is_not(self):
        """Long raw arguments: turn.content is capped, raw_arguments is not."""
        long_raw = "x" * 5000 + '{"filter": {}}'  # 5000+ chars of junk
        script = [
            _one_bulk_export_call(long_raw),
            ModelReply(content="Done.", tool_calls=[], cost_usd=0.001),
        ]
        client = FakeModelClient(script)
        state = fresh_state()
        transcript = run_agent(
            "export please",
            tools=_bulk_export_spec(),
            state=state,
            model_client=client,
            session_id="s_capped",
        )

        tool_turns = [t for t in transcript.turns if t.role == "tool"]
        assert len(tool_turns) == 1
        tc = tool_turns[0].tool_call
        turn = tool_turns[0]
        # The message to the model is capped
        assert len(turn.content) < 400
        assert turn.content.endswith("...")
        # The evidence is not
        assert tc.raw_arguments == long_raw
        assert tc.arguments_parse_failed is True

    def test_an_unknown_tool_is_still_reported_as_an_unknown_tool(self):
        """Parse-failure branch must not swallow the unknown-tool path."""
        # Valid JSON, but tool name doesn't exist in registry
        script = [
            ModelReply(
                content="",
                tool_calls=[
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "nonexistent_tool",
                            "arguments": '{"x": 1}',
                        },
                    }
                ],
                cost_usd=0.001,
            ),
            ModelReply(content="Done.", tool_calls=[], cost_usd=0.001),
        ]
        client = FakeModelClient(script)
        state = fresh_state()
        transcript = run_agent(
            "try unknown tool",
            tools=_read_ticket_spec(),  # only read_ticket_content registered
            state=state,
            model_client=client,
            session_id="s_unknown",
        )

        tool_turns = [t for t in transcript.turns if t.role == "tool"]
        assert len(tool_turns) == 1
        tc = tool_turns[0].tool_call
        assert tc.tool_name == "nonexistent_tool"
        assert tc.status == "error"
        # Must NOT be flagged as a parse failure — the arguments were valid JSON
        assert tc.arguments_parse_failed is False
        assert "unknown tool" in tc.result
