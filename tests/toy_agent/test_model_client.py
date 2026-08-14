from types import SimpleNamespace

import pytest

from toy_agent.model_client import compute_cost_usd, ModelReply, OpenRouterModelClient


def test_compute_cost_usd_known_model():
    cost = compute_cost_usd("openai/gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert cost == pytest.approx(0.15 + 0.60)


def test_compute_cost_usd_zero_tokens():
    assert compute_cost_usd("openai/gpt-4o-mini", prompt_tokens=0, completion_tokens=0) == 0.0


def test_compute_cost_usd_unknown_model_raises():
    with pytest.raises(ValueError):
        compute_cost_usd("unknown/model", prompt_tokens=100, completion_tokens=100)


def test_openrouter_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        OpenRouterModelClient()


def test_openrouter_client_accepts_explicit_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = OpenRouterModelClient(api_key="sk-test-not-real")
    assert client is not None


def test_openrouter_client_rejects_unpriced_model_at_construction(monkeypatch):
    # I2 regression guard: an unpriced model must be rejected at construction
    # time, before any (billed) network call could happen.
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError):
        OpenRouterModelClient(model="unknown/model", api_key="sk-test")


def _fake_response(content: str, tool_calls: list | None, prompt_tokens: int, completion_tokens: int):
    """Build a SimpleNamespace shaped like the real openai SDK's ChatCompletion
    response — just deep enough to exercise complete()'s field-mapping code."""
    fake_tool_calls = None
    if tool_calls is not None:
        fake_tool_calls = [
            SimpleNamespace(id=tc["id"], function=SimpleNamespace(name=tc["name"], arguments=tc["arguments"]))
            for tc in tool_calls
        ]
    message = SimpleNamespace(content=content, tool_calls=fake_tool_calls)
    choice = SimpleNamespace(message=message)
    usage = SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return SimpleNamespace(choices=[choice], usage=usage)


def test_complete_parses_response_with_tool_call_into_correct_shape(monkeypatch):
    # I5/C1 regression guard: exercise complete()'s actual response-parsing
    # code (never faked at the .complete() boundary), and assert the SDK's
    # nested tool_calls shape survives untouched — {"id", "type": "function",
    # "function": {"name", "arguments"}} — not the old flattened shape.
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = OpenRouterModelClient(api_key="sk-test-not-real")

    response = _fake_response(
        content="Let me check that ticket for you.",
        tool_calls=[{"id": "call_1", "name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'}],
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )
    client._client.chat.completions.create = lambda **kwargs: response

    reply = client.complete(messages=[{"role": "user", "content": "help"}], tools=[])

    assert isinstance(reply, ModelReply)
    assert reply.content == "Let me check that ticket for you."
    assert reply.cost_usd == pytest.approx(0.15 + 0.60)
    assert reply.tool_calls == [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "read_ticket_content", "arguments": '{"ticket_id": "tkt_001"}'},
        }
    ]


def test_complete_parses_response_with_no_tool_calls(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = OpenRouterModelClient(api_key="sk-test-not-real")

    response = _fake_response(content="All done, glad to help!", tool_calls=None, prompt_tokens=0, completion_tokens=0)
    client._client.chat.completions.create = lambda **kwargs: response

    reply = client.complete(messages=[{"role": "user", "content": "help"}], tools=[])

    assert reply.content == "All done, glad to help!"
    assert reply.tool_calls == []
    assert reply.cost_usd == 0.0
