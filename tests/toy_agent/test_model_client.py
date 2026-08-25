from types import SimpleNamespace

import httpx
import openai
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


# test_openrouter_client_rejects_unpriced_model_at_construction removed: the
# guard it protected is the coupling design doc D3 removes (it made AGENT_MODEL
# unusable). Replaced by test_a_model_absent_from_the_pricing_table_is_accepted_at_construction
# plus the live preflight probe on the agent model.
def test_a_model_absent_from_the_pricing_table_is_accepted_at_construction(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = OpenRouterModelClient(model="anthropic/claude-haiku-4.5", api_key="sk-test")
    assert client is not None


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


def _fake_response_with_cost(cost, prompt_tokens=1000, completion_tokens=1000):
    message = SimpleNamespace(content="ok", tool_calls=None)
    usage = SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, cost=cost)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


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


def test_complete_prefers_the_cost_reported_by_openrouter(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = OpenRouterModelClient(api_key="sk-test-not-real")
    client._client.chat.completions.create = lambda **kwargs: _fake_response_with_cost(0.0123)
    reply = client.complete(messages=[{"role": "user", "content": "hi"}], tools=[])
    assert reply.cost_usd == pytest.approx(0.0123)


def test_complete_falls_back_to_the_pricing_table_while_it_still_exists(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = OpenRouterModelClient(api_key="sk-test-not-real")
    response = _fake_response("ok", None, 1_000_000, 1_000_000)
    client._client.chat.completions.create = lambda **kwargs: response
    reply = client.complete(messages=[{"role": "user", "content": "hi"}], tools=[])
    assert reply.cost_usd == pytest.approx(0.75)


def test_complete_sends_an_explicit_max_tokens_and_timeout(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = OpenRouterModelClient(api_key="sk-test-not-real")
    captured = {}

    def capture_create(**kwargs):
        captured.update(kwargs)
        return _fake_response("ok", None, 1000, 1000)

    client._client.chat.completions.create = capture_create
    client.complete(messages=[{"role": "user", "content": "hi"}], tools=[])
    assert captured["max_tokens"] == 2048
    assert captured["timeout"] == 20.0


# ---------------------------------------------------------------------------
# Retry helpers (Task 4)
# ---------------------------------------------------------------------------


class _FailThenSucceed:
    def __init__(self, failures, exc_factory):
        self.remaining = failures
        self.calls = 0
        self._exc_factory = exc_factory

    def __call__(self, **kwargs):
        self.calls += 1
        if self.remaining > 0:
            self.remaining -= 1
            raise self._exc_factory()
        return _fake_response_with_cost(0.001)


def _rate_limit_error():
    return openai.RateLimitError(
        "rate limited",
        response=httpx.Response(429, request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")),
        body=None,
    )


def _auth_error():
    return openai.AuthenticationError(
        "bad key",
        response=httpx.Response(401, request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")),
        body=None,
    )


# ---------------------------------------------------------------------------
# Retry tests (Task 4)
# ---------------------------------------------------------------------------


class TestRetryLogic:
    def test_a_transient_failure_is_retried_and_still_counted(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        client = OpenRouterModelClient(api_key="sk-test-not-real")
        create = _FailThenSucceed(1, _rate_limit_error)
        client._client.chat.completions.create = create
        slept = []
        client._sleep = slept.append

        reply = client.complete(messages=[{"role": "user", "content": "hi"}], tools=[])

        assert reply.cost_usd == pytest.approx(0.001)
        assert create.calls == 2
        assert client.retry_count == 1
        assert slept == [1.0]

    def test_a_permanent_failure_is_not_retried(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        client = OpenRouterModelClient(api_key="sk-test-not-real")
        create = _FailThenSucceed(1, _auth_error)
        client._client.chat.completions.create = create
        slept = []
        client._sleep = slept.append

        with pytest.raises(openai.AuthenticationError):
            client.complete(messages=[{"role": "user", "content": "hi"}], tools=[])

        assert create.calls == 1
        assert client.retry_count == 0

    def test_the_retry_budget_is_per_case_not_per_call(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        client = OpenRouterModelClient(api_key="sk-test-not-real")
        create = _FailThenSucceed(99, _rate_limit_error)  # never succeeds
        client._client.chat.completions.create = create
        slept = []
        client._sleep = slept.append

        with pytest.raises(openai.RateLimitError):
            client.complete(messages=[{"role": "user", "content": "hi"}], tools=[])

        # 1 initial attempt + 2 retries = 3 calls
        assert create.calls == 3
        assert client.retry_count == 2
        assert slept == [1.0, 3.0]

        # Second complete() fails without retry (budget already exhausted)
        with pytest.raises(openai.RateLimitError):
            client.complete(messages=[{"role": "user", "content": "hi"}], tools=[])

        # One more call attempt (no retries)
        assert create.calls == 4
        assert client.retry_count == 2
