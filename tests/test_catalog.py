"""Structural checks for catalog/cases.yaml (Plan 5 dataset design).

Not a check against src/toy_agent: the catalog is candidate content, never read
by load_dataset() (design doc, "Catalogo"). These checks exist so the catalog
stays internally consistent as it grows, without relying on a human re-running
an ad-hoc script every time a new entry is added.
"""

import re
from pathlib import Path

import pytest
import yaml

from toy_agent.dataset import _entry_to_test_case, load_dataset

CATALOG_PATH = Path(__file__).resolve().parent.parent / "catalog" / "cases.yaml"
TAXONOMY_SNAPSHOT_PATH = (
    Path(__file__).resolve().parent.parent / "catalog" / "vendor_taxonomy_snapshot.yaml"
)
DATASET_PATH = Path(__file__).resolve().parent.parent / "dataset"

REQUIRED_FIELDS = {
    "catalog_id", "technique_code", "technique_name", "label_hint",
    "source_type", "summary", "citation", "adaptation", "status", "selected_as",
}

_URL_RE = re.compile(r"https?://\S+")


def _load_entries() -> list[dict]:
    data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    return data["entries"]


def _load_vendor_techniques() -> dict[str, str]:
    """Loaded from catalog/vendor_taxonomy_snapshot.yaml, not hardcoded here.

    Keeping this out of the test's own source means a pin bump or a
    different vendor (Fase 2) is a data-file edit, not a change to this
    test's logic (design doc, "Catalogo" — principio 8 SPIRIT.md: nessuna
    verità del vendor cablata come se fosse universale)."""
    data = yaml.safe_load(TAXONOMY_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    return data["techniques"]


def test_every_entry_has_all_required_fields():
    missing_by_entry = {
        e.get("catalog_id", "<unknown>"): REQUIRED_FIELDS - set(e.keys())
        for e in _load_entries()
    }
    offending = {k: v for k, v in missing_by_entry.items() if v}
    assert not offending, f"entries missing required fields: {offending}"


def test_catalog_ids_are_unique():
    ids = [e["catalog_id"] for e in _load_entries()]
    duplicates = {i for i in ids if ids.count(i) > 1}
    assert not duplicates, f"duplicate catalog_id values: {duplicates}"


@pytest.mark.parametrize("entry_index", range(len(_load_entries())))
def test_technique_name_matches_vendor_taxonomy(entry_index):
    vendor_techniques = _load_vendor_techniques()
    entry = _load_entries()[entry_index]
    code = entry["technique_code"]
    if code is None:
        assert entry["technique_name"] is None, (
            f"{entry['catalog_id']}: technique_code is null but technique_name is set"
        )
        return
    assert code in vendor_techniques, (
        f"{entry['catalog_id']}: technique_code {code!r} is not in the vendor "
        f"taxonomy snapshot ({TAXONOMY_SNAPSHOT_PATH.name})"
    )
    assert entry["technique_name"] == vendor_techniques[code], (
        f"{entry['catalog_id']}: technique_name {entry['technique_name']!r} "
        f"does not match the snapshot's name {vendor_techniques[code]!r} for {code}"
    )


_EXTERNAL_SOURCE_TYPES = ("real_incident", "benchmark_inspired")


def test_external_source_entries_declare_citation_and_adaptation():
    """Both source types with a real external provenance — an incident report
    or an independent academic benchmark — must declare it (design doc,
    "Fonti dei casi": benchmark_inspired is a per-entry adaptation, same
    accountability standard as real_incident, not merely an abstract
    taxonomy cross-check — corrected 2026-08-19, grill-with-docs)."""
    offending = [
        e["catalog_id"] for e in _load_entries()
        if e["source_type"] in _EXTERNAL_SOURCE_TYPES
        and (not e.get("citation", "").strip() or not e.get("adaptation", "").strip())
    ]
    assert not offending, f"real_incident/benchmark_inspired entries missing citation/adaptation: {offending}"


def test_citation_and_adaptation_are_null_for_invented_entries():
    """citation/adaptation are keys required on every entry (REQUIRED_FIELDS),
    but only the two externally-sourced types (real_incident,
    benchmark_inspired) give them content — invented entries (no external
    provenance to declare) must declare an explicit null, never an empty
    string, so "not applicable by construction" stays distinguishable from
    "forgotten during authoring" (design doc, "Campi", corrected
    2026-08-19)."""
    offending = [
        e["catalog_id"] for e in _load_entries()
        if e["source_type"] not in _EXTERNAL_SOURCE_TYPES
        and (e["citation"] is not None or e["adaptation"] is not None)
    ]
    assert not offending, (
        f"invented entries with citation/adaptation not null: {offending}"
    )


def test_external_source_citations_contain_a_url():
    offending = [
        e["catalog_id"] for e in _load_entries()
        if e["source_type"] in _EXTERNAL_SOURCE_TYPES and not _URL_RE.search(e["citation"])
    ]
    assert not offending, f"real_incident entries with no URL in citation: {offending}"


def test_status_and_selected_as_are_consistent():
    offending = [
        e["catalog_id"] for e in _load_entries()
        if (e["status"] == "candidate") != (e["selected_as"] is None)
    ]
    assert not offending, (
        f"status/selected_as mismatch (candidate must have selected_as=null, "
        f"selected must have it set): {offending}"
    )


def test_label_hint_is_a_known_value():
    offending = [
        e["catalog_id"] for e in _load_entries()
        if e["label_hint"] not in ("malicious", "benign")
    ]
    assert not offending, f"entries with an invalid label_hint: {offending}"


def test_selected_catalog_entries_match_their_dataset_test_case():
    """Non-blocking (design doc, mapping Requisito -> Verifica): every catalog
    entry with status: selected must still agree with the real TestCase it
    produced — no silent drift between catalog/cases.yaml and dataset/."""
    selected = [e for e in _load_entries() if e["status"] == "selected"]
    if not selected:
        return  # nothing selected yet — vacuously fine, not a false pass on real drift
    cases_by_id = {c.case_id: c for c in load_dataset(DATASET_PATH)}
    offending = []
    for entry in selected:
        case = cases_by_id.get(entry["selected_as"])
        if case is None:
            offending.append(f"{entry['catalog_id']}: selected_as {entry['selected_as']!r} not found in dataset/")
            continue
        if entry["label_hint"] == "malicious" and case.technique_target != entry["technique_code"]:
            offending.append(
                f"{entry['catalog_id']}: dataset technique_target {case.technique_target!r} "
                f"!= catalog technique_code {entry['technique_code']!r}"
            )
        if entry["catalog_id"] not in case.rationale:
            offending.append(f"{entry['catalog_id']}: dataset case {case.case_id!r} rationale does not mention the catalog_id")
    assert not offending, f"catalog/dataset drift: {offending}"


def _filled_template_example(label: str, technique_target: str | None) -> dict:
    """A realistic filled-in copy of catalog/_template.yaml's field set —
    not a parse of the template file itself (its placeholder values, e.g.
    <mechanic_descriptive_slug>, would never pass CASE_ID_PATTERN). Closes
    the open item in registro-limiti-aperti.md: the design doc's claim that
    the template compiles into a valid TestCase was verified by hand,
    leaving no trace in the repo — this test makes it a re-runnable fact."""
    case_id = "template_validation_" + label + "_example"
    data = {
        "case_id": case_id,
        "label": label,
        "technique_target": technique_target,
        "rationale": (
            "Template validation example, not part of the real dataset — see "
            "docs/design/2026-08-19-plan5-dataset-design.md, sections Naming / "
            "Authoring — template."
        ),
        "transcript": {
            "session_id": case_id,
            "turns": [{"seq": 0, "role": "user", "content": "example seed content", "tool_call": None}],
            "stop_reason": None,
        },
        "attack_success_criteria": None,
    }
    if label == "malicious":
        # Gap 18: template's own attack_success_criteria field, filled with
        # the trivial always-true form — this test validates that the
        # template's FIELD SET compiles, not any specific criterion's logic
        # (that is criteria.py's job, exercised elsewhere).
        data["attack_success_criteria"] = {"always": True}
    return data


def test_template_compiled_with_a_malicious_example_produces_a_valid_test_case():
    data = _filled_template_example("malicious", "T0001")
    case = _entry_to_test_case(data, Path("template_validation_malicious_example.yaml"))
    assert case.label == "malicious"
    assert case.technique_target == "T0001"
    assert case.attack_success_criteria is not None


def test_template_compiled_with_a_benign_example_produces_a_valid_test_case():
    data = _filled_template_example("benign", None)
    case = _entry_to_test_case(data, Path("template_validation_benign_example.yaml"))
    assert case.label == "benign"
    assert case.technique_target is None
    assert case.attack_success_criteria is None


def test_template_validation_actually_catches_a_real_error():
    """Negative check (design doc self-review discipline): a validation test
    that never fails on bad input is vacuous. A benign entry declaring a
    technique_target is exactly the mistake TestCase.__post_init__ already
    rejects (schema.py) — confirm _entry_to_test_case surfaces it, not just
    that valid input passes."""
    data = _filled_template_example("benign", "T0001")
    with pytest.raises(ValueError, match="benign TestCase must not declare a technique_target"):
        _entry_to_test_case(data, Path("bad_example.yaml"))


def test_template_validation_catches_a_malicious_example_missing_attack_success_criteria():
    """Second negative check, specific to Gap 18: the mistake TestCase.__post_init__
    added on top of the pre-existing technique_target rule — a malicious entry
    with no attack_success_criteria at all (e.g. an author who filled in the
    template before Gap 18 landed, or skipped the field by mistake)."""
    data = _filled_template_example("malicious", "T0001")
    del data["attack_success_criteria"]
    with pytest.raises(ValueError, match="malicious TestCase must declare attack_success_criteria"):
        _entry_to_test_case(data, Path("bad_example.yaml"))
