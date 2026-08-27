from __future__ import annotations

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
