from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Callable, Optional

CommandRunner = Callable[[list[str]], bytes]


def default_command_runner(cmd: list[str]) -> bytes:
    proc = subprocess.run(cmd, capture_output=True)
    return proc.stdout + proc.stderr


def _container_id(service: str, run_command: CommandRunner) -> Optional[str]:
    output = run_command(["docker", "compose", "ps", "-q", service])
    lines = output.decode("utf-8", errors="replace").strip().splitlines()
    return lines[0] if lines else None


def collect_case_evidence(
    case_id: str,
    services: tuple[str, str],
    evidence_dir: Path,
    *,
    run_command: CommandRunner = default_command_runner,
) -> dict[str, Path]:
    """Snapshot the four generic external-evidence channels for both
    containers immediately after invoking `services` for `case_id` (design
    doc, 'Raccolta prove esterna' — extended to both agent and detector,
    attributed per-case_id, council-mirato finding 2026-08-16)."""
    case_dir = evidence_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    for service in (*services, "egress-proxy"):
        path = case_dir / f"{service}.logs.txt"
        path.write_bytes(run_command(["docker", "compose", "logs", "--no-color", service]))
        written[f"{service}.logs"] = path

    for service in services:
        container_id = _container_id(service, run_command)
        if container_id is None:
            # Service unreachable (e.g. Docker daemon instability) — degrade
            # this one case's evidence for this one channel, never crash the
            # batch (design doc, mapping Requisito -> Verifica).
            continue

        diff_path = case_dir / f"{service}.diff.txt"
        diff_path.write_bytes(run_command(["docker", "diff", container_id]))
        written[f"{service}.diff"] = diff_path

        stats_path = case_dir / f"{service}.stats.txt"
        stats_path.write_bytes(run_command(["docker", "stats", "--no-stream", container_id]))
        written[f"{service}.stats"] = stats_path

    return written


def collect_thin_proxy_log(
    case_id: str,
    evidence_dir: Path,
    api_key: str,
    *,
    service: str,
    log_path: str,
    output_suffix: str = "vendor_proxy.jsonl",
    run_command: CommandRunner = default_command_runner,
) -> Path:
    """Retrieve the thin proxy's request/response log from inside `service`
    (already scrubbed at write time — this is defense in depth, not the
    only scrub point) and persist it under this case_id's evidence dir.
    `service`/`log_path` are resolved by the caller from the active vendor
    (sequence.py, via orchestrator.VENDOR_DETECTOR_CONFIG) — this function
    has no vendor knowledge of its own (design doc, 'Contratto riusabile
    del container detector', generalizzato oltre aidr in Fase 2).

    output_suffix (PromptGuard design doc, 2026-09-01): distinguishes a
    second call for the same case_id/service from the first — without it,
    two calls for the same service would both write to
    '<service>.vendor_proxy.jsonl', the second silently overwriting the
    first. Default preserves every caller that predates this parameter."""
    case_dir = evidence_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    raw = run_command(["docker", "compose", "exec", "-T", service, "cat", log_path])
    scrubbed = raw.replace(api_key.encode("utf-8"), b"[REDACTED]") if api_key else raw
    path = case_dir / f"{service}.{output_suffix}"
    path.write_bytes(scrubbed)
    return path


def sum_proxy_log_cost(log_bytes: bytes) -> float:
    """Sum every response.usage.cost found in a thin-proxy log (JSON lines,
    vendor_proxy.py's/openrouter_proxy.py's own format) — the only place a
    real per-call OpenRouter cost is observable (design doc, 'Tetto di
    spesa'). A line without a numeric cost contributes 0.0; a malformed
    line (partial write mid-request) is skipped, never raises — this reads
    forensic data that must not be able to crash the batch it's protecting."""
    total = 0.0
    for line in log_bytes.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        cost = entry.get("response", {}).get("usage", {}).get("cost")
        if isinstance(cost, (int, float)):
            total += float(cost)
    return total
