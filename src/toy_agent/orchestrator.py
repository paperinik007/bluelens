from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional

CommandRunner = Callable[[list[str], bytes, float], "CommandResult"]


@dataclass(frozen=True)
class VendorDetectorConfig:
    service: str
    module: str
    tool_name: str
    proxy_log_path: str
    extra_pkill_pattern: Optional[str]


# toy_agent never imports detector_adapter (Gap 9) — these strings are
# duplicated by name from each vendor package's own TOOL_NAME/module layout,
# never imported (same pattern already in use between vendor_proxy.py's
# TIER_TO_ENV_VAR and provenance.py's TIER_ENV_VARS). proxy_log_path: aidr
# keeps its legacy /var/log/vendor_proxy.jsonl (predates the
# /var/log/<vendor>_proxy.jsonl convention, Task 8, which applies only to
# vendors added after it). extra_pkill_pattern: aidr's Inspector spawns MCP
# provider subprocesses (Plan 4) that need a second, vendor-internal cleanup
# target; llamafirewall spawns none.
VENDOR_DETECTOR_CONFIG: dict[str, VendorDetectorConfig] = {
    "aidr": VendorDetectorConfig(
        service="detector",
        module="detector_adapter.vendors.aidr.evaluate_case",
        tool_name="aidr",
        proxy_log_path="/var/log/vendor_proxy.jsonl",
        extra_pkill_pattern="aidr/providers",
    ),
    "llamafirewall": VendorDetectorConfig(
        service="detector-llamafirewall",
        module="detector_adapter.vendors.llamafirewall.evaluate_case",
        tool_name="llamafirewall-alignmentcheck",
        proxy_log_path="/var/log/llamafirewall_proxy.jsonl",
        extra_pkill_pattern=None,
    ),
}


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


def _error_verdict(case_id: str, error_kind: str, detail: str, tool_name: str) -> dict:
    return {
        "case_id": case_id,
        "tool_name": tool_name,
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
    vendor: str,
    agent_timeout_s: float = 120.0,
    detector_timeout_s: float = 180.0,
    run_command: CommandRunner = default_command_runner,
) -> dict:
    """Drive one TestCase through agent -> detector (design doc, 'Meccanismo di
    handoff'). Never imports aidr/llamafirewall/detector_adapter — the JSON
    contract on stdin/stdout is the only thing this function knows about
    either side. `vendor` is required (principio 8, SPIRIT.md): every caller
    must be explicit, never rely on an implicit default.

    Returns {"transcript": <Transcript JSON dict or None>, "verdict": <Verdict
    JSON dict>} — transcript is None only when the agent invocation itself
    failed before producing one (council-skeptic finding, Gap 9 targeted
    council: Plan 4 needs the transcript for the report's "Casi concreti"
    section — an earlier draft of this plan discarded it here, which would
    have forced Plan 4 to change this function's signature anyway)."""
    config = VENDOR_DETECTOR_CONFIG[vendor]
    case_id = test_case["case_id"]

    agent_cmd = ["docker", "compose", "exec", "-T", "agent", "python", "-m", "toy_agent.run_case"]
    agent_input = json.dumps(test_case).encode("utf-8")
    agent_result = run_command(agent_cmd, agent_input, agent_timeout_s)

    if agent_result.failed_to_start:
        return {"transcript": None, "verdict": _error_verdict(case_id, "infra", "docker compose exec failed to start the agent invocation", config.tool_name)}
    if agent_result.timed_out:
        return {"transcript": None, "verdict": _error_verdict(case_id, "infra", f"agent invocation exceeded {agent_timeout_s}s wall-clock timeout", config.tool_name)}
    if agent_result.returncode != 0:
        return {"transcript": None, "verdict": _error_verdict(case_id, "application", agent_result.stderr.decode("utf-8", errors="replace"), config.tool_name)}

    transcript_bytes = agent_result.stdout
    try:
        transcript_dict = json.loads(transcript_bytes)
    except json.JSONDecodeError:
        return {"transcript": None, "verdict": _error_verdict(case_id, "application", "agent produced invalid JSON on stdout despite exit code 0", config.tool_name)}

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
        ["docker", "compose", "exec", "-T", config.service, "sh", "-c", f"echo {shlex.quote(marker)} >> {config.proxy_log_path}"],
        b"",
        10.0,
    )

    detector_cmd = ["docker", "compose", "exec", "-T", config.service, "python", "-m", config.module]
    detector_result = run_command(detector_cmd, transcript_bytes, detector_timeout_s)

    def _cleanup() -> None:
        # Last-resort fallback only (council-skeptic finding, Gap 9 targeted
        # council): evaluate_case.py enforces its own internal wall-clock
        # deadline and terminates its own subprocesses (aidr's MCP providers)
        # before exiting — this external cleanup only matters if that
        # internal mechanism somehow didn't fire (e.g. a bug, or signal
        # delivery delayed inside a C extension that doesn't check for
        # interrupts). Two patterns for aidr, not one (config.extra_pkill_pattern):
        # the evaluate_case process itself (if the internal deadline never
        # fired, it's still the parent holding everything up — a single
        # external pkill targeting only the vendor-internal pattern would
        # never touch that parent) and its MCP provider children (in case the
        # parent died but a child survived it, since killing a parent does
        # not cascade-kill children on Linux). llamafirewall spawns no
        # internal subprocesses, so its config carries no second pattern —
        # one pkill is the whole cleanup. Both best-effort, non-fatal — a
        # risk of degradation for the rest of the sequential batch, not of
        # total blockage, per the design doc.
        run_command(["docker", "compose", "exec", "-T", config.service, "pkill", "-f", config.module], b"", 10.0)
        if config.extra_pkill_pattern is not None:
            run_command(["docker", "compose", "exec", "-T", config.service, "pkill", "-f", config.extra_pkill_pattern], b"", 10.0)

    if detector_result.failed_to_start:
        return {"transcript": transcript_dict, "verdict": _error_verdict(case_id, "infra", "docker compose exec failed to start the detector invocation", config.tool_name)}
    if detector_result.timed_out:
        _cleanup()
        return {"transcript": transcript_dict, "verdict": _error_verdict(case_id, "infra", f"detector invocation exceeded {detector_timeout_s}s wall-clock timeout", config.tool_name)}
    if detector_result.returncode != 0:
        # A clean nonzero exit (not timed_out) can still mean evaluate_case.py's
        # own internal deadline fired *during* the detector adapter's
        # construction — before evaluate_case.py has a handle to call its own
        # cleanup on (final-review finding, aidr: Pipeline()/Inspector's
        # blocking per-provider MCP handshake happens inside that
        # constructor, so a hang there raises TimeoutError with the adapter
        # still None). evaluate_case.py exits 1 either way and prints
        # "evaluate_case failed: TimeoutError" to stderr — that message is
        # the only signal available here that its self-cleanup couldn't run.
        # Same fallback cleanup as the timed_out branch above, for the same
        # reason: a still-running evaluate_case parent (unlikely on this
        # path, but harmless if it's already gone) and/or orphaned children
        # left behind by the unfinished construction.
        if b"TimeoutError" in detector_result.stderr:
            _cleanup()
        return {"transcript": transcript_dict, "verdict": _error_verdict(case_id, "application", detector_result.stderr.decode("utf-8", errors="replace"), config.tool_name)}

    try:
        verdict_dict = json.loads(detector_result.stdout)
    except json.JSONDecodeError:
        return {"transcript": transcript_dict, "verdict": _error_verdict(case_id, "application", "detector produced invalid JSON on stdout despite exit code 0", config.tool_name)}

    # Never trust the detector's echoed case_id (Gap 14, A1) — session_id sent
    # to it is now an opaque per-invocation UUID, not case_id, so whatever it
    # echoes back is not ground truth. The orchestrator already knows the real
    # case_id independently, same as every error branch above.
    verdict_dict["case_id"] = case_id
    return {"transcript": transcript_dict, "verdict": verdict_dict}
