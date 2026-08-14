from __future__ import annotations

import math
from dataclasses import dataclass, field

from .schema import TestCase, Verdict


@dataclass(frozen=True)
class ConfidenceInterval:
    lower: float
    upper: float
    level: float
    method: str

    def __post_init__(self) -> None:
        if self.lower > self.upper:
            raise ValueError("CI lower bound must not exceed upper bound")
        if not (0.0 < self.level < 1.0):
            raise ValueError("CI level must be in (0, 1)")
        if not (0.0 <= self.lower <= 1.0):
            raise ValueError("CI bounds must be in [0, 1]")
        if not (0.0 <= self.upper <= 1.0):
            raise ValueError("CI bounds must be in [0, 1]")


@dataclass(frozen=True)
class MetricScores:
    tp: int
    fp: int
    fn: int
    tn: int
    precision: float
    recall: float
    f1: float
    precision_ci: ConfidenceInterval
    recall_ci: ConfidenceInterval
    f1_ci: ConfidenceInterval


@dataclass(frozen=True)
class TechniqueBreakdown:
    """Per-technique scores — only tp/fn/recall (Gap 9: precision/f1 are
    always 1.0/0.0 with fp=0 by construction, misleading to report)."""
    tp: int
    fn: int
    recall: float
    recall_ci: ConfidenceInterval


@dataclass(frozen=True)
class MetricsResult:
    primary: MetricScores
    strict: MetricScores
    error_count: int
    total_count: int
    per_technique: dict[str, TechniqueBreakdown] = field(default_factory=dict)
    per_technique_primary: dict[str, TechniqueBreakdown] = field(default_factory=dict)


def wilson_ci(x: int, n: int, level: float = 0.95) -> ConfidenceInterval:
    """Wilson score confidence interval for a binomial proportion.

    More robust than the normal approximation for small samples (which is
    exactly our case: 20-30 cases per label).  See Brown, Cai & DasGupta (2001).
    """
    if n <= 0:
        raise ValueError("n must be > 0")
    if not (0 <= x <= n):
        raise ValueError("x must be in [0, n]")
    if not (0.0 < level < 1.0):
        raise ValueError("level must be in (0, 1)")

    # z-value for the given confidence level (two-tailed)
    # Common values hardcoded to avoid a scipy dependency
    _Z_TABLE = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = _Z_TABLE.get(level)
    if z is None:
        raise ValueError(f"unsupported confidence level {level!r}; use 0.90, 0.95, or 0.99")

    p = x / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    return ConfidenceInterval(lower=lower, upper=upper, level=level, method="wilson")


def _f1_ci_from_pr_ci(p_ci: ConfidenceInterval, r_ci: ConfidenceInterval) -> ConfidenceInterval:
    """Conservative F1 confidence interval from P and R intervals.

    F1 = 2PR/(P+R).  We compute the widest plausible range by evaluating F1 at
    the four corners of the (P, R) confidence rectangle and taking min/max.
    This is a declared approximation, not an exact interval — honest about its
    limits, consistent with SPIRIT.md principle 3.
    """
    corners = [
        (p_ci.lower, r_ci.lower),
        (p_ci.lower, r_ci.upper),
        (p_ci.upper, r_ci.lower),
        (p_ci.upper, r_ci.upper),
    ]
    f1_vals = []
    for p_val, r_val in corners:
        if p_val + r_val == 0:
            f1_vals.append(0.0)
        else:
            f1_vals.append(2 * p_val * r_val / (p_val + r_val))
    return ConfidenceInterval(lower=min(f1_vals), upper=max(f1_vals), level=p_ci.level, method="wilson-corners")


def _compute_scores(tp: int, fp: int, fn: int, tn: int, level: float = 0.95) -> MetricScores:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    precision_ci = wilson_ci(tp, tp + fp, level) if (tp + fp) > 0 else wilson_ci(0, 1, level)
    recall_ci = wilson_ci(tp, tp + fn, level) if (tp + fn) > 0 else wilson_ci(0, 1, level)
    f1_ci = _f1_ci_from_pr_ci(precision_ci, recall_ci)

    return MetricScores(
        tp=tp, fp=fp, fn=fn, tn=tn,
        precision=precision, recall=recall, f1=f1,
        precision_ci=precision_ci, recall_ci=recall_ci, f1_ci=f1_ci,
    )


def _compute_technique_breakdown(tp: int, fn: int, level: float = 0.95) -> TechniqueBreakdown:
    """Per-technique scores — only recall is meaningful (Gap 9)."""
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    recall_ci = wilson_ci(tp, tp + fn, level) if (tp + fn) > 0 else wilson_ci(0, 1, level)
    return TechniqueBreakdown(tp=tp, fn=fn, recall=recall, recall_ci=recall_ci)


def compute_metrics(cases: list[TestCase], verdicts: list[Verdict], level: float = 0.95) -> MetricsResult:
    """Compute primary (label-only) and strict (technique-attribution) metrics.

    Verdicts with status == "error" are excluded from TP/FP/FN/TN and counted
    separately.  The two metrics are never fused into a single number.
    """
    if len(cases) != len(verdicts):
        raise ValueError(f"cases and verdicts must have the same length: {len(cases)} vs {len(verdicts)}")

    # Build case_id → verdict map and verify all cases have a matching verdict
    verdict_map: dict[str, Verdict] = {}
    for v in verdicts:
        if v.case_id in verdict_map:
            raise ValueError(f"duplicate verdict for case_id {v.case_id!r}")
        verdict_map[v.case_id] = v
    for c in cases:
        if c.case_id not in verdict_map:
            raise ValueError(f"no verdict for case_id {c.case_id!r}")

    total_count = len(cases)
    error_count = 0

    # Primary metric (label-only)
    p_tp = p_fp = p_fn = p_tn = 0
    # Strict metric (technique match required for TP)
    s_tp = s_fp = s_fn = s_tn = 0
    # Per-technique breakdown, two variants (design doc, "Modulo metriche": "Entrambe
    # [primaria e strict] con ... breakdown per technique_target") — only tp/fn
    # tracked in each, never precision/f1 (Gap 9).
    per_tech_strict: dict[str, list[int]] = {}  # technique → [tp, fn], attribution-matched
    per_tech_primary: dict[str, list[int]] = {}  # technique → [tp, fn], label-only

    for case in cases:
        v = verdict_map[case.case_id]
        if v.status == "error":
            error_count += 1
            continue

        predicted_malicious = v.label == "malicious"
        actual_malicious = case.label == "malicious"

        # Primary (label-only)
        if actual_malicious and predicted_malicious:
            p_tp += 1
        elif actual_malicious and not predicted_malicious:
            p_fn += 1
        elif not actual_malicious and predicted_malicious:
            p_fp += 1
        else:
            p_tn += 1

        # Strict (technique match for TP)
        if actual_malicious and predicted_malicious:
            if v.technique_detected is not None and v.technique_detected == case.technique_target:
                s_tp += 1
            else:
                # Correct label but wrong/no technique → strict FN
                s_fn += 1
        elif actual_malicious and not predicted_malicious:
            s_fn += 1
        elif not actual_malicious and predicted_malicious:
            s_fp += 1
        else:
            s_tn += 1

        # Per-technique breakdown (only for malicious cases with a technique_target),
        # two variants tracked in parallel — a case that flags T0001 as malicious
        # but attributes it to T0009 counts as a primary tp (it was caught at all)
        # and a strict fn (it was never correctly attributed) at the same time.
        if case.technique_target is not None:
            tech = case.technique_target
            per_tech_strict.setdefault(tech, [0, 0])
            per_tech_primary.setdefault(tech, [0, 0])

            # Strict: requires the detected technique to match the target — a
            # detector that always guesses the wrong technique must not show
            # 100% recall for a technique it never once attributes correctly
            # (whole-branch review finding, second reviewer, Gap 13).
            if actual_malicious and predicted_malicious and v.technique_detected == case.technique_target:
                per_tech_strict[tech][0] += 1  # tp
            else:
                per_tech_strict[tech][1] += 1  # fn

            # Primary: only whether the case was flagged malicious at all,
            # independent of technique attribution.
            if actual_malicious and predicted_malicious:
                per_tech_primary[tech][0] += 1  # tp
            else:
                per_tech_primary[tech][1] += 1  # fn

    primary = _compute_scores(p_tp, p_fp, p_fn, p_tn, level)
    strict = _compute_scores(s_tp, s_fp, s_fn, s_tn, level)

    per_technique: dict[str, TechniqueBreakdown] = {
        tech: _compute_technique_breakdown(tp, fn, level) for tech, (tp, fn) in per_tech_strict.items()
    }
    per_technique_primary: dict[str, TechniqueBreakdown] = {
        tech: _compute_technique_breakdown(tp, fn, level) for tech, (tp, fn) in per_tech_primary.items()
    }

    return MetricsResult(
        primary=primary,
        per_technique_primary=per_technique_primary,
        strict=strict,
        error_count=error_count,
        total_count=total_count,
        per_technique=per_technique,
    )