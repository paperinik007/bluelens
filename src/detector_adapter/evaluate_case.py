from __future__ import annotations

import json
import os
import signal
import sys

from .adapter import AgenticThreatDetectionAdapter

# Shorter than orchestrator.py's detector_timeout_s (Task 7, default 180s) on
# purpose (Global Constraints) — this internal deadline is meant to fire and
# let evaluate_case exit cleanly, with its own cleanup already done, before
# the orchestrator's outer timeout would otherwise have to kill the
# docker-compose-exec client and fall back to its own, less precise cleanup.
DEFAULT_DEADLINE_S = 150.0


def _install_deadline(deadline_s: float) -> None:
    if not hasattr(signal, "SIGALRM"):
        # The detector container is Linux-only (design constraint) — this
        # guard only matters when this module's tests run on a non-Linux
        # host (this repo's Windows dev machine), where SIGALRM doesn't exist
        # at all. No-op there; the real container always has it.
        return

    def _handler(signum, frame):
        raise TimeoutError(f"evaluate_case exceeded its internal {deadline_s}s deadline")

    signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, deadline_s)  # setitimer, not alarm(): sub-second precision, needed for a fast test suite


def _cancel_deadline() -> None:
    if hasattr(signal, "SIGALRM"):
        signal.setitimer(signal.ITIMER_REAL, 0)


def run_evaluate_case(data: dict, adapter) -> dict:
    return adapter.evaluate(data)


def main() -> None:
    deadline_s = float(os.environ.get("EVALUATE_CASE_DEADLINE_S", DEFAULT_DEADLINE_S))
    adapter = None
    try:
        _install_deadline(deadline_s)
        data = json.loads(sys.stdin.read())
        adapter = AgenticThreatDetectionAdapter()
        result = run_evaluate_case(data, adapter)
    except TimeoutError as exc:
        if adapter is not None:
            adapter.terminate_subprocesses()
        print(f"evaluate_case failed: {exc.__class__.__name__}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        # Global Constraints: stdout carries only the final Verdict JSON —
        # every diagnostic, here and in any future vendor's evaluate_case,
        # goes to stderr.
        print(f"evaluate_case failed: {exc.__class__.__name__}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        _cancel_deadline()
    print(json.dumps(result))


if __name__ == "__main__":
    main()
