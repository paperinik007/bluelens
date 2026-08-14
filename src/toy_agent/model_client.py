from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

# Pricing per 1M tokens (input, output), USD. This drives the toy agent's own
# reasoning — a different model from the vendor's Sifter/Inspector under test.
_PRICING_PER_MILLION_TOKENS: dict[str, tuple[float, float]] = {
    "openai/gpt-4o-mini": (0.15, 0.60),
}

_DEFAULT_MODEL = "openai/gpt-4o-mini"


@dataclass
class ModelReply:
    content: str
    tool_calls: list[dict[str, Any]]
    cost_usd: float


class OpenRouterModelClient:
    def __init__(self, model: str = _DEFAULT_MODEL, api_key: str | None = None) -> None:
        self._model = model
        if model not in _PRICING_PER_MILLION_TOKENS:
            raise ValueError(f"no known pricing for model {model!r}")
        key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        self._client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelReply:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools,
        )
        choice = response.choices[0].message
        usage = response.usage
        cost_usd = compute_cost_usd(self._model, usage.prompt_tokens, usage.completion_tokens)
        tool_calls = [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in (choice.tool_calls or [])
        ]
        return ModelReply(content=choice.content or "", tool_calls=tool_calls, cost_usd=cost_usd)


def compute_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    if model not in _PRICING_PER_MILLION_TOKENS:
        raise ValueError(f"no known pricing for model {model!r}")
    in_price, out_price = _PRICING_PER_MILLION_TOKENS[model]
    return (prompt_tokens / 1_000_000) * in_price + (completion_tokens / 1_000_000) * out_price
