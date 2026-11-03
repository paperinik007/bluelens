import json
import time
from http.client import HTTPConnection

import httpx
import pytest

from detector_adapter.vendors.llamafirewall.openrouter_proxy import (
    OPENROUTER_BASE_URL,
    build_forwarder,
    serve_forever,
)


def test_build_forwarder_posts_the_body_verbatim_to_the_chat_endpoint():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    forward = build_forwarder(api_key="sk-test", transport=httpx.MockTransport(handler))
    body = {"model": "meta-llama/llama-3.3-70b-instruct", "messages": [{"role": "user", "content": "hi"}]}
    result = forward(body)

    assert captured["url"] == f"{OPENROUTER_BASE_URL}/chat/completions"
    assert captured["auth"] == "Bearer sk-test"
    assert captured["body"] == body  # verbatim — no tier remap, unlike aidr's vendor_proxy.py
    assert result == {"choices": [{"message": {"content": "ok"}}]}


def test_a_pinned_provider_is_added_to_the_body_with_no_fallback_and_the_parameters_required():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": []})

    forward = build_forwarder(api_key="sk-test", transport=httpx.MockTransport(handler), provider="parasail/fp8")
    body = {"model": "meta-llama/llama-4-maverick", "messages": []}
    forward(body)

    assert captured["body"]["provider"] == {"order": ["parasail/fp8"], "allow_fallbacks": False, "require_parameters": True}
    assert captured["body"]["model"] == "meta-llama/llama-4-maverick" and captured["body"]["messages"] == []
    assert "provider" not in body  # the caller's dict is not changed


def test_the_logged_request_shows_the_provider_that_was_pinned(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    log_path = tmp_path / "log.jsonl"
    forward = build_forwarder(api_key="sk-test", transport=httpx.MockTransport(handler), log_path=log_path, provider="parasail/fp8")
    forward({"model": "m", "messages": []})
    assert json.loads(log_path.read_text(encoding="utf-8"))["request"]["provider"]["order"] == ["parasail/fp8"]


def test_the_provider_is_read_from_the_environment(monkeypatch):
    from detector_adapter.vendors.llamafirewall.openrouter_proxy import provider_from_env

    monkeypatch.setenv("LLAMAFIREWALL_PROVIDER", "parasail/fp8")
    assert provider_from_env() == "parasail/fp8"
    monkeypatch.setenv("LLAMAFIREWALL_PROVIDER", "")
    assert provider_from_env() is None
    monkeypatch.delenv("LLAMAFIREWALL_PROVIDER")
    assert provider_from_env() is None


def test_build_forwarder_logs_request_and_response(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    log_path = tmp_path / "llamafirewall_proxy.jsonl"
    forward = build_forwarder(api_key="sk-test-secret", transport=httpx.MockTransport(handler), log_path=log_path)
    forward({"model": "vendor/model", "messages": []})

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["request"]["model"] == "vendor/model"
    assert entry["response"] == {"choices": []}
    assert "error" not in entry


def test_thin_proxy_log_never_contains_the_api_key(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        raise RuntimeError("upstream rejected request with header Bearer sk-test-secret")

    log_path = tmp_path / "llamafirewall_proxy.jsonl"
    forward = build_forwarder(api_key="sk-test-secret", transport=httpx.MockTransport(handler), log_path=log_path)
    with pytest.raises(RuntimeError):
        forward({"model": "vendor/model", "messages": []})

    persisted = log_path.read_text(encoding="utf-8")
    assert "sk-test-secret" not in persisted
    assert "[REDACTED]" in persisted


def test_no_log_path_means_no_logging():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    forward = build_forwarder(api_key="sk-test", transport=httpx.MockTransport(handler))
    forward({"model": "vendor/model", "messages": []})  # must not raise


def test_serve_forever_binds_loopback_and_serves_stubbed_response():
    def stub_forward(body: dict) -> dict:
        return {"echo": body}

    server = serve_forever(18200, stub_forward)
    try:
        time.sleep(0.05)
        conn = HTTPConnection("127.0.0.1", 18200, timeout=2)
        payload = json.dumps({"model": "vendor/model"}).encode()
        conn.request("POST", "/v1/chat/completions", body=payload, headers={"Content-Length": str(len(payload))})
        response = conn.getresponse()
        result = json.loads(response.read())
        assert response.status == 200
        assert result == {"echo": {"model": "vendor/model"}}
    finally:
        server.shutdown()
