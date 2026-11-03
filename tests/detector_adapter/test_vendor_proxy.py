import json
import json as _json
import time
from http.client import HTTPConnection

import httpx
import pytest

from detector_adapter.vendors.aidr.vendor_proxy import (
    DEFAULT_TIER_TO_MODEL,
    DEFAULT_TIER_TO_PROVIDER,
    TIER_TO_MODEL,
    build_forwarder,
    build_tier_to_model,
    build_tier_to_provider,
    remap_tier,
    serve_forever,
)


def test_every_request_is_pinned_to_one_provider_without_fallback():
    # plan part 7, 2026-10-27: in the pilot 8 invalid tool-call arguments, all from SiliconFlow (0 of 252 on Nebius);
    # one fp8 provider for the two chat tiers, the only embedding provider for the third, no fallback.
    assert DEFAULT_TIER_TO_PROVIDER == {"sifter": "nebius/fp8", "inspector": "nebius/fp8", "embed": "deepinfra/us"}
    body = {"model": "inspector", "messages": []}
    remapped = remap_tier(body)
    assert remapped["provider"] == {"order": ["nebius/fp8"], "allow_fallbacks": False, "require_parameters": True}
    assert remapped["messages"] == [] and "provider" not in body


def test_the_provider_of_a_tier_can_be_set_from_the_environment_and_an_empty_value_means_the_default():
    assert build_tier_to_provider({"SIFTER_PROVIDER": "siliconflow/fp8"})["sifter"] == "siliconflow/fp8"
    assert build_tier_to_provider({"SIFTER_PROVIDER": ""}) == DEFAULT_TIER_TO_PROVIDER
    assert build_tier_to_provider({}) == DEFAULT_TIER_TO_PROVIDER


def test_the_first_stage_uses_a_model_that_exists_on_openrouter():
    # qwen/qwen3-8b, the substitute of the published runs, is no longer in OpenRouter's listing (checked
    # 2026-10-26); plan part 7: the first stage runs on the second stage's model, the deviation is declared.
    assert DEFAULT_TIER_TO_MODEL["sifter"] == "qwen/qwen3-30b-a3b-instruct-2507"


def test_build_tier_to_model_uses_defaults_when_env_is_empty():
    assert build_tier_to_model({}) == DEFAULT_TIER_TO_MODEL


def test_build_tier_to_model_env_override_wins_per_tier():
    result = build_tier_to_model({"SIFTER_MODEL": "vendor/custom-sifter"})
    assert result["sifter"] == "vendor/custom-sifter"
    assert result["inspector"] == DEFAULT_TIER_TO_MODEL["inspector"]
    assert result["embed"] == DEFAULT_TIER_TO_MODEL["embed"]


def test_build_tier_to_model_treats_blank_env_value_as_unset():
    # docker compose substitutes an unset .env entry as an empty string, not an
    # absent key — must fall back to the default, not use "".
    result = build_tier_to_model({"SIFTER_MODEL": ""})
    assert result["sifter"] == DEFAULT_TIER_TO_MODEL["sifter"]


def test_remap_tier_rewrites_model_field():
    body = {"model": "sifter", "messages": []}
    remapped = remap_tier(body)
    assert remapped["model"] == TIER_TO_MODEL["sifter"]
    assert body["model"] == "sifter"  # original untouched


def test_remap_tier_rejects_unknown_tier():
    with pytest.raises(ValueError):
        remap_tier({"model": "unknown-tier"})


def test_build_forwarder_posts_remapped_body_to_openrouter_chat_endpoint():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": []})

    forward = build_forwarder(api_key="sk-test", transport=httpx.MockTransport(handler))
    result = forward(8100, {"model": "sifter", "messages": [{"role": "user", "content": "hi"}]})

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["auth"] == "Bearer sk-test"
    assert captured["body"]["model"] == TIER_TO_MODEL["sifter"]
    assert result == {"choices": []}


def test_build_forwarder_posts_embeddings_endpoint_for_embed_tier():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"data": []})

    forward = build_forwarder(api_key="sk-test", transport=httpx.MockTransport(handler))
    result = forward(8102, {"model": "embed", "input": "hello"})

    assert captured["url"] == "https://openrouter.ai/api/v1/embeddings"
    assert captured["body"]["model"] == "qwen/qwen3-embedding-4b"
    assert result == {"data": []}


def test_forward_raises_for_unconfigured_port():
    forward = build_forwarder(api_key="sk-test", transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    with pytest.raises(ValueError):
        forward(9999, {"model": "sifter"})


def test_serve_forever_binds_loopback_and_serves_stubbed_response():
    def stub_forward(port: int, body: dict) -> dict:
        return {"echo": body, "port": port}

    servers = serve_forever([18100], stub_forward)
    try:
        time.sleep(0.05)  # let the background thread start listening
        conn = HTTPConnection("127.0.0.1", 18100, timeout=2)
        payload = json.dumps({"model": "sifter"}).encode()
        conn.request("POST", "/v1/chat/completions", body=payload, headers={"Content-Length": str(len(payload))})
        response = conn.getresponse()
        result = json.loads(response.read())
        assert response.status == 200
        assert result == {"echo": {"model": "sifter"}, "port": 18100}
    finally:
        for server in servers:
            server.shutdown()


def _sequence(statuses, ok_body=None):
    """A transport answering with the given HTTP statuses in turn; the last one repeats."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        status = statuses[min(len(calls), len(statuses) - 1)]
        calls.append(status)
        return httpx.Response(status, json=ok_body if status == 200 else {"error": "x"})
    return httpx.MockTransport(handler), calls


def test_a_rate_limit_or_a_server_error_is_retried_with_the_same_request_after_a_pause():
    transport, calls = _sequence([429, 502, 200], {"data": [1]})
    pauses = []
    forward = build_forwarder(api_key="sk", transport=transport, sleep=pauses.append)
    assert forward(8102, {"model": "embed", "input": "x"}) == {"data": [1]}
    assert calls == [429, 502, 200] and pauses == [1.0, 2.0]  # doubling pauses


def test_it_gives_up_after_four_attempts_and_raises():
    transport, calls = _sequence([429])
    forward = build_forwarder(api_key="sk", transport=transport, sleep=lambda s: None)
    with pytest.raises(httpx.HTTPStatusError):
        forward(8102, {"model": "embed", "input": "x"})
    assert len(calls) == 4


def test_a_client_error_that_is_not_a_rate_limit_is_not_retried():
    transport, calls = _sequence([400])
    forward = build_forwarder(api_key="sk", transport=transport, sleep=lambda s: None)
    with pytest.raises(httpx.HTTPStatusError):
        forward(8100, {"model": "sifter", "messages": []})
    assert calls == [400]


def test_every_failed_attempt_is_logged_with_its_attempt_number(tmp_path):
    transport, _ = _sequence([429, 200], {"data": [1]})
    log = tmp_path / "log.jsonl"
    forward = build_forwarder(api_key="sk", transport=transport, log_path=log, sleep=lambda s: None)
    forward(8102, {"model": "embed", "input": "x"})
    entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert [(("error" in e), e.get("attempt")) for e in entries] == [(True, 1), (False, 2)]


def test_build_forwarder_logs_request_and_response(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    log_path = tmp_path / "vendor_proxy.jsonl"
    forward = build_forwarder(
        api_key="sk-test-secret",
        transport=httpx.MockTransport(handler),
        log_path=log_path,
    )
    forward(8100, {"model": "sifter", "messages": [{"role": "user", "content": "hi"}]})

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = _json.loads(lines[0])
    assert entry["port"] == 8100
    assert entry["request"]["model"] == TIER_TO_MODEL["sifter"]
    assert entry["response"] == {"choices": []}
    assert "error" not in entry


def test_thin_proxy_log_never_contains_the_api_key(tmp_path):
    # httpx.HTTPStatusError's own message never includes the response body, so
    # a 4xx/5xx Response alone wouldn't actually exercise the scrub path here
    # (the secret would never be in str(exc) to begin with — a vacuous test).
    # Raising directly from the transport handler is what makes this a real
    # test: it simulates the scenario the council-risk finding actually
    # flagged (2026-08-16 targeted council on Gap 9) — an error whose message
    # echoes the Authorization header back — and gives forward()'s except
    # branch a str(exc) that genuinely contains the secret to scrub.
    def handler(request: httpx.Request) -> httpx.Response:
        raise RuntimeError(f"upstream rejected request with header Bearer sk-test-secret")

    log_path = tmp_path / "vendor_proxy.jsonl"
    forward = build_forwarder(
        api_key="sk-test-secret",
        transport=httpx.MockTransport(handler),
        log_path=log_path,
    )
    with pytest.raises(RuntimeError):
        forward(8100, {"model": "sifter", "messages": []})

    persisted = log_path.read_text(encoding="utf-8")
    assert "sk-test-secret" not in persisted
    assert "[REDACTED]" in persisted


def test_no_log_path_means_no_logging(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    forward = build_forwarder(api_key="sk-test", transport=httpx.MockTransport(handler))
    forward(8100, {"model": "sifter", "messages": []})
    # No log_path given: nothing should be written anywhere reachable from this
    # test — the only assertion possible is that forward() didn't raise.
