from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

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


@dataclass
class TestCase:
    case_id: str
    transcript: Transcript
    label: Label
    technique_target: Optional[str]
    rationale: str

    def __post_init__(self) -> None:
        if self.label not in ("malicious", "benign"):
            raise ValueError(f"TestCase.label must be 'malicious' or 'benign', got {self.label!r}")
        if self.label == "benign" and self.technique_target is not None:
            raise ValueError("a benign TestCase must not declare a technique_target")
        if self.label == "malicious" and not self.technique_target:
            raise ValueError("a malicious TestCase must declare a technique_target")
        if not self.rationale.strip():
            raise ValueError("TestCase.rationale must not be empty")


@dataclass
class Verdict:
    case_id: str
    tool_name: str
    status: Status
    label: Optional[Label] = None
    confidence: Optional[float] = None
    technique_detected: Optional[str] = None
    rationale: Optional[str] = None
    cost_usd: Optional[float] = None
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
