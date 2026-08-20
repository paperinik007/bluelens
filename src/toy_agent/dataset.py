from __future__ import annotations

import re
from pathlib import Path

import yaml

from . import criteria
from .schema import TestCase, validate_unique_case_ids
from .serialization import transcript_from_dict

# Plan 5 (dataset construction) inherits this constant — every case_id written
# to a dataset YAML file must match it (design doc decision 12).
CASE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

# Fields every dataset entry must declare (Finding 3, final review) — mirrors
# run_case.py::_extract_scenario()'s own preconditions on the seed turn so the
# two validations can't silently drift apart over time.
_REQUIRED_FIELDS = ("label", "rationale", "transcript")


def _entry_to_test_case(data: dict, source: Path) -> TestCase:
    if not isinstance(data, dict):
        raise ValueError(f"{source}: dataset entry must be a YAML mapping, got {type(data).__name__}")

    case_id = data.get("case_id")
    if not isinstance(case_id, str) or not CASE_ID_PATTERN.match(case_id):
        raise ValueError(
            f"{source}: case_id {case_id!r} does not match the allowed pattern {CASE_ID_PATTERN.pattern!r}"
        )

    for field_name in _REQUIRED_FIELDS:
        if field_name not in data:
            raise ValueError(f"{source}: missing required field {field_name!r}")

    transcript = transcript_from_dict(data["transcript"])
    if len(transcript.turns) != 1:
        raise ValueError(
            f"{source}: transcript.turns must contain exactly one seed turn, got {len(transcript.turns)}"
        )
    seed = transcript.turns[0]
    if seed.role != "user" or not isinstance(seed.content, str) or not seed.content:
        raise ValueError(f"{source}: the seed turn must have role 'user' and non-empty string content")

    attack_success_criteria_raw = data.get("attack_success_criteria")
    attack_success_criteria = None
    if attack_success_criteria_raw is not None:
        try:
            attack_success_criteria = criteria.criterion_from_dict(attack_success_criteria_raw)
            criteria.validate_criterion(attack_success_criteria)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{source}: invalid attack_success_criteria: {exc}") from exc

    return TestCase(
        case_id=case_id,
        label=data["label"],
        technique_target=data.get("technique_target"),
        rationale=data["rationale"],
        transcript=transcript,
        attack_success_criteria=attack_success_criteria,
    )


def load_dataset(dataset_dir: Path) -> list[TestCase]:
    """Load every *.yaml TestCase entry under dataset_dir (design doc decision 1).

    Never writes to dataset_dir (decision 10). Each case_id is validated
    against CASE_ID_PATTERN before it is used for anything else, including
    before this function returns — no caller ever sees an unvalidated
    case_id (decision 12)."""
    cases: list[TestCase] = []
    for path in sorted(dataset_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        cases.append(_entry_to_test_case(data, path))
    validate_unique_case_ids(cases)
    return cases
