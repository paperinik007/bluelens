from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

CommandRunner = Callable[[list[str]], bytes]


def default_command_runner(cmd: list[str]) -> bytes:
    proc = subprocess.run(cmd, capture_output=True)
    return proc.stdout + proc.stderr


def _container_id(service: str, run_command: CommandRunner) -> str:
    output = run_command(["docker", "compose", "ps", "-q", service])
    return output.decode("utf-8").strip().splitlines()[0]


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
    run_command: CommandRunner = default_command_runner,
) -> Path:
    """Retrieve the thin proxy's request/response log from inside `detector`
    (already scrubbed at write time, Task 1 — this is defense in depth, not
    the only scrub point) and persist it under this case_id's evidence dir.
    Vendor-specific (not one of the four generic channels above) — design
    doc, 'Contratto riusabile del container detector'."""
    case_dir = evidence_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    raw = run_command(["docker", "compose", "exec", "-T", "detector", "cat", "/var/log/vendor_proxy.jsonl"])
    scrubbed = raw.replace(api_key.encode("utf-8"), b"[REDACTED]") if api_key else raw
    path = case_dir / "detector.vendor_proxy.jsonl"
    path.write_bytes(scrubbed)
    return path
