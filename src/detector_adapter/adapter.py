from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SERVER_NAME = "toy_support"
# Identifies which detector produced a Verdict (design doc, "Schema di misura")
# — a constant today (one detector active per audit, design doc, "Limiti
# dichiarati"), populated so a future second-vendor Verdict is distinguishable
# without a schema change.
DETECTOR_TOOL_NAME = "agentic_threat_detection"


def _build_messages(turns: list[dict]) -> list[Any]:
    # Lazy import: this function is the one place that actually needs aidr's
    # real dataclasses (Pipeline().analyze() reads ev.messages/len(ev.messages)
    # directly, so a duck-typed stand-in wouldn't do) — keeping the import out
    # of module scope keeps detection_result_to_verdict and the CLI wiring in
    # evaluate_case.py importable on a host without aidr installed.
    from aidr.schema.agent_event import ChatMessage, ToolUsage

    messages: list[Any] = []
    for turn in turns:
        role = turn["role"]
        seq = turn["seq"]
        if role == "user":
            messages.append(ChatMessage(seq=seq, role="user", message_type="user_prompt", content=turn["content"]))
        elif role == "assistant":
            messages.append(ChatMessage(seq=seq, role="assistant", message_type="agent_response", content=turn["content"]))
        elif role == "tool":
            call = turn["tool_call"]
            usage = ToolUsage(
                tool_name=f"{SERVER_NAME}.{call['tool_name']}",
                server_name=SERVER_NAME,
                arguments=call["arguments"],
                result=call.get("result"),
                status=call.get("status", "ok"),
                call_id=f"call_{seq}",
            )
            messages.append(ChatMessage(seq=seq, role="assistant", message_type="tool_calling", content="", tool_calls=[usage]))
            messages.append(ChatMessage(seq=seq, role="tool", message_type="tool_result", content=call.get("result") or ""))
        else:
            raise ValueError(f"unknown turn role: {role!r}")
    return messages


def transcript_dict_to_agent_event(transcript: dict):
    """Build an AgentEvent from a Transcript JSON dict (design doc, 'Adapter').

    Reads the JSON's keys directly — never deserializes a toy_agent.schema.Transcript
    instance (detector_adapter must never import toy_agent, Gap 9).
    """
    from aidr.schema.agent_event import AgentEvent

    return AgentEvent(
        session_id=transcript["session_id"],
        source="toy_agent",
        timestamp=datetime.now(timezone.utc),
        declared_servers=[SERVER_NAME],
        messages=_build_messages(transcript["turns"]),
    )


def detection_result_to_verdict(case_id: str, result: Any) -> dict:
    """Normalize a vendor DetectionResult (duck-typed here — only attribute
    access, no isinstance check, so this stays testable without aidr) into
    our Verdict JSON shape.

    in_tokens/out_tokens are carried through as extra keys, not part of the
    toy_agent.schema.Verdict shape (which has no such fields) — preserved so
    Plan 4's metrics module can compute cost_usd from them later without
    reopening this function (council-skeptic finding, Gap 9 targeted council:
    discarding them here would make cost_usd permanently uncomputable, since
    DetectionResult is the only object that ever has them)."""
    technique = result.technique
    return {
        "case_id": case_id,
        "tool_name": DETECTOR_TOOL_NAME,
        "status": "ok",
        "label": "malicious" if result.is_malicious else "benign",
        "confidence": result.confidence,
        "technique_detected": None if technique in (None, "N/A") else technique,
        "rationale": result.explanation or None,
        "cost_usd": None,
        "latency_s": result.latency_s,
        "in_tokens": result.in_tokens,
        "out_tokens": result.out_tokens,
    }


class AgenticThreatDetectionAdapter:
    """TargetAdapter for agentic-threat-detection (aidr), pinned commit
    7fad14d2478707e68a09b8ecd9942dec8fde1614. Bypasses Dredge — builds an
    AgentEvent directly from the Transcript JSON dict received on stdin, calls
    Pipeline().analyze(), normalizes the result."""

    def __init__(self, pipeline: Any = None) -> None:
        if pipeline is not None:
            self._pipeline = pipeline
        else:
            from aidr.detector.pipeline import Pipeline
            self._pipeline = Pipeline()

    def evaluate(self, transcript: dict) -> dict:
        case_id = transcript["session_id"]
        ev = transcript_dict_to_agent_event(transcript)
        result = self._pipeline.analyze(ev)
        return detection_result_to_verdict(case_id, result)

    def terminate_subprocesses(self) -> None:
        """Best-effort termination of the real MCP provider subprocesses
        Inspector spawned (SourceLens/ThreatLens/PolicyLens) — called by
        evaluate_case.py's internal wall-clock deadline handler on expiry,
        never by evaluate() itself. Design doc, 'Meccanismo di handoff':
        cleanup 'dal processo evaluate_case stesso, prima di uscire' — the
        option this plan implements as primary (council-skeptic finding, Gap
        9 targeted council: an external pkill from outside the container
        cannot reach a hung Inspector call itself, only its child
        subprocesses at best — this method reaches both, via direct process
        handles, no name-pattern guessing). Never raises — an exception here
        would mask the real TimeoutError already being handled by the
        caller."""
        router = getattr(getattr(self._pipeline, "inspector", None), "router", None)
        if router is None:
            return
        try:
            clients = router.clients.values()
        except Exception:
            # router exists but is some partially-constructed/malformed shape
            # (e.g. no .clients, or .clients isn't dict-like) — exactly the
            # kind of mid-operation state this method is called to clean up
            # after (evaluate_case.py's except TimeoutError handler). Degrade
            # to "did nothing" rather than propagate, same discipline as the
            # per-client terminate/wait/kill fallback below.
            return
        for client in clients:
            proc = getattr(client, "proc", None)
            if proc is None or proc.poll() is not None:
                continue
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
