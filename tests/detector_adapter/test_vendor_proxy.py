import json
import json as _json
import time
from http.client import HTTPConnection

import httpx
import pytest

from detector_adapter.vendor_proxy import (
    build_forwarder,
    remap_tier,
    serve_forever,
)


def test_remap_tier_rewrites_model_field():
    body = {"model": "sifter", "messages": []}
    remapped = remap_tier(body)
    assert remapped["model"] == "qwen/qwen3-4b-instruct-2507"
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
    assert captured["body"]["model"] == "qwen/qwen3-4b-instruct-2507"
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
    assert entry["request"]["model"] == "qwen/qwen3-4b-instruct-2507"
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
