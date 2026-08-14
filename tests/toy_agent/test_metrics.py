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
    tb = TechniqueBreakdown(tp=3, fn=1, recall=0.75, recall_ci=ci)
    assert tb.tp == 3
    assert tb.fn == 1
    assert not hasattr(tb, "precision")
    assert not hasattr(tb, "f1")


def test_metrics_result_has_primary_and_strict():
    ci = ConfidenceInterval(lower=0.5, upper=0.9, level=0.95, method="wilson")
    scores = MetricScores(tp=10, fp=2, fn=3, tn=15, precision=0.83, recall=0.77, f1=0.80, precision_ci=ci, recall_ci=ci, f1_ci=ci)
    result = MetricsResult(primary=scores, strict=scores, error_count=1, total_count=31, per_technique={})
    assert result.primary is not None
    assert result.strict is not None
    assert result.error_count == 1


from toy_agent.schema import ToolCall, Turn, Transcript, TestCase, Verdict
from toy_agent.metrics import wilson_ci, compute_metrics


def _make_case(case_id, label, technique=None):
    t = Transcript(session_id=f"sess_{case_id}", turns=[Turn(seq=0, role="user", content="x")])
    return TestCase(case_id=case_id, transcript=t, label=label, technique_target=technique, rationale="r")


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


def test_compute_metrics_always_returns_ci():
    cases = [_make_case("c1", "benign")]
    verdicts = [_make_verdict("c1", "benign")]
    result = compute_metrics(cases, verdicts)
    assert result.primary.precision_ci is not None
    assert result.primary.recall_ci is not None
    assert result.primary.f1_ci is not None
