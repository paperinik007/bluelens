from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import openai
from openai import OpenAI

_DEFAULT_MODEL = "openai/gpt-4o-mini"

MAX_TOKENS = 2048
REQUEST_TIMEOUT_S = 20.0

TRANSIENT_EXCEPTIONS = (openai.APIConnectionError, openai.APITimeoutError, openai.RateLimitError)
MAX_RETRIES_PER_CASE = 2
BACKOFF_S = (1.0, 3.0)


@dataclass
class ModelReply:
    content: str
    tool_calls: list[dict[str, Any]]
    cost_usd: float


class OpenRouterModelClient:
    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        api_key: str | None = None,
        sleep=time.sleep,
        reasoning_effort: str | None = None,
        provider: str | None = None,
        request_timeout_s: float = REQUEST_TIMEOUT_S,
        clock=time.monotonic,
    ) -> None:
        self._model = model
        # Both sent explicitly when set, never left to the provider's default,
        # which can change (SPIRIT.md principle 8). Unset: the request is the
        # same as in the published runs.
        self._extra_body: dict[str, Any] = {}
        if reasoning_effort is not None:
            self._extra_body["reasoning"] = {"effort": reasoning_effort}
        if provider is not None:
            self._extra_body["provider"] = {"order": [provider], "allow_fallbacks": False}
        self._request_timeout_s = request_timeout_s
        self._clock = clock
        # One entry per attempt: returned model and provider (a change stops
        # the run, measurement conditions), duration, cost or error class.
        self.call_log: list[dict[str, Any]] = []
        key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        self._client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
        self._sleep = sleep
        self.retry_count = 0

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelReply:
        while True:
            try:
                return self._complete_once(messages, tools)
            except TRANSIENT_EXCEPTIONS:
                if self.retry_count >= MAX_RETRIES_PER_CASE:
                    raise
                backoff = BACKOFF_S[self.retry_count]
                self.retry_count += 1
                self._sleep(backoff)

    def _complete_once(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ModelReply:
        kwargs: dict[str, Any] = dict(
            model=self._model,
            messages=messages,
            tools=tools,
            max_tokens=MAX_TOKENS,
            timeout=self._request_timeout_s,
        )
        if self._extra_body:
            kwargs["extra_body"] = self._extra_body
        started = self._clock()
        try:
            response = self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            # Class name only: the message may carry the API key.
            self.call_log.append({
                "generation_id": None, "model": None, "provider": None, "service_tier": None, "reasoning_tokens": None,
                "duration_s": self._clock() - started, "cost_usd": None, "error": exc.__class__.__name__,
            })
            raise
        duration_s = self._clock() - started
        choice = response.choices[0].message
        usage = response.usage
        cost_usd = getattr(usage, "cost", None)
        self.call_log.append({
            # OpenRouter returns the model alias; the exact version is in its
            # generation record, looked up afterwards by this id.
            "generation_id": getattr(response, "id", None),
            "model": getattr(response, "model", None),
            "provider": getattr(response, "provider", None),
            "service_tier": getattr(response, "service_tier", None),
            "reasoning_tokens": getattr(getattr(usage, "completion_tokens_details", None), "reasoning_tokens", None),
            "duration_s": duration_s,
            "cost_usd": cost_usd,
            "error": None,
        })
        if cost_usd is None:
            raise ValueError("OpenRouter response carried no usage.cost")
        tool_calls = [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in (choice.tool_calls or [])
        ]
        return ModelReply(content=choice.content or "", tool_calls=tool_calls, cost_usd=cost_usd)

