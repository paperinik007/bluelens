from __future__ import annotations

import re
from pathlib import Path

import yaml

from .schema import TestCase, validate_unique_case_ids
from .serialization import transcript_from_dict

# Plan 5 (dataset construction) inherits this constant — every case_id written
# to a dataset YAML file must match it (design doc decision 12).
CASE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _entry_to_test_case(data: dict, source: Path) -> TestCase:
    case_id = data.get("case_id")
    if not isinstance(case_id, str) or not CASE_ID_PATTERN.match(case_id):
        raise ValueError(
            f"{source}: case_id {case_id!r} does not match the allowed pattern {CASE_ID_PATTERN.pattern!r}"
        )
    return TestCase(
        case_id=case_id,
        label=data["label"],
        technique_target=data.get("technique_target"),
        rationale=data["rationale"],
        transcript=transcript_from_dict(data["transcript"]),
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
