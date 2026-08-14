import pytest

from toy_agent.model_client import compute_cost_usd, OpenRouterModelClient


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
