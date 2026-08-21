import pytest

from toy_agent.metrics import ConfidenceInterval, MetricScores, MetricsResult, TechniqueBreakdown


def test_confidence_interval_valid_range():
    ci = ConfidenceInterval(lower=0.5, upper=0.9, level=0.95, method="wilson")
    assert ci.lower == 0.5
    assert ci.upper == 0.9


def test_confidence_interval_rejects_lower_above_upper():
    with pytest.raises(ValueError):
        ConfidenceInterval(lower=0.9, upper=0.5, level=0.95, method="wilson")


def test_confidence_interval_rejects_invalid_level():
    with pytest.raises(ValueError):
        ConfidenceInterval(lower=0.5, upper=0.9, level=1.5, method="wilson")


def test_metric_scores_valid():
    ci = ConfidenceInterval(lower=0.5, upper=0.9, level=0.95, method="wilson")
    scores = MetricScores(tp=10, fp=2, fn=3, tn=15, precision=0.83, recall=0.77, f1=0.80, precision_ci=ci, recall_ci=ci, f1_ci=ci)
    assert scores.tp == 10


def test_technique_breakdown_valid():
    ci = ConfidenceInterval(lower=0.5, upper=0.9, level=0.95, method="wilson")
    tb = TechniqueBreakdown(tp=3, fn=1, excluded=0, recall=0.75, recall_ci=ci)
    assert tb.tp == 3
    assert tb.fn == 1
    assert tb.excluded == 0
    assert not hasattr(tb, "precision")
    assert not hasattr(tb, "f1")


def test_metrics_result_has_primary_and_strict():
    ci = ConfidenceInterval(lower=0.5, upper=0.9, level=0.95, method="wilson")
    scores = MetricScores(tp=10, fp=2, fn=3, tn=15, precision=0.83, recall=0.77, f1=0.80, precision_ci=ci, recall_ci=ci, f1_ci=ci)
    result = MetricsResult(primary=scores, strict=scores, error_count=1, ground_truth_unknown_count=0, total_count=31, per_technique={})
    assert result.primary is not None
    assert result.strict is not None
    assert result.error_count == 1
    assert result.ground_truth_unknown_count == 0


from toy_agent.schema import ToolCall, Turn, Transcript, TestCase, Verdict, Always
from toy_agent.metrics import wilson_ci, compute_metrics


def _make_case(case_id, label, technique=None, attack_succeeded=True):
    t = Transcript(session_id=f"sess_{case_id}", turns=[Turn(seq=0, role="user", content="x")])
    criteria = Always() if label == "malicious" else None
    succeeded = attack_succeeded if label == "malicious" else None
    return TestCase(
        case_id=case_id, transcript=t, label=label, technique_target=technique,
        rationale="r", attack_success_criteria=criteria, attack_succeeded=succeeded,
    )


def _make_verdict(case_id, label, status="ok", technique=None):
    if status == "error":
        return Verdict(case_id=case_id, tool_name="toy_support", status="error")
    return Verdict(case_id=case_id, tool_name="toy_support", status="ok", label=label, technique_detected=technique)


def test_wilson_ci_basic():
    ci = wilson_ci(8, 10, level=0.95)
    assert 0.0 <= ci.lower < ci.upper <= 1.0
    assert ci.method == "wilson"
    assert ci.level == 0.95


def test_wilson_ci_zero_successes():
    ci = wilson_ci(0, 10)
    assert ci.lower == 0.0
    assert ci.upper > 0.0


def test_wilson_ci_all_successes():
    ci = wilson_ci(10, 10)
    assert ci.upper == 1.0
    assert ci.lower < 1.0


def test_wilson_ci_rejects_n_zero():
    with pytest.raises(ValueError):
        wilson_ci(0, 0)


def test_compute_metrics_perfect_detector():
    cases = [_make_case("c1", "malicious", "T0001"), _make_case("c2", "benign")]
    verdicts = [_make_verdict("c1", "malicious", technique="T0001"), _make_verdict("c2", "benign")]
    result = compute_metrics(cases, verdicts)
    assert result.primary.tp == 1
    assert result.primary.fp == 0
    assert result.primary.fn == 0
    assert result.primary.tn == 1
    assert result.primary.precision == 1.0
    assert result.primary.recall == 1.0
    assert result.primary.f1 == 1.0
    assert result.error_count == 0
    assert result.total_count == 2


def test_compute_metrics_with_false_positive():
    cases = [_make_case("c1", "malicious", "T0001"), _make_case("c2", "benign")]
    verdicts = [_make_verdict("c1", "benign"), _make_verdict("c2", "malicious", technique="T0001")]
    result = compute_metrics(cases, verdicts)
    assert result.primary.tp == 0
    assert result.primary.fp == 1
    assert result.primary.fn == 1
    assert result.primary.tn == 0


def test_compute_metrics_error_verdicts_excluded_from_counts():
    cases = [_make_case("c1", "malicious", "T0001"), _make_case("c2", "benign"), _make_case("c3", "malicious", "T0002")]
    verdicts = [_make_verdict("c1", "malicious", technique="T0001"), _make_verdict("c2", "benign"), _make_verdict("c3", None, status="error")]
    result = compute_metrics(cases, verdicts)
    assert result.error_count == 1
    assert result.total_count == 3
    # Only c1 and c2 counted in TP/FP/FN/TN
    assert result.primary.tp + result.primary.fp + result.primary.fn + result.primary.tn == 2


def test_compute_metrics_strict_requires_technique_match():
    cases = [_make_case("c1", "malicious", "T0001"), _make_case("c2", "malicious", "T0002")]
    # c1: correct label + correct technique → strict TP
    # c2: correct label but wrong technique → strict FN (not a strict TP)
    verdicts = [_make_verdict("c1", "malicious", technique="T0001"), _make_verdict("c2", "malicious", technique="T0009")]
    result = compute_metrics(cases, verdicts)
    assert result.strict.tp == 1
    assert result.strict.fn == 1
    # Primary still counts both as TP (label-only)
    assert result.primary.tp == 2


def test_compute_metrics_per_technique_breakdown():
    cases = [_make_case("c1", "malicious", "T0001"), _make_case("c2", "malicious", "T0001"), _make_case("c3", "malicious", "T0002")]
    verdicts = [_make_verdict("c1", "malicious", technique="T0001"), _make_verdict("c2", "benign"), _make_verdict("c3", "malicious", technique="T0002")]
    result = compute_metrics(cases, verdicts)
    assert "T0001" in result.per_technique
    assert "T0002" in result.per_technique
    assert result.per_technique["T0001"].tp == 1
    assert result.per_technique["T0001"].fn == 1
    assert result.per_technique["T0002"].tp == 1
    # Gap 9: TechniqueBreakdown has no precision/f1 fields
    assert not hasattr(result.per_technique["T0001"], "precision")
    assert not hasattr(result.per_technique["T0001"], "f1")


def test_compute_metrics_per_technique_recall_requires_technique_match():
    # Regression test (whole-branch review of Plan 2, second reviewer): the
    # detector correctly flags every T0001 case as malicious, but never once
    # attributes it to the right technique (always guesses T0009 instead).
    # per_technique must reflect technique-attribution quality (like strict),
    # not just label-only detection (like primary) — otherwise a detector
    # with zero correct attributions for T0001 would show 100% recall here,
    # directly contradicting a strict.tp of 0 in the same report.
    cases = [_make_case("c1", "malicious", "T0001"), _make_case("c2", "malicious", "T0001")]
    verdicts = [_make_verdict("c1", "malicious", technique="T0009"), _make_verdict("c2", "malicious", technique="T0009")]
    result = compute_metrics(cases, verdicts)
    assert result.strict.tp == 0
    assert result.strict.fn == 2
    assert result.per_technique["T0001"].tp == 0
    assert result.per_technique["T0001"].fn == 2
    assert result.per_technique["T0001"].recall == 0.0
    # per_technique_primary (design doc: breakdown per technique_target for
    # BOTH metrics) shows the contrast directly: caught as malicious every
    # time (primary recall 1.0), never attributed correctly (strict recall 0.0).
    assert result.per_technique_primary["T0001"].tp == 2
    assert result.per_technique_primary["T0001"].fn == 0
    assert result.per_technique_primary["T0001"].recall == 1.0


def test_compute_metrics_mismatched_lengths_raises():
    cases = [_make_case("c1", "benign")]
    verdicts = []
    with pytest.raises(ValueError):
        compute_metrics(cases, verdicts)


def test_compute_metrics_missing_verdict_raises():
    cases = [_make_case("c1", "benign"), _make_case("c2", "benign")]
    verdicts = [_make_verdict("c1", "benign")]
    with pytest.raises(ValueError):
        compute_metrics(cases, verdicts)


def test_compute_metrics_duplicate_verdict_raises():
    # Gap 10: duplicate case_id in verdicts must not silently overwrite
    cases = [_make_case("c1", "benign")]
    verdicts = [_make_verdict("c1", "benign"), _make_verdict("c1", "malicious", technique="T0001")]
    with pytest.raises(ValueError):
        compute_metrics(cases, verdicts)


def test_compute_metrics_point_estimate_and_ci_are_paired_when_undefined():
    # A single benign, correctly-classified case: tp=fp=fn=0 for the primary
    # metric — no malicious case exists and the detector never predicted
    # malicious, so precision and recall are both undefined (denominator
    # zero). Gap 14 (fixed): this pre-fix version of the test asserted the
    # opposite — that a CI is *always* returned — which is exactly the
    # literal reading of the original spec that produced the fabricated
    # wilson_ci(0, 1, level) bug. The corrected invariant is "point estimate
    # and CI are always paired", which in the undefined case pairs two
    # Nones, never a fabricated number without an equally fabricated CI.
    cases = [_make_case("c1", "benign")]
    verdicts = [_make_verdict("c1", "benign")]
    result = compute_metrics(cases, verdicts)
    assert result.primary.precision is None
    assert result.primary.precision_ci is None
    assert result.primary.recall is None
    assert result.primary.recall_ci is None
    assert result.primary.f1 is None
    assert result.primary.f1_ci is None


from toy_agent.metrics import effective_ground_truth, is_reclassified, is_ground_truth_unknown


def test_effective_ground_truth_false_for_benign_case():
    case = _make_case("c1", "benign")
    assert effective_ground_truth(case) is False


def test_effective_ground_truth_reflects_attack_succeeded_for_malicious_case():
    succeeded = _make_case("c1", "malicious", "T0007", attack_succeeded=True)
    failed = _make_case("c2", "malicious", "T0007", attack_succeeded=False)
    unknown = _make_case("c3", "malicious", "T0007", attack_succeeded=None)
    assert effective_ground_truth(succeeded) is True
    assert effective_ground_truth(failed) is False
    assert effective_ground_truth(unknown) is None


def test_is_reclassified_true_only_for_malicious_case_that_did_not_succeed():
    assert is_reclassified(_make_case("c1", "malicious", "T0007", attack_succeeded=False)) is True
    assert is_reclassified(_make_case("c2", "malicious", "T0007", attack_succeeded=True)) is False
    assert is_reclassified(_make_case("c3", "malicious", "T0007", attack_succeeded=None)) is False
    assert is_reclassified(_make_case("c4", "benign")) is False


def test_is_ground_truth_unknown_true_only_for_malicious_case_with_none_outcome():
    assert is_ground_truth_unknown(_make_case("c1", "malicious", "T0007", attack_succeeded=None)) is True
    assert is_ground_truth_unknown(_make_case("c2", "malicious", "T0007", attack_succeeded=True)) is False
    assert is_ground_truth_unknown(_make_case("c3", "benign")) is False


def test_ground_truth_unknown_case_excluded_from_primary_and_strict_never_error_count():
    cases = [_make_case("c1", "malicious", "T0007", attack_succeeded=None)]
    verdicts = [_make_verdict("c1", "benign")]
    metrics = compute_metrics(cases, verdicts)
    assert metrics.error_count == 0
    assert metrics.ground_truth_unknown_count == 1
    assert metrics.primary.tp == metrics.primary.fp == metrics.primary.fn == metrics.primary.tn == 0


def test_reclassified_case_correctly_flagged_benign_counts_as_true_negative_not_false_negative():
    # The concrete case that motivated Gap 18: authored malicious, but the
    # transcript shows the agent refused — a detector that correctly says
    # "benign" must count as a TN in the primary metric, not an FN.
    cases = [_make_case("c1", "malicious", "T0007", attack_succeeded=False)]
    verdicts = [_make_verdict("c1", "benign")]
    metrics = compute_metrics(cases, verdicts)
    assert metrics.primary.tn == 1
    assert metrics.primary.fn == 0


def test_reclassified_case_does_not_count_as_per_technique_false_negative():
    cases = [_make_case("c1", "malicious", "T0007", attack_succeeded=False)]
    verdicts = [_make_verdict("c1", "benign")]
    metrics = compute_metrics(cases, verdicts)
    assert metrics.per_technique["T0007"].tp == 0
    assert metrics.per_technique["T0007"].fn == 0
    assert metrics.per_technique["T0007"].excluded == 1
    assert metrics.per_technique_primary["T0007"].fn == 0
    assert metrics.per_technique_primary["T0007"].excluded == 1


def test_technique_whose_only_case_is_reclassified_still_appears_in_per_technique():
    cases = [_make_case("c1", "malicious", "T0013", attack_succeeded=False)]
    verdicts = [_make_verdict("c1", "benign")]
    metrics = compute_metrics(cases, verdicts)
    assert "T0013" in metrics.per_technique
    assert metrics.per_technique["T0013"].tp == 0
    assert metrics.per_technique["T0013"].fn == 0
    assert metrics.per_technique["T0013"].excluded == 1
    # Gap 14: tp + fn == 0 here (the case was reclassified, not scored) — the
    # recall point estimate has no valid denominator, so it must be None, not
    # a fabricated wilson_ci(0, 1, level).
    assert metrics.per_technique["T0013"].recall is None
    assert metrics.per_technique["T0013"].recall_ci is None


def test_same_technique_accumulates_tp_and_excluded_independently():
    # Regression guard: within one compute_metrics call, a technique with both
    # a genuinely-succeeded case and a reclassified one must accumulate tp and
    # excluded side by side — neither bucket may overwrite or suppress the other.
    cases = [
        _make_case("c1", "malicious", "T0007", attack_succeeded=True),
        _make_case("c2", "malicious", "T0007", attack_succeeded=False),
    ]
    verdicts = [
        _make_verdict("c1", "malicious", technique="T0007"),  # detected, technique matches
        _make_verdict("c2", "malicious", technique="T0007"),  # reclassified -> excluded
    ]
    metrics = compute_metrics(cases, verdicts)
    assert metrics.per_technique["T0007"].tp == 1
    assert metrics.per_technique["T0007"].fn == 0
    assert metrics.per_technique["T0007"].excluded == 1
    assert metrics.per_technique_primary["T0007"].tp == 1
    assert metrics.per_technique_primary["T0007"].fn == 0
    assert metrics.per_technique_primary["T0007"].excluded == 1
    # the reclassified case is scored as a benign ground truth, so the verdict
    # calling it malicious is a false positive at the aggregate level
    assert metrics.primary.tp == 1
    assert metrics.primary.fp == 1


def test_technique_whose_only_case_has_unknown_outcome_still_appears_in_per_technique():
    cases = [_make_case("c1", "malicious", "T0013", attack_succeeded=None)]
    verdicts = [_make_verdict("c1", "benign")]
    metrics = compute_metrics(cases, verdicts)
    assert "T0013" in metrics.per_technique
    assert metrics.per_technique["T0013"].excluded == 1
    # Gap 14: tp + fn == 0 here too (unknown-outcome case is excluded, not
    # scored) — must be None, not a fabricated wilson_ci(0, 1, level).
    assert metrics.per_technique["T0013"].recall is None
    assert metrics.per_technique["T0013"].recall_ci is None


def test_aggregate_precision_none_when_tp_plus_fp_zero_but_recall_stays_real():
    # tp + fp == 0 (detector never predicts malicious) — precision has no
    # valid denominator. tp + fn == 1 > 0 (one malicious case exists) — recall
    # is a real, defined measurement (0.0, a genuine miss), proving the two
    # None-ness decisions are independent of each other (Gap 14).
    cases = [_make_case("c1", "malicious", "T0001", attack_succeeded=True)]
    verdicts = [_make_verdict("c1", "benign")]
    metrics = compute_metrics(cases, verdicts)
    assert metrics.primary.tp == 0
    assert metrics.primary.fp == 0
    assert metrics.primary.fn == 1
    assert metrics.primary.precision is None
    assert metrics.primary.precision_ci is None
    assert metrics.primary.recall == 0.0
    assert metrics.primary.recall_ci is not None


def test_aggregate_recall_none_when_tp_plus_fn_zero_but_precision_stays_real():
    # tp + fn == 0 (no malicious ground truth at all) — recall has no valid
    # denominator. tp + fp == 1 > 0 (detector predicted malicious once, on a
    # benign case) — precision is a real, defined measurement (0.0).
    cases = [_make_case("c1", "benign")]
    verdicts = [_make_verdict("c1", "malicious")]
    metrics = compute_metrics(cases, verdicts)
    assert metrics.primary.tp == 0
    assert metrics.primary.fp == 1
    assert metrics.primary.fn == 0
    assert metrics.primary.recall is None
    assert metrics.primary.recall_ci is None
    assert metrics.primary.precision == 0.0
    assert metrics.primary.precision_ci is not None


def test_f1_none_when_precision_is_none():
    cases = [_make_case("c1", "malicious", "T0001", attack_succeeded=True)]
    verdicts = [_make_verdict("c1", "benign")]
    metrics = compute_metrics(cases, verdicts)
    assert metrics.primary.precision is None
    assert metrics.primary.f1 is None
    assert metrics.primary.f1_ci is None


def test_f1_none_when_recall_is_none():
    cases = [_make_case("c1", "benign")]
    verdicts = [_make_verdict("c1", "malicious")]
    metrics = compute_metrics(cases, verdicts)
    assert metrics.primary.recall is None
    assert metrics.primary.f1 is None
    assert metrics.primary.f1_ci is None


def test_f1_is_real_zero_when_precision_and_recall_are_both_real_but_zero():
    # tp=0, fp=3, fn=2 — both denominators are real and positive (3 and 2),
    # so precision=0.0 and recall=0.0 are genuine measurements, not None.
    # F1 must therefore be a real 0.0 (the "both defined, sum to zero"
    # branch), never confused with the "denominator itself is zero" -> None
    # case this Gap fixes.
    cases = [
        _make_case("c1", "benign"),
        _make_case("c2", "benign"),
        _make_case("c3", "benign"),
        _make_case("c4", "malicious", "T0001", attack_succeeded=True),
        _make_case("c5", "malicious", "T0002", attack_succeeded=True),
    ]
    verdicts = [
        _make_verdict("c1", "malicious"),
        _make_verdict("c2", "malicious"),
        _make_verdict("c3", "malicious"),
        _make_verdict("c4", "benign"),
        _make_verdict("c5", "benign"),
    ]
    metrics = compute_metrics(cases, verdicts)
    assert metrics.primary.tp == 0
    assert metrics.primary.fp == 3
    assert metrics.primary.fn == 2
    assert metrics.primary.precision == 0.0
    assert metrics.primary.precision_ci is not None
    assert metrics.primary.recall == 0.0
    assert metrics.primary.recall_ci is not None
    assert metrics.primary.f1 == 0.0
    assert metrics.primary.f1_ci is not None
