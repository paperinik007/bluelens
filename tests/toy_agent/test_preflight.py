import json

import httpx

from toy_agent.preflight import preflight_check_models


def test_the_agent_model_is_probed_live_like_every_detector_tier():
    def handler(request):
        if json.loads(request.content)["model"] == "openai/gpt-4o-mini":
            return httpx.Response(404, json={"error": "No endpoints found"})
        return httpx.Response(200, json={"choices": []})
    failures = preflight_check_models({}, "sk-detector", agent_api_key="sk-agent", transport=httpx.MockTransport(handler))
    assert len(failures) == 1
    assert "agent" in failures[0]


def test_the_agent_probe_uses_the_agent_key_and_the_tier_probes_use_the_detector_key():
    seen = []
    def handler(request):
        seen.append((json.loads(request.content)["model"], request.headers["Authorization"]))
        return httpx.Response(200, json={"choices": [], "data": []})
    preflight_check_models({"SIFTER_MODEL": "vendor/sifter", "AGENT_MODEL": "vendor/agent"}, "sk-detector", agent_api_key="sk-agent", transport=httpx.MockTransport(handler))
    by_model = dict(seen)
    assert by_model["vendor/sifter"] == "Bearer sk-detector"
    assert by_model["vendor/agent"] == "Bearer sk-agent"


def test_no_raw_exception_text_reaches_the_preflight_output():
    class Boom(httpx.HTTPError): pass
    def handler(request): raise Boom("Authorization: Bearer sk-SENTINEL-not-a-real-key")
    failures = preflight_check_models({"SIFTER_MODEL": "vendor/sifter"}, "sk-detector", transport=httpx.MockTransport(handler))
    assert len(failures) == 2  # sifter failure + agent key missing
    assert "SENTINEL" not in failures[0]
    assert "Boom" in failures[0]


def test_an_http_failure_still_reports_its_status_code():
    def handler(request): return httpx.Response(404, json={"error": "No endpoints found"})
    failures = preflight_check_models({"SIFTER_MODEL": "vendor/gone"}, "sk-detector", transport=httpx.MockTransport(handler))
    assert "404" in failures[0]


def test_a_missing_agent_key_is_reported_rather_than_skipped():
    failures = preflight_check_models({}, "sk-detector", agent_api_key="", transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    assert any("AGENT_OPENROUTER_API_KEY" in f for f in failures)


def test_preflight_check_models_passes_when_all_configured_tiers_respond_ok():
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/embeddings"):
            return httpx.Response(200, json={"data": []})
        return httpx.Response(200, json={"choices": []})

    env = {"SIFTER_MODEL": "vendor/sifter", "INSPECTOR_MODEL": "vendor/inspector", "EMBED_MODEL": "vendor/embed"}
    failures = preflight_check_models(env, "sk-test", transport=httpx.MockTransport(handler))

    # agent_api_key not passed, agent probe reports missing key
    assert len(failures) == 1
    assert "AGENT_OPENROUTER_API_KEY" in failures[0]


def test_preflight_check_models_reports_a_404_for_the_failing_model():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["model"] == "vendor/gone":
            return httpx.Response(404, json={"error": "No endpoints found"})
        return httpx.Response(200, json={"choices": []})

    env = {"SIFTER_MODEL": "vendor/gone", "INSPECTOR_MODEL": "vendor/inspector"}
    failures = preflight_check_models(env, "sk-test", transport=httpx.MockTransport(handler))

    # agent_api_key not passed, agent probe reports missing key
    assert len(failures) == 2
    assert "sifter" in failures[0]
    assert "vendor/gone" in failures[0]


def test_preflight_check_models_skips_tiers_with_no_env_var_set():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json={"choices": []})

    failures = preflight_check_models({}, "sk-test", transport=httpx.MockTransport(handler))

    # agent_api_key not passed, agent probe reports missing key
    assert len(failures) == 1
    assert "AGENT_OPENROUTER_API_KEY" in failures[0]
    assert calls == []


def test_preflight_check_models_posts_embeddings_endpoint_for_embed_tier():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"data": []})

    env = {"EMBED_MODEL": "vendor/embed"}
    failures = preflight_check_models(env, "sk-test", transport=httpx.MockTransport(handler))

    # agent_api_key not passed, agent probe reports missing key
    assert len(failures) == 1
    assert "AGENT_OPENROUTER_API_KEY" in failures[0]
    assert captured["url"] == "https://openrouter.ai/api/v1/embeddings"
    assert captured["body"]["model"] == "vendor/embed"
