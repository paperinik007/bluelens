import json

import httpx

from toy_agent.preflight import preflight_check_models


def test_preflight_check_models_passes_when_all_configured_tiers_respond_ok():
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/embeddings"):
            return httpx.Response(200, json={"data": []})
        return httpx.Response(200, json={"choices": []})

    env = {"SIFTER_MODEL": "vendor/sifter", "INSPECTOR_MODEL": "vendor/inspector", "EMBED_MODEL": "vendor/embed"}
    failures = preflight_check_models(env, "sk-test", transport=httpx.MockTransport(handler))

    assert failures == []


def test_preflight_check_models_reports_a_404_for_the_failing_model():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["model"] == "vendor/gone":
            return httpx.Response(404, json={"error": "No endpoints found"})
        return httpx.Response(200, json={"choices": []})

    env = {"SIFTER_MODEL": "vendor/gone", "INSPECTOR_MODEL": "vendor/inspector"}
    failures = preflight_check_models(env, "sk-test", transport=httpx.MockTransport(handler))

    assert len(failures) == 1
    assert "sifter" in failures[0]
    assert "vendor/gone" in failures[0]


def test_preflight_check_models_skips_tiers_with_no_env_var_set():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json={"choices": []})

    failures = preflight_check_models({}, "sk-test", transport=httpx.MockTransport(handler))

    assert failures == []
    assert calls == []


def test_preflight_check_models_posts_embeddings_endpoint_for_embed_tier():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"data": []})

    env = {"EMBED_MODEL": "vendor/embed"}
    failures = preflight_check_models(env, "sk-test", transport=httpx.MockTransport(handler))

    assert failures == []
    assert captured["url"] == "https://openrouter.ai/api/v1/embeddings"
    assert captured["body"]["model"] == "vendor/embed"
