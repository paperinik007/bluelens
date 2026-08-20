from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Union

Role = Literal["user", "assistant", "tool"]
Status = Literal["ok", "error"]
Label = Literal["malicious", "benign"]


@dataclass
class ToolCall:
    tool_name: str
    arguments: dict
    result: Optional[str]
    status: Status

    def __post_init__(self) -> None:
        if self.status not in ("ok", "error"):
            raise ValueError(f"ToolCall.status must be 'ok' or 'error', got {self.status!r}")


@dataclass
class Turn:
    seq: int
    role: Role
    content: str
    tool_call: Optional[ToolCall] = None

    def __post_init__(self) -> None:
        if self.role not in ("user", "assistant", "tool"):
            raise ValueError(f"Turn.role must be 'user'/'assistant'/'tool', got {self.role!r}")
        if self.role == "tool" and self.tool_call is None:
            raise ValueError("Turn.role == 'tool' requires a tool_call")
        if self.role != "tool" and self.tool_call is not None:
            raise ValueError("tool_call is only allowed when role == 'tool'")


@dataclass
class Transcript:
    session_id: str
    turns: list[Turn] = field(default_factory=list)
    stop_reason: Optional[Literal["completed", "max_turns", "max_cost", "model_error"]] = None


# --- attack_success_criteria DSL (Gap 18) ---
# A small closed hierarchy, Union + isinstance dispatch — same idiom sequence.py
# already uses for SequenceStep. Only data shape lives here; evaluation logic
# lives in criteria.py (Task 2).

@dataclass(frozen=True)
class Equals:
    value: Any


@dataclass(frozen=True)
class NotEquals:
    value: Any


@dataclass(frozen=True)
class InSet:
    values: tuple


@dataclass(frozen=True)
class NotInSet:
    values: tuple


@dataclass(frozen=True)
class Contains:
    value: Any


ArgMatcherType = Union[Equals, NotEquals, InSet, NotInSet, Contains]


@dataclass(frozen=True)
class ToolCallCriterion:
    tool_name: str
    arguments: dict = field(default_factory=dict)  # str -> ArgMatcherType
    min_count: int = 1
    require_ok: bool = False  # if True, a matching call with status="error" doesn't count


@dataclass(frozen=True)
class AllOf:
    criteria: tuple  # tuple[CriterionType, ...]


@dataclass(frozen=True)
class AnyOf:
    criteria: tuple  # tuple[CriterionType, ...]


@dataclass(frozen=True)
class Not:
    criterion: "CriterionType"


@dataclass(frozen=True)
class Always:
    pass


CriterionType = Union[ToolCallCriterion, AllOf, AnyOf, Not, Always]


@dataclass
class TestCase:
    case_id: str
    label: Label
    technique_target: Optional[str]
    rationale: str
    transcript: Optional[Transcript] = None
    attack_success_criteria: Optional[CriterionType] = None
    attack_succeeded: Optional[bool] = None

    def __post_init__(self) -> None:
        if self.label not in ("malicious", "benign"):
            raise ValueError(f"TestCase.label must be 'malicious' or 'benign', got {self.label!r}")
        if self.label == "benign" and self.technique_target is not None:
            raise ValueError("a benign TestCase must not declare a technique_target")
        if self.label == "malicious" and not self.technique_target:
            raise ValueError("a malicious TestCase must declare a technique_target")
        if not self.rationale.strip():
            raise ValueError("TestCase.rationale must not be empty")
        if self.label == "malicious" and self.attack_success_criteria is None:
            raise ValueError("a malicious TestCase must declare attack_success_criteria")
        if self.label == "benign" and self.attack_success_criteria is not None:
            raise ValueError("a benign TestCase must not declare attack_success_criteria")


@dataclass
class Verdict:
    case_id: str
    tool_name: str  # which detector produced this Verdict — a constant today (one
                     # detector active per audit at a time, design doc, "Limiti
                     # dichiarati"), kept so a future second-vendor Verdict is
                     # distinguishable without a schema change; populated by
                     # detector_adapter (src/detector_adapter/adapter.py)
    status: Status
    label: Optional[Label] = None
    confidence: Optional[float] = None
    technique_detected: Optional[str] = None
    rationale: Optional[str] = None
    cost_usd: Optional[float] = None  # always None from detector_adapter — computed
                                       # later by the metrics module (Plan 4) from
                                       # token counts + known pricing, design doc,
                                       # "Schema di misura"
    latency_s: Optional[float] = None

    def __post_init__(self) -> None:
        if self.status not in ("ok", "error"):
            raise ValueError(f"Verdict.status must be 'ok' or 'error', got {self.status!r}")
        if self.status == "error" and self.label is not None:
            raise ValueError("Verdict.status == 'error' requires label is None")
        if self.status == "ok" and self.label is None:
            raise ValueError("Verdict.status == 'ok' requires a non-None label")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Verdict.confidence must be within [0, 1]")
        if self.cost_usd is not None and self.cost_usd < 0:
            raise ValueError("Verdict.cost_usd must be non-negative")
        if self.latency_s is not None and self.latency_s < 0:
            raise ValueError("Verdict.latency_s must be non-negative")


def validate_unique_case_ids(cases: list[TestCase]) -> None:
    seen: set[str] = set()
    for case in cases:
        if case.case_id in seen:
            raise ValueError(f"duplicate case_id: {case.case_id!r}")
        seen.add(case.case_id)
