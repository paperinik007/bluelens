from __future__ import annotations

import json
import sys

from .adapter import OpenRouterAlignmentCheck, TOOL_NAME, fail_open_verdict, scan_decision_to_verdict, transcript_dict_to_trace


def run_evaluate_case(data: dict) -> dict:
    from llamafirewall import LlamaFirewall, Role

    case_id = data["session_id"]
    trace = transcript_dict_to_trace(data)

    OpenRouterAlignmentCheck.fail_open_detected = False
    OpenRouterAlignmentCheck.fail_open_exception_class = None

    firewall = LlamaFirewall(scanners={Role.ASSISTANT: [TOOL_NAME]})
    scan_result = firewall.scan_replay(trace)

    if OpenRouterAlignmentCheck.fail_open_detected:
        return fail_open_verdict(case_id, OpenRouterAlignmentCheck.fail_open_exception_class)
    return scan_decision_to_verdict(case_id, scan_result)


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
