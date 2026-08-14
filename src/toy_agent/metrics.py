from __future__ import annotations

from dataclasses import dataclass, field


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