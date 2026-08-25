from __future__ import annotations

import json
import os
import sys
import uuid

from .agent_loop import build_tool_registry, run_agent
from .model_client import OpenRouterModelClient, _DEFAULT_MODEL
from .schema import ToolCall, Transcript, Turn
from .state import fresh_state


def _tool_call_to_dict(tc: ToolCall | None) -> dict | None:
    if tc is None:
        return None
    return {
        "tool_name": tc.tool_name, "arguments": tc.arguments, "result": tc.result, "status": tc.status,
        "arguments_parse_failed": tc.arguments_parse_failed,
        "raw_arguments": tc.raw_arguments,
    }


def _turn_to_dict(turn: Turn) -> dict:
    return {"seq": turn.seq, "role": turn.role, "content": turn.content, "tool_call": _tool_call_to_dict(turn.tool_call)}


def transcript_to_dict(transcript: Transcript) -> dict:
    return {
        "session_id": transcript.session_id,
        "turns": [_turn_to_dict(t) for t in transcript.turns],
        "stop_reason": transcript.stop_reason,
        "model_retry_count": transcript.model_retry_count,
    }


def _extract_scenario(data: dict) -> tuple[str, str]:
    case_id = data.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError("input JSON must have a non-empty string 'case_id'")
    transcript = data.get("transcript")
    if not isinstance(transcript, dict):
        raise ValueError("input JSON must have a 'transcript' object")
    turns = transcript.get("turns")
    if not isinstance(turns, list) or len(turns) != 1:
        raise ValueError("input 'transcript.turns' must contain exactly one seed turn")
    seed = turns[0]
    if seed.get("role") != "user" or not isinstance(seed.get("content"), str) or not seed["content"]:
        raise ValueError("the seed turn must have role 'user' and non-empty string content")
    return case_id, seed["content"]


def run_case(data: dict, model_client) -> dict:
    case_id, scenario = _extract_scenario(data)
    state = fresh_state()
    transcript = run_agent(
        scenario=scenario,
        tools=build_tool_registry(),
        state=state,
        model_client=model_client,
        # Opaque per-invocation identifier, deliberately disconnected from
        # case_id (which reveals the ground-truth label, e.g. "malicious_001",
        # to the detector — Gap 14, A1).
        session_id=uuid.uuid4().hex,
    )
    return transcript_to_dict(transcript)


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
        model = os.environ.get("AGENT_MODEL") or _DEFAULT_MODEL
        result = run_case(data, OpenRouterModelClient(model=model))
    except Exception as exc:
        # Never propagate the raw exception message — may contain the
        # OpenRouter API key (same discipline as agent_loop.py's own
        # exception handling).
        print(f"run_case failed: {exc.__class__.__name__}", file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
