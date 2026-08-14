"""End-to-end integration test: cases + verdicts -> metrics -> report.

Exercises the full pipeline with a realistic synthetic dataset covering
multiple techniques, errors, and misclassifications - verifying that the
two metrics are never fused, errors are always separate, and the report
is deterministic and contains all 5 parts.
"""

from toy_agent.metrics import compute_metrics
from toy_agent.report import render_report
from toy_agent.schema import Turn, Transcript, TestCase, Verdict


def _case(case_id, label, technique=None, rationale="r"):
    t = Transcript(session_id=f"sess_{case_id}", turns=[Turn(seq=0, role="user", content="x")])
    return TestCase(case_id=case_id, transcript=t, label=label, technique_target=technique, rationale=rationale)


def _verdict(case_id, label, status="ok", technique=None):
    if status == "error":
        return Verdict(case_id=case_id, tool_name="toy_support", status="error")
    return Verdict(case_id=case_id, tool_name="toy_support", status="ok", label=label, technique_detected=technique)


def test_full_pipeline_produces_valid_report():
    cases = [
        _case("c1", "malicious", "T0001", "prompt injection via ticket"),
        _case("c2", "malicious", "T0002", "data exfiltration via email"),
        _case("c3", "malicious", "T0003", "unauthorized email send"),
        _case("c4", "benign", None, "legitimate refund request"),
        _case("c5", "benign", None, "password reset request"),
        _case("c6", "malicious", "T0004", "tool poisoning attempt"),
        _case("c7", "benign", None, "marketing opt-out"),
    ]
    verdicts = [
        _verdict("c1", "malicious", technique="T0001"),   # correct + correct technique
        _verdict("c2", "benign"),                          # false negative
        _verdict("c3", "malicious", technique="T0009"),    # correct label, wrong technique
        _verdict("c4", "benign"),                          # correct
        _verdict("c5", "malicious", technique="T0001"),    # false positive
        _verdict("c6", None, status="error"),              # detector error
        _verdict("c7", "benign"),                          # correct
    ]

    metrics = compute_metrics(cases, verdicts)
    report = render_report(cases, verdicts, metrics)

    # Metrics invariants
    assert metrics.total_count == 7
    assert metrics.error_count == 1
    # 6 non-error cases counted in TP/FP/FN/TN
    assert metrics.primary.tp + metrics.primary.fp + metrics.primary.fn + metrics.primary.tn == 6
    # Primary and strict are distinct objects (never fused)
    assert metrics.primary is not metrics.strict
    # Strict TP <= Primary TP (strict requires technique match)
    assert metrics.strict.tp <= metrics.primary.tp

    # Report invariants
    assert "Executive Summary" in report or "Executive summary" in report
    assert "Findings" in report
    assert "Methodology" in report
    assert "Concrete Cases" in report
    assert "Raw Data" in report
    # Misclassified case c2 should appear
    assert "c2" in report
    # Determinism
    assert report == render_report(cases, verdicts, metrics)


def test_metrics_never_fuse_primary_and_strict():
    """The MetricsResult interface exposes two distinct named fields, never an aggregate."""
    cases = [_case("c1", "malicious", "T0001"), _case("c2", "benign")]
    verdicts = [_verdict("c1", "malicious", technique="T0001"), _verdict("c2", "benign")]
    result = compute_metrics(cases, verdicts)
    # No 'aggregate' or 'combined' field exists
    assert not hasattr(result, "aggregate")
    assert not hasattr(result, "combined")
    assert not hasattr(result, "overall")
    # primary and strict are both MetricScores, independently accessible
    assert hasattr(result, "primary")
    assert hasattr(result, "strict")


def test_error_verdicts_always_reported_separately():
    # Use enough cases so error_count != any TP/FP/FN/TN by construction
    cases = [
        _case("c1", "malicious", "T0001"),
        _case("c2", "benign"),
        _case("c3", "benign"),
        _case("c4", "malicious", "T0002"),
    ]
    verdicts = [
        _verdict("c1", "malicious", technique="T0001"),  # TP
        _verdict("c2", "benign"),                          # TN
        _verdict("c3", "benign"),                          # TN
        _verdict("c4", None, status="error"),              # error
    ]
    result = compute_metrics(cases, verdicts)
    assert result.error_count == 1
    assert result.total_count == 4
    # 3 non-error cases counted in TP/FP/FN/TN
    assert result.primary.tp + result.primary.fp + result.primary.fn + result.primary.tn == 3
    # Error count is a separate field, not absorbed into TP/FP/FN/TN
    # (error_count=1, but tp=1 too — the point is they are separate fields,
    # not that the numbers are always different. Verify the sum invariant:
    # tp+fp+fn+tn+error_count == total_count)
    assert result.primary.tp + result.primary.fp + result.primary.fn + result.primary.tn + result.error_count == result.total_count
