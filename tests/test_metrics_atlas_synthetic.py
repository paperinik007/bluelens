"""Verify metrics.py excludes strict_significant: False both from per_tech_strict
breakdown AND from the aggregated strict counters (Atlas 6-gap spec Scope IN
voce 6 + ADR-0002 + C16)."""

from pathlib import Path

import pytest

from toy_agent.metrics import compute_metrics
from toy_agent.schema import Always, TestCase, Transcript, Turn, Verdict

DATASET_PATH = Path(__file__).resolve().parent.parent / "dataset"


def _mk_case(case_id: str, technique_target: str, strict_significant: bool = True) -> TestCase:
    """Build a TestCase whose ground truth is KNOWN (attack_succeeded=True) AND
    whose transcript is not flagged as unusable (otherwise Gap 18 / D-I routes
    the case to ground_truth_unknown_count or transcript_unusable_count before
    any strict counter is touched, defeating the test's purpose)."""
    transcript = Transcript(
        session_id=case_id,
        turns=[Turn(seq=0, role="user", content="seed")],
        stop_reason="completed",
    )
    return TestCase(
        case_id=case_id,
        label="malicious",
        technique_target=technique_target,
        rationale=f"metrics smoke test for {case_id}",
        strict_significant=strict_significant,
        attack_success_criteria=Always(),
        attack_succeeded=True,
        transcript=transcript,
    )


def _mk_verdict(case_id: str, technique_detected: str = "T0001", label: str = "malicious") -> Verdict:
    return Verdict(
        case_id=case_id,
        tool_name="aidr",
        status="ok",
        label=label,
        technique_detected=technique_detected,
    )


def test_synthetic_target_excluded_from_per_tech_strict():
    """Caso con technique_target=T-ATLAS-... e strict_significant=False:
    NON entra in per_tech_strict (per costruzione sarebbe FN garantito),
    entra in per_tech_primary."""
    case = _mk_case("smoke_synth", "T-ATLAS-atlas-t0077-rendering", strict_significant=False)
    verdict = _mk_verdict("smoke_synth", technique_detected="T0001")  # mismatch by construction
    metrics = compute_metrics([case], [verdict])
    assert "T-ATLAS-atlas-t0077-rendering" not in metrics.per_technique, (
        "synthetic target must NOT appear in per_tech_strict"
    )
    assert "T-ATLAS-atlas-t0077-rendering" in metrics.per_technique_primary, (
        "synthetic target must appear in per_tech_primary"
    )


def test_real_target_still_appears_in_per_tech_strict():
    """Regression guard: casi reali (strict_significant=True default) restano in per_tech_strict."""
    case = _mk_case("smoke_real", "T0001")
    verdict = _mk_verdict("smoke_real", technique_detected="T0001")
    metrics = compute_metrics([case], [verdict])
    assert "T0001" in metrics.per_technique


def test_synthetic_target_excluded_from_aggregated_strict_counters():
    """C16: un caso strict_significant=False malicious correttamente rilevato da
    aidr (predicted_malicious=True) NON deve entrare nei contatori aggregati
    strict s_tp/s_fn/s_fp/s_tn — anche se il technique_detected non matcha
    (mismatch per costruzione), non può essere contato come FN nel numero
    aggregato pubblicato in testa al report."""
    case = _mk_case("smoke_c16", "T-ATLAS-atlas-t0077-rendering", strict_significant=False)
    verdict = _mk_verdict("smoke_c16", technique_detected="T0001")  # mismatch by construction
    metrics = compute_metrics([case], [verdict])
    assert metrics.strict.tp == 0
    assert metrics.strict.fn == 0
    assert metrics.strict.fp == 0
    assert metrics.strict.tn == 0
    assert metrics.strict.recall is None, (
        "strict recall must be None (zero denominator) when only strict_significant=False cases run, "
        "NOT a 0.0 from one FN"
    )


def test_primary_metric_still_counts_synthetic_target():
    """Regression guard: la metrica primary NON esclude i casi synthetic —
    è l'unica metrica comune a tutti i vendor (vedi design v4, già applicato
    a LlamaFirewall). C16 esclude solo i contatori strict."""
    case = _mk_case("smoke_primary", "T-ATLAS-atlas-t0077-rendering", strict_significant=False)
    verdict = _mk_verdict("smoke_primary", technique_detected="T0001")
    metrics = compute_metrics([case], [verdict])
    assert metrics.primary.tp == 1, f"primary TP atteso 1, got {metrics.primary.tp}"


def test_report_shows_na_row_for_synthetic_tech():
    """C14: un tech presente in per_technique_primary ma assente in
    per_technique (target synthetic, strict_significant=False) produce una
    riga n/a nel breakdown strict, non un'omissione silenziosa."""
    case = _mk_case("smoke_synth_field", "T-ATLAS-atlas-t0077-rendering", strict_significant=False)
    verdict = _mk_verdict("smoke_synth_field")
    metrics = compute_metrics([case], [verdict])
    assert "T-ATLAS-atlas-t0077-rendering" in metrics.per_technique_primary
    assert "T-ATLAS-atlas-t0077-rendering" not in metrics.per_technique


# Atlas 6-gap Task 1 R1: removed @pytest.mark.xfail (was xfail(strict=False)).
# Era rumoroso (XPASS) dopo che Task 1 ha popolato i TestCase mirror per
# atlas-t0077-rendering (atlas_t0077_markdown_link_payload, atlas_t0077_html_payload)
# — vedi commit 0df7aaf. Il test passa naturalmente senza marker.
def test_atlas_testcase_mirror_consistency():
    """C13: ogni TestCase mirror in dataset/ per un cluster atlas ha
    strict_significant: False + technique_target inizia con 'T-ATLAS-'
    + technique_target uguale a 'T-ATLAS-{catalog_entry.variant_cluster_id}'
    per la corrispondente entry in cases.yaml."""
    from toy_agent.dataset import load_dataset
    cases = [c for c in load_dataset(DATASET_PATH) if c.technique_target and c.technique_target.startswith("T-ATLAS-")]
    assert cases, "no atlas synthetic TestCase found"
    offenders = []
    for case in cases:
        if case.strict_significant is not False:
            offenders.append(f"{case.case_id}: strict_significant must be False, got {case.strict_significant!r}")
    assert not offenders, f"atlas TestCases with wrong strict_significant: {offenders}"
