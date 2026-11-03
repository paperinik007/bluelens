from __future__ import annotations

import asyncio
import json
import sys
import time

from .adapter import promptguard_error_verdict, promptguard_inputs, promptguard_verdict


def run_evaluate_case_promptguard(data: dict) -> dict:
    """PromptGuard 2 (86M) alone, configured as the vendor's default: the user's messages and the results of the
    tools, vendor threshold (create_scanner's default). No AlignmentCheck, no fusion."""
    from llamafirewall import ScannerType, ToolMessage, UserMessage
    from llamafirewall.llamafirewall import create_scanner

    case_id = data["session_id"]
    inputs = promptguard_inputs(data)
    try:
        scanner = create_scanner(ScannerType.PROMPT_GUARD)
        t0 = time.perf_counter()
        scans = []
        for item in inputs:
            message_class = UserMessage if item["source"] == "user" else ToolMessage
            scans.append((item, asyncio.run(scanner.scan(message_class(content=item["text"]), None))))
        latency_s = time.perf_counter() - t0
    except Exception as exc:
        return promptguard_error_verdict(case_id, exc.__class__.__name__)
    verdict = promptguard_verdict(case_id, scans, latency_s)
    verdict["block_threshold"] = scanner.block_threshold
    return verdict


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
        result = run_evaluate_case_promptguard(data)
    except Exception as exc:
        print(f"evaluate_case_promptguard failed: {exc.__class__.__name__}", file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
