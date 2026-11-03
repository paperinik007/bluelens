from __future__ import annotations

import asyncio
import json
import sys
import time

from .adapter import OpenRouterAlignmentCheck, alignmentcheck_steps, alignmentcheck_verdict, fail_open_verdict


def run_evaluate_case(data: dict) -> dict:
    """AlignmentCheck alone, as the vendor replays a trace (LlamaFirewall.scan_replay, pinned 1.0.3): each action of
    the assistant is judged against the user's first message with the trace before it, and the replay stops at the
    first action judged misaligned. Done here action by action instead of through scan_replay so that the outcome of
    every action is kept (scan_replay returns only the last). No PromptGuard, no fusion."""
    from llamafirewall import AssistantMessage, ToolMessage, UserMessage

    case_id = data["session_id"]
    steps = alignmentcheck_steps(data)
    message_class = {"user": UserMessage, "assistant": AssistantMessage, "tool": ToolMessage}
    trace = [message_class[step["role"]](content=step["content"]) for step in steps]

    OpenRouterAlignmentCheck.fail_open_detected = False
    OpenRouterAlignmentCheck.fail_open_exception_class = None

    scanner = OpenRouterAlignmentCheck()
    scans = []
    start = time.perf_counter()
    for index, step in enumerate(steps):
        if step["role"] != "assistant":
            continue
        result = asyncio.run(scanner.scan(trace[index], trace[:index] or None))
        scans.append((step, result))
        if result.decision.value == "human_in_the_loop_required":
            break
    latency_s = time.perf_counter() - start

    if OpenRouterAlignmentCheck.fail_open_detected:
        return fail_open_verdict(case_id, OpenRouterAlignmentCheck.fail_open_exception_class)
    verdict = alignmentcheck_verdict(case_id, scans, latency_s)
    verdict["model"] = scanner.llm.model_name
    return verdict


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
        result = run_evaluate_case(data)
    except Exception as exc:
        print(f"evaluate_case failed: {exc.__class__.__name__}", file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
