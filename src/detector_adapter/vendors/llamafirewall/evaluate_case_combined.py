from __future__ import annotations

import asyncio
import json
import sys
import time

from .adapter import (
    OpenRouterAlignmentCheck,
    TOOL_NAME,
    aggregate_promptguard_turns,
    combine_scan_results_to_verdict,
    combined_error_verdict,
    transcript_dict_to_trace,
)

# A module-level constant so tests can monkeypatch it (module attribute
# lookup happens at call time inside _append_secondary_log, not captured as
# a default argument) — same shape as OpenRouterAlignmentCheck's class-level
# flags being readable/settable from outside the instance that set them.
SECONDARY_LOG_PATH = "/var/log/llamafirewall_promptguard_raw.jsonl"


def _append_secondary_log(text: str, result, threshold: float) -> None:
    decision_value = getattr(result.decision, "value", result.decision)
    entry = {"text": text, "score": result.score, "threshold": threshold, "decision": decision_value}
    with open(SECONDARY_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def run_evaluate_case_combined(data: dict) -> dict:
    from llamafirewall import LlamaFirewall, Role, ScannerType
    # create_scanner is not re-exported from the llamafirewall top-level
    # package in the pinned vendor version (1.0.3, verified live inside the
    # detector-llamafirewall container) — only from this submodule, same
    # path already documented in adapter.py's OpenRouterAlignmentCheck
    # docstring ("llamafirewall.llamafirewall.create_scanner()").
    from llamafirewall.llamafirewall import create_scanner

    case_id = data["session_id"]
    trace = transcript_dict_to_trace(data)

    OpenRouterAlignmentCheck.fail_open_detected = False
    OpenRouterAlignmentCheck.fail_open_exception_class = None

    firewall = LlamaFirewall(scanners={Role.ASSISTANT: [TOOL_NAME]})
    t0 = time.perf_counter()
    try:
        ac_result = firewall.scan_replay(trace)
    except Exception as exc:
        return combined_error_verdict(case_id, "alignmentcheck", exc.__class__.__name__)
    ac_latency_s = time.perf_counter() - t0

    if OpenRouterAlignmentCheck.fail_open_detected:
        return combined_error_verdict(case_id, "alignmentcheck", OpenRouterAlignmentCheck.fail_open_exception_class)

    pg_scanner = create_scanner(ScannerType.PROMPT_GUARD)
    pg_turn_results = []
    t0 = time.perf_counter()
    try:
        for ix, msg in enumerate(trace):
            if msg.role == Role.USER:
                past = trace[:ix] or None
                result = asyncio.run(pg_scanner.scan(msg, past))
                pg_turn_results.append(result)
                _append_secondary_log(msg.content, result, pg_scanner.block_threshold)
    except Exception as exc:
        return combined_error_verdict(case_id, "promptguard", exc.__class__.__name__)
    pg_latency_s = time.perf_counter() - t0

    pg_decision_value, pg_score = aggregate_promptguard_turns(pg_turn_results)
    return combine_scan_results_to_verdict(
        case_id, ac_result, pg_decision_value, pg_score, pg_turn_results, ac_latency_s, pg_latency_s,
    )


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
        result = run_evaluate_case_combined(data)
    except Exception as exc:
        print(f"evaluate_case_combined failed: {exc.__class__.__name__}", file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
