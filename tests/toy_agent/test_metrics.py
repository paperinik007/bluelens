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