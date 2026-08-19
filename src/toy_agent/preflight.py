from __future__ import annotations

from typing import Mapping

import httpx

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Tier -> host env var name. Duplicated by name only from
# detector_adapter/vendor_proxy.py's TIER_TO_ENV_VAR, never imported —
# toy_agent never imports detector_adapter (same boundary run_test_case/
# execute_sequence already declare, orchestrator.py/sequence.py).
TIER_ENV_VARS: dict[str, str] = {
    "sifter": "SIFTER_MODEL",
    "inspector": "INSPECTOR_MODEL",
    "embed": "EMBED_MODEL",
}


def _probe_request(tier: str, model: str) -> tuple[str, dict]:
    if tier == "embed":
        return "/embeddings", {"model": model, "input": "ping"}
    return "/chat/completions", {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
    }


def preflight_check_models(
    env: Mapping[str, str],
    api_key: str,
    *,
    transport: httpx.BaseTransport | None = None,
) -> list[str]:
    """One minimal live OpenRouter call per configured tier model, run on the
    host before any container opens. A third-party model catalog ages (Gap
    10): a model can be listed as available on OpenRouter's own product page
    and still 404 "No endpoints found" at real call time — the exact failure
    that hit qwen/qwen3-4b during Gap 10's setup, caught only by a live probe.

    Only tiers whose env var is actually set in `env` are checked — same
    requirement already documented for DETECTOR_OPENROUTER_API_KEY (README:
    must be exported in the host shell, not only present in .env). A tier
    left unset here is not verified, it falls back to detector_adapter's own
    default at container-run time.

    Returns one description per model that failed to respond; an empty list
    means every configured tier responded successfully.
    """
    client = httpx.Client(
        base_url=OPENROUTER_BASE_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30.0,
        transport=transport,
    )
    failures: list[str] = []
    for tier, env_var in TIER_ENV_VARS.items():
        model = env.get(env_var)
        if not model:
            continue
        path, body = _probe_request(tier, model)
        try:
            response = client.post(path, json=body)
            response.raise_for_status()
        except Exception as exc:
            failures.append(f"{tier} ({model}): {exc}")
    return failures
