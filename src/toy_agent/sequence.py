from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .orchestrator import CommandRunner, default_command_runner

# Only agent/detector are part of the sequence vocabulary — egress-proxy is
# shared infrastructure, never managed by a sequence (design doc, "Meccanica
# Docker per open/close").
KNOWN_CONTAINERS = ("agent", "detector")


@dataclass(frozen=True)
class OpenStep:
    containers: tuple[str, ...]


@dataclass(frozen=True)
class CommandStep:
    case_id: str
    counts_toward_metric: bool


@dataclass(frozen=True)
class CloseStep:
    containers: tuple[str, ...]


SequenceStep = Union[OpenStep, CommandStep, CloseStep]

OPEN_CLOSE_TIMEOUT_S = 30.0


def _open_container(service: str, run_command: CommandRunner) -> None:
    """Auto-healing open (design doc, 'Meccanica Docker per open/close';
    council-risk finding, crash dell'orchestratore a metà sequenza): the
    best-effort rm before up recovers from any residual state regardless of
    what happened before it — a crashed prior run included, not only the
    path where everything went cleanly."""
    run_command(["docker", "compose", "rm", "-f", "-s", "-v", service], b"", OPEN_CLOSE_TIMEOUT_S)
    run_command(["docker", "compose", "up", "-d", service], b"", OPEN_CLOSE_TIMEOUT_S)


def _close_container(service: str, run_command: CommandRunner) -> None:
    """Real removal, never a bare stop (design doc, 'Meccanica Docker per
    open/close'): rm -f -s -v deletes the container's writable layer by
    Docker's own command contract — that contract is the guarantee, not an
    empirical check of what's left on disk.

    The CommandResult's returncode is not checked here — same best-effort
    discipline orchestrator.py already applies to its own cleanup calls
    (the pkill fallbacks). A failed rm/up is not silently hidden forever: a
    container that's still broken will make the next docker compose exec in
    the sequence fail too, which run_test_case classifies as an infra error
    and the circuit breaker will trip on within a bounded number of
    commands (council-risk finding, this plan's checkpoint)."""
    run_command(["docker", "compose", "rm", "-f", "-s", "-v", service], b"", OPEN_CLOSE_TIMEOUT_S)


def validate_sequence(steps: list[SequenceStep], known_case_ids: set[str]) -> None:
    """Fail-fast static validation (design doc, 'Validazione statica') — a
    scan over `steps` tracking which containers are open, before any Docker
    or LLM call is issued. Mirrors CASE_ID_PATTERN/validate_unique_case_ids
    in dataset.py: cheap, structural checks first, never a wasted real call
    on a malformed sequence."""
    open_containers: set[str] = set()
    for step in steps:
        if isinstance(step, OpenStep):
            already_open = open_containers & set(step.containers)
            if already_open:
                raise ValueError(f"open step re-opens already-open containers: {sorted(already_open)}")
            open_containers |= set(step.containers)
        elif isinstance(step, CommandStep):
            missing = set(KNOWN_CONTAINERS) - open_containers
            if missing:
                raise ValueError(
                    f"command step {step.case_id!r} requires containers not open: {sorted(missing)}"
                )
            if step.case_id not in known_case_ids:
                raise ValueError(f"command step references unknown case_id: {step.case_id!r}")
        elif isinstance(step, CloseStep):
            not_open = set(step.containers) - open_containers
            if not_open:
                raise ValueError(f"close step closes containers not open: {sorted(not_open)}")
            open_containers -= set(step.containers)
        else:
            raise TypeError(f"unknown sequence step type: {type(step).__name__}")
    if open_containers:
        raise ValueError(f"sequence ends with containers still open: {sorted(open_containers)}")
