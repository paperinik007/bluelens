from __future__ import annotations

import os
from typing import Any

TOOL_NAME = "llamafirewall-alignmentcheck"


def scan_decision_to_verdict(case_id: str, scan_result: Any) -> dict:
    """Normalize a llamafirewall ScanResult (duck-typed here — only attribute
    access, no isinstance check, so this stays testable without llamafirewall
    installed) into our Verdict JSON shape. Mirrors
    detector_adapter.vendors.aidr.adapter.detection_result_to_verdict.

    decision is compared by .value (a plain string on the real ScanDecision
    enum) rather than by importing ScanDecision — never needs llamafirewall
    importable to be called or tested."""
    decision_value = getattr(scan_result.decision, "value", scan_result.decision)
    is_malicious = decision_value == "human_in_the_loop_required"
    return {
        "case_id": case_id,
        "tool_name": TOOL_NAME,
        "status": "ok",
        "label": "malicious" if is_malicious else "benign",
        "confidence": scan_result.score,
        "technique_detected": None,
        "rationale": scan_result.reason or None,
        "cost_usd": None,
        "latency_s": None,
        "in_tokens": None,
        "out_tokens": None,
    }


def transcript_dict_to_trace(transcript: dict) -> list:
    """Build a llamafirewall Trace (list of Message) from a Transcript JSON
    dict (same wire format aidr's adapter consumes on stdin) — never
    deserializes a toy_agent.schema.Transcript instance (detector_adapter
    must never import toy_agent, Gap 9).

    Lazy import (function-local, not module-level): keeps this module
    importable without llamafirewall installed for anything that doesn't
    call this function — same pattern as _build_messages in
    detector_adapter/vendors/aidr/adapter.py."""
    from llamafirewall import AssistantMessage, ToolMessage, UserMessage

    messages: list = []
    for turn in transcript["turns"]:
        role = turn["role"]
        if role == "user":
            messages.append(UserMessage(content=turn["content"]))
        elif role == "assistant":
            messages.append(AssistantMessage(content=turn["content"]))
        elif role == "tool":
            call = turn["tool_call"]
            action_text = f"ACTION: {call['tool_name']}\nACTION INPUT: {call['arguments']}"
            messages.append(AssistantMessage(content=action_text))
            messages.append(ToolMessage(content=call.get("result") or ""))
        else:
            raise ValueError(f"unknown turn role: {role!r}")
    return messages


try:
    from llamafirewall import register_llamafirewall_scanner
    from llamafirewall.scanners.custom_check_scanner import CustomCheckScanner
    from llamafirewall.scanners.experimental.alignmentcheck_scanner import (
        AlignmentCheckOutputSchema,
        AlignmentCheckScanner,
        SYSTEM_PROMPT,
    )
except ImportError:
    OpenRouterAlignmentCheck = None  # llamafirewall not installed on this host
else:
    # Verified live (Step 0, deferred in this run — see above) at
    # implementation time, not only at pre-design falsification — a
    # third-party model catalog ages (Gap 10, same lesson already applied to
    # aidr's SIFTER_MODEL/INSPECTOR_MODEL).
    DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct"
    API_BASE_URL = "http://127.0.0.1:8200/v1"  # local proxy (a later task), single port — no tier remap needed
    API_KEY_ENV_VAR = "LLAMAFIREWALL_OPENROUTER_API_KEY"

    @register_llamafirewall_scanner(TOOL_NAME)
    class OpenRouterAlignmentCheck(AlignmentCheckScanner):
        """AlignmentCheckScanner pointed at OpenRouter via our local proxy,
        instead of Together — bypasses AlignmentCheckScanner.__init__
        (hardcodes Together's api_base_url/api_key_env_var) by calling
        CustomCheckScanner.__init__ directly. Zero-argument constructor:
        llamafirewall.llamafirewall.create_scanner() instantiates a
        registered custom scanner with scanner_class() — no arguments."""

        fail_open_detected: bool = False
        fail_open_exception_class: str | None = None

        def __init__(self, model_name: str | None = None) -> None:
            model = model_name or os.environ.get("LLAMAFIREWALL_MODEL") or DEFAULT_MODEL
            CustomCheckScanner.__init__(
                self,
                scanner_name=TOOL_NAME,
                system_prompt=SYSTEM_PROMPT,
                output_schema=AlignmentCheckOutputSchema,
                model_name=model,
                api_base_url=API_BASE_URL,
                api_key_env_var=API_KEY_ENV_VAR,
            )
            self.require_full_trace = True

        async def _evaluate_with_llm(self, text: str) -> AlignmentCheckOutputSchema:
            """Overrides CustomCheckScanner._evaluate_with_llm (verified on
            llamafirewall/scanners/custom_check_scanner.py:68-80) to record a
            vendor fail-open before its own default silently substitutes
            conclusion=True — same interception point the vendor's own test
            suite patches. The class attribute (not self) is what
            create_scanner()'s caller can actually read afterward."""
            try:
                return await self.llm.call(
                    prompt=text, system_prompt=self.system_prompt,
                    output_schema=self.output_schema, temperature=self.temperature,
                )
            except Exception as exc:
                cls = type(self)
                cls.fail_open_detected = True
                cls.fail_open_exception_class = exc.__class__.__name__
                return self._get_default_error_response()


def fail_open_verdict(case_id: str, exception_class: str | None) -> dict:
    """Verdict for a vendor fail-open (the LLM call inside
    _evaluate_with_llm raised, and AlignmentCheckScanner's own default
    silently substituted conclusion=True) — status='error'/label=None so
    metrics.py excludes it from TP/FP/FN/TN via the existing error_count
    bucket."""
    detail = f"vendor fail-open: {exception_class}" if exception_class else "vendor fail-open"
    return {
        "case_id": case_id,
        "tool_name": TOOL_NAME,
        "status": "error",
        "label": None,
        "confidence": None,
        "technique_detected": None,
        "rationale": detail,
        "cost_usd": None,
        "latency_s": None,
        "in_tokens": None,
        "out_tokens": None,
    }
