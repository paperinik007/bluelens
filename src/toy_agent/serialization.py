from __future__ import annotations

from .schema import ToolCall, Transcript, Turn, Verdict


def _tool_call_from_dict(d: dict | None) -> ToolCall | None:
    if d is None:
        return None
    return ToolCall(
        tool_name=d["tool_name"],
        arguments=d["arguments"],
        result=d.get("result"),
        status=d["status"],
        arguments_parse_failed=d.get("arguments_parse_failed", False),
        raw_arguments=d.get("raw_arguments"),
    )


def _turn_from_dict(d: dict) -> Turn:
    return Turn(seq=d["seq"], role=d["role"], content=d["content"], tool_call=_tool_call_from_dict(d.get("tool_call")))


def transcript_from_dict(d: dict) -> Transcript:
    """Inverse of run_case.py::transcript_to_dict (design doc decision 3)."""
    return Transcript(
        session_id=d["session_id"],
        turns=[_turn_from_dict(t) for t in d.get("turns", [])],
        stop_reason=d.get("stop_reason"),
        model_retry_count=d.get("model_retry_count", 0),
    )


_VERDICT_FIELDS = (
    "case_id", "tool_name", "status", "label", "confidence",
    "technique_detected", "rationale", "cost_usd", "latency_s",
)


def verdict_from_dict(d: dict) -> Verdict:
    """Inverse of detector_adapter's Verdict-shaped dicts (design doc decision 3).

    Only known Verdict fields are read — extra keys (in_tokens, out_tokens,
    error_kind) are silently ignored here; they are never lost, only absent
    from the in-memory dataclass, because the raw dict is persisted to disk
    before this function is ever called (decision 6)."""
    kwargs = {k: d[k] for k in _VERDICT_FIELDS if k in d}
    return Verdict(**kwargs)
