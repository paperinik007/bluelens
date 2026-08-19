from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

CommandRunner = Callable[[list[str], bytes, float], "CommandResult"]

# Matches VENDOR_PROXY_LOG_PATH in docker-compose.yml (Task 4) and the default
# read by collect_thin_proxy_log (Task 8) — one fixed path, three places that
# must agree on it.
THIN_PROXY_LOG_PATH = "/var/log/vendor_proxy.jsonl"


@dataclass
class CommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    failed_to_start: bool = False


def default_command_runner(cmd: list[str], stdin_bytes: bytes, timeout_s: float) -> "CommandResult":
    try:
        proc = subprocess.run(cmd, input=stdin_bytes, capture_output=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        return CommandResult(returncode=-1, stdout=exc.stdout or b"", stderr=exc.stderr or b"", timed_out=True)
    except OSError:
        return CommandResult(returncode=-1, stdout=b"", stderr=b"", failed_to_start=True)
    return CommandResult(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def _error_verdict(case_id: str, error_kind: str, detail: str) -> dict:
    return {
        "case_id": case_id,
        "tool_name": "agentic_threat_detection",
        "status": "error",
        "error_kind": error_kind,
        "label": None,
        "confidence": None,
        "technique_detected": None,
        "rationale": detail,
        "cost_usd": None,
        "latency_s": None,
        "in_tokens": None,
        "out_tokens": None,
    }


def run_test_case(
    test_case: dict,
    *,
    command_index: int,
    agent_timeout_s: float = 120.0,
    detector_timeout_s: float = 180.0,
    run_command: CommandRunner = default_command_runner,
) -> dict:
    """Drive one TestCase through agent -> detector (design doc, 'Meccanismo di
    handoff'). Never imports aidr or detector_adapter — the JSON contract on
    stdin/stdout is the only thing this function knows about either side.

    Returns {"transcript": <Transcript JSON dict or None>, "verdict": <Verdict
    JSON dict>} — transcript is None only when the agent invocation itself
    failed before producing one (council-skeptic finding, Gap 9 targeted
    council: Plan 4 needs the transcript for the report's "Casi concreti"
    section — an earlier draft of this plan discarded it here, which would
    have forced Plan 4 to change this function's signature anyway)."""
    case_id = test_case["case_id"]

    agent_cmd = ["docker", "compose", "exec", "-T", "agent", "python", "-m", "toy_agent.run_case"]
    agent_input = json.dumps(test_case).encode("utf-8")
    agent_result = run_command(agent_cmd, agent_input, agent_timeout_s)

    if agent_result.failed_to_start:
        return {"transcript": None, "verdict": _error_verdict(case_id, "infra", "docker compose exec failed to start the agent invocation")}
    if agent_result.timed_out:
        return {"transcript": None, "verdict": _error_verdict(case_id, "infra", f"agent invocation exceeded {agent_timeout_s}s wall-clock timeout")}
    if agent_result.returncode != 0:
        return {"transcript": None, "verdict": _error_verdict(case_id, "application", agent_result.stderr.decode("utf-8", errors="replace"))}

    transcript_bytes = agent_result.stdout
    try:
        transcript_dict = json.loads(transcript_bytes)
    except json.JSONDecodeError:
        return {"transcript": None, "verdict": _error_verdict(case_id, "application", "agent produced invalid JSON on stdout despite exit code 0")}

    # Append-only marker instead of truncating (design doc, Gap 14/15,
    # 'Raccolta prove del thin-proxy log'): the old truncation existed only
    # for per-case attribution (vendor_proxy runs as one long-lived process
    # for the detector container's whole life), never a security mechanism —
    # deleting log content in the observed container proves nothing about
    # what the container itself retains. The marker turns the log into a
    # complete, continuous corpus for the whole sequence instead: nothing is
    # ever lost, and command_index (this command's position in the calling
    # sequence, supplied by execute_sequence) plus case_id let a reader
    # attribute every line without needing to isolate files per case.
    marker = json.dumps({
        "marker": True,
        "case_id": case_id,
        "command_index": command_index,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    run_command(
        ["docker", "compose", "exec", "-T", "detector", "sh", "-c", f"echo {shlex.quote(marker)} >> {THIN_PROXY_LOG_PATH}"],
        b"",
        10.0,
    )

    detector_cmd = ["docker", "compose", "exec", "-T", "detector", "python", "-m", "detector_adapter.evaluate_case"]
    detector_result = run_command(detector_cmd, transcript_bytes, detector_timeout_s)

    if detector_result.failed_to_start:
        return {"transcript": transcript_dict, "verdict": _error_verdict(case_id, "infra", "docker compose exec failed to start the detector invocation")}
    if detector_result.timed_out:
        # Last-resort fallback only (council-skeptic finding, Gap 9 targeted
        # council): evaluate_case.py (Task 6) now enforces its own internal
        # wall-clock deadline and terminates its MCP subprocesses via direct
        # process handles before exiting — this external cleanup only matters
        # if that internal mechanism somehow didn't fire (e.g. a bug, or
        # signal delivery delayed inside a C extension that doesn't check for
        # interrupts). Two patterns, not one: the evaluate_case process
        # itself (if the internal deadline never fired, it's still the
        # parent holding everything up — a single external pkill targeting
        # only "aidr/providers", as an earlier draft of this plan did, would
        # never touch that parent) and its MCP provider children (in case
        # the parent died but a child survived it, since killing a parent
        # does not cascade-kill children on Linux). Both best-effort,
        # non-fatal — a risk of degradation for the rest of the sequential
        # batch, not of total blockage, per the design doc.
        run_command(
            ["docker", "compose", "exec", "-T", "detector", "pkill", "-f", "detector_adapter.evaluate_case"],
            b"",
            10.0,
        )
        run_command(
            ["docker", "compose", "exec", "-T", "detector", "pkill", "-f", "aidr/providers"],
            b"",
            10.0,
        )
        return {"transcript": transcript_dict, "verdict": _error_verdict(case_id, "infra", f"detector invocation exceeded {detector_timeout_s}s wall-clock timeout")}
    if detector_result.returncode != 0:
        # A clean nonzero exit (not timed_out) can still mean evaluate_case.py's
        # own internal deadline (Task 6) fired *during* AgenticThreatDetectionAdapter()
        # construction — before evaluate_case.py has an adapter handle to call
        # terminate_subprocesses() on (final-review finding: Pipeline()/Inspector's
        # blocking per-provider MCP handshake happens inside that constructor, so a
        # hang there raises TimeoutError with adapter still None). evaluate_case.py
        # exits 1 either way and prints "evaluate_case failed: TimeoutError" to
        # stderr (see the except TimeoutError branch there) — that message is the
        # only signal available here that its self-cleanup couldn't run. Same
        # fallback pkill pair as the timed_out branch above, for the same reason:
        # a still-running evaluate_case parent (unlikely on this path, but the
        # first pkill is harmless if it's already gone) and/or orphaned MCP
        # provider children left behind by the unfinished construction.
        if b"TimeoutError" in detector_result.stderr:
            run_command(
                ["docker", "compose", "exec", "-T", "detector", "pkill", "-f", "detector_adapter.evaluate_case"],
                b"",
                10.0,
            )
            run_command(
                ["docker", "compose", "exec", "-T", "detector", "pkill", "-f", "aidr/providers"],
                b"",
                10.0,
            )
        return {"transcript": transcript_dict, "verdict": _error_verdict(case_id, "application", detector_result.stderr.decode("utf-8", errors="replace"))}

    try:
        verdict_dict = json.loads(detector_result.stdout)
    except json.JSONDecodeError:
        return {"transcript": transcript_dict, "verdict": _error_verdict(case_id, "application", "detector produced invalid JSON on stdout despite exit code 0")}

    # Never trust the detector's echoed case_id (Gap 14, A1) — session_id sent
    # to it is now an opaque per-invocation UUID, not case_id, so whatever it
    # echoes back is not ground truth. The orchestrator already knows the real
    # case_id independently, same as every error branch above.
    verdict_dict["case_id"] = case_id
    return {"transcript": transcript_dict, "verdict": verdict_dict}
