"""Structural checks for catalog/vendor_scope_verification.yaml (Atlas 6-gap batch,
spec C4-C8). Mirror di tests/test_catalog.py::test_every_entry_has_all_required_fields
— esercita il path reale (no test che passa senza leggere il file, lezione
docs/notes/pi-lesson-test-must-exercise-real-path.md)."""

from pathlib import Path

import yaml

VERIFICATION_PATH = (
    Path(__file__).resolve().parent.parent / "catalog" / "vendor_scope_verification.yaml"
)

REQUIRED_FIELDS = {
    "vendor", "technique_code", "declared_scope", "verified_mechanism", "verdict", "evidence",
}
# Fix 2 post-council (2026-08-31): aggiunto "inconclusive" come verdict
# ammissibile — segnala "esecuzione non prodotta" senza dichiarare un
# ambito di copertura che non è stato verificato. Il gate esplicito vieta
# "in_scope" senza almeno variant_round_count verdicts ok contro aidr.
ALLOWED_VERDICTS = {"in_scope", "narrower_than_declared", "out_of_scope", "inconclusive"}


def _load_entries() -> list[dict]:
    data = yaml.safe_load(VERIFICATION_PATH.read_text(encoding="utf-8"))
    return data.get("entries", [])


def test_every_entry_has_all_required_fields():
    entries = _load_entries()
    # Empty list is valid (this file starts empty — entries are appended by
    # Atlas 6-gap Task 4 / narrative sections). The check only fires when
    # there is at least one entry to inspect.
    if not entries:
        return
    missing_by_entry = {
        e.get("vendor", "<unknown>"): REQUIRED_FIELDS - set(e.keys())
        for e in entries
    }
    offenders = {k: v for k, v in missing_by_entry.items() if v}
    assert not offenders, f"entries missing required fields: {offenders}"


def test_verdict_is_an_allowed_value():
    offenders = [
        e["vendor"] for e in _load_entries()
        if e["verdict"] not in ALLOWED_VERDICTS
    ]
    assert not offenders, f"entries with invalid verdict: {offenders}"


def test_evidence_points_to_an_existing_docs_file():
    """C7: evidence punta a un file docs/**.md esistente su disco.
    Niente URL né path assoluti — solo path relativi dalla repo root."""
    offenders = []
    for e in _load_entries():
        path = Path(e["evidence"])
        if not path.exists():
            offenders.append(f"{e['vendor']}: evidence {e['evidence']!r} not found on disk")
    assert not offenders, f"entries with non-existent evidence: {offenders}"


def test_evidence_is_relative_docs_path():
    """C7 rinforzato: evidence è un path relativo dalla repo root (no URL
    esterni, no path assoluti). Garantisce riproducibilità del puntatore
    in un repo clonato ovunque."""
    offenders = [
        e["vendor"] for e in _load_entries()
        if Path(e["evidence"]).is_absolute() or e["evidence"].startswith("http")
    ]
    assert not offenders, f"entries with non-relative evidence path: {offenders}"


def test_technique_code_when_set_references_a_known_vendor_technique():
    """C8: technique_code non-null referenzia un T-code in vendor_taxonomy_snapshot.yaml.
    Per la popolazione iniziale con technique_code: null, il coverage sarà zero
    (limite accettato dal design v4)."""
    snapshot_path = (
        Path(__file__).resolve().parent.parent / "catalog" / "vendor_taxonomy_snapshot.yaml"
    )
    snapshot = yaml.safe_load(snapshot_path.read_text(encoding="utf-8"))
    known = set(snapshot.get("techniques", {}).keys())
    offenders = [
        e["vendor"] for e in _load_entries()
        if e["technique_code"] is not None and e["technique_code"] not in known
    ]
    assert not offenders, f"entries with unknown technique_code: {offenders}"
