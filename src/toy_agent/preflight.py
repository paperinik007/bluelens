from __future__ import annotations

from typing import Mapping

import httpx

from .model_client import _DEFAULT_MODEL

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Vendor -> {tier -> host env var}. aidr checks 3 tiers (Sifter/Inspector/
# embed), llamafirewall checks its own single model tier — this is a
# rewrite of "which tiers to check, with which key" per vendor, not an
# added branch (self-review finding, v3).
TIER_ENV_VARS_BY_VENDOR: dict[str, dict[str, str]] = {
    "aidr": {
        "sifter": "SIFTER_MODEL",
        "inspector": "INSPECTOR_MODEL",
        "embed": "EMBED_MODEL",
    },
    "llamafirewall": {
        "llamafirewall": "LLAMAFIREWALL_MODEL",
    },
}

AGENT_ENV_VAR = "AGENT_MODEL"


def _probe_request(tier: str, model: str) -> tuple[str, dict]:
    if tier == "embed":
        return "/embeddings", {"model": model, "input": "ping"}
    return "/chat/completions", {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
    }


def _client(api_key: str, transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        base_url=OPENROUTER_BASE_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30.0,
        transport=transport,
    )


def _probe(client: httpx.Client, tier: str, model: str) -> str | None:
    """One minimal live OpenRouter call. Returns None on success, or a
    human-readable failure description on error. Never echoes raw exception
    text — the OpenRouter API key is in the Authorization header and an
    uncaught exception could leak it."""
    path, body = _probe_request(tier, model)
    try:
        response = client.post(path, json=body)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return f"{tier} ({model}): HTTP {exc.response.status_code}"
    except Exception as exc:
        return f"{tier} ({model}): {exc.__class__.__name__}"
    else:
        return None


def preflight_check_models(
    env: Mapping[str, str],
    api_key: str,
    *,
    vendor: str,
    agent_api_key: str = "",
    transport: httpx.BaseTransport | None = None,
) -> list[str]:
    """One minimal live OpenRouter call per configured tier model for the
    active vendor, run on the host before any container opens (Gap 10: a
    third-party model catalog ages). `vendor` selects which tiers to check
    and is required — no default (principio 8).

    Only tiers whose env var is actually set are checked. The agent model
    is always probed regardless of vendor; if AGENT_OPENROUTER_API_KEY is
    not set, the missing-key failure is reported instead of the probe.

    Returns one description per model that failed to respond; an empty list
    means every configured tier responded successfully.
    """
    failures: list[str] = []

    detector_client = _client(api_key, transport)
    for tier, env_var in TIER_ENV_VARS_BY_VENDOR[vendor].items():
        model = env.get(env_var)
        if not model:
            continue
        failure = _probe(detector_client, tier, model)
        if failure:
            failures.append(failure)

    agent_model = env.get(AGENT_ENV_VAR) or _DEFAULT_MODEL
    if not agent_api_key:
        failures.append(f"agent ({agent_model}): AGENT_OPENROUTER_API_KEY is not set")
    else:
        failure = _probe(_client(agent_api_key, transport), "agent", agent_model)
        if failure:
            failures.append(failure)

    return failures
