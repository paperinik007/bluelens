"""Blocking coverage gate (design doc Plan 5, mapping Requisito -> Verifica):
the set of technique_target values on malicious TestCase entries in dataset/
must cover every T-code in the vendor taxonomy except the two declared as
out of scope this round (Gap 17) — never a silent `== 14`.

Static and pytest-collectible, unlike the tool->label shortcut check
(run_batch.py::main(), Task 2 of this plan): every malicious TestCase
declares technique_target up front, at authoring time — no live execution
needed to know what this test should check.
"""

from pathlib import Path

import yaml

from toy_agent.dataset import load_dataset

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = REPO_ROOT / "dataset"
TAXONOMY_PATH = REPO_ROOT / "catalog" / "vendor_taxonomy_snapshot.yaml"

# Gap 17 (docs/design/2026-08-14-toy-agent-gap-tracking.md): no scenario for
# these two was found that doesn't risk contaminating benign cases sharing
# the same tool. Declared limitation, not a silent gap — remove an entry
# here only after Gap 17 is actually resolved in the gap-tracking doc.
DECLARED_UNCOVERED_TECHNIQUES = {"T0009", "T0011"}


def _all_vendor_techniques() -> set[str]:
    data = yaml.safe_load(TAXONOMY_PATH.read_text(encoding="utf-8"))
    return set(data["techniques"].keys())


def test_every_non_excluded_technique_has_a_malicious_test_case():
    required = _all_vendor_techniques() - DECLARED_UNCOVERED_TECHNIQUES
    cases = load_dataset(DATASET_DIR)
    covered = {c.technique_target for c in cases if c.label == "malicious"}
    missing = required - covered
    assert not missing, (
        f"no malicious TestCase in dataset/ declares technique_target for: "
        f"{sorted(missing)} — every technique except {sorted(DECLARED_UNCOVERED_TECHNIQUES)} "
        f"(Gap 17) must be covered before run_batch.py runs on the full dataset"
    )
