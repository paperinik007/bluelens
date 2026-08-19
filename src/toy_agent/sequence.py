from __future__ import annotations

from dataclasses import dataclass
from typing import Union

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
