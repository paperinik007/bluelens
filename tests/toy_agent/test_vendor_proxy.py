import json
import time
from http.client import HTTPConnection

import httpx
import pytest

from toy_agent.vendor_proxy import (
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
