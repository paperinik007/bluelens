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

CATALOG_PATH = Path(__file__).resolve().parent.parent / "catalog" / "cases.yaml"
TAXONOMY_SNAPSHOT_PATH = (
    Path(__file__).resolve().parent.parent / "catalog" / "vendor_taxonomy_snapshot.yaml"
)

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
