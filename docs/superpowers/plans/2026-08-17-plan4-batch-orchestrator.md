# Plan 4 — Batch Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `run_batch.py`, the missing composition piece that drives an entire dataset of `TestCase`s through the existing `agent`/`detector` pipeline (`orchestrator.run_test_case()`, Gap 9) one case at a time, persists raw evidence per case, and produces the final Markdown audit report — closing Gap 6.

**Architecture:** A per-case loop (`execute_batch`) that: builds a ground-truth-free input dict for `run_test_case()`, persists the raw verdict/transcript dicts immediately, collects external evidence immediately, converts dicts to dataclasses with a fallback on malformed data, and tracks a circuit breaker on consecutive infra failures. A thin CLI wrapper (`main()`) loads the YAML dataset, runs the loop, then calls the already-built `compute_metrics()`/`render_report()` and writes `report.md`. No new measurement logic — pure composition, per the design doc's own framing.

**Tech Stack:** Python 3.11+, pytest, `pyyaml` (new dependency, `yaml.safe_load` only).

**Spec:** `docs/design/2026-08-17-plan4-batch-orchestrator-design.md` (14 decisions, mapping Requisito→Verifica, council checkpoint outcome). Executors should read both this plan and the spec — the spec has the "why" behind constraints this plan states as fact.

## Global Constraints

- Python `>=3.11` (`pyproject.toml`).
- YAML parsing anywhere in `toy_agent` uses `yaml.safe_load` only — never `yaml.load` (design doc decision 11; dataset entries contain adversarial payloads by construction).
- Every `case_id` loaded from a dataset file is validated against `^[a-zA-Z0-9_-]+$` before it is used to build any filesystem path (decision 12).
- `dataset_dir` is never written to by any code in this plan (decision 10).
- `Verdict.cost_usd` stays `None` in every `Verdict` produced by this plan; `in_tokens`/`out_tokens` stay in the raw persisted dicts only, never added to the `Verdict` dataclass (decision 7).
- Ground truth (`label`/`technique_target`/`rationale`) must never be included in the dict sent to `run_test_case()` (decision 2).
- Default `agent_timeout_s=120.0`, `detector_timeout_s=180.0` (must match `orchestrator.run_test_case()`'s own defaults, `src/toy_agent/orchestrator.py:55-56`) and circuit breaker threshold `3` consecutive `error_kind: "infra"` verdicts (decision 8).

---

## Task 1: `schema.py` — make `TestCase.transcript` optional

**Files:**
- Modify: `src/toy_agent/schema.py:46-62`
- Test: `tests/toy_agent/test_schema.py`

**Interfaces:**
- Produces: `TestCase(case_id: str, label: Label, technique_target: Optional[str], rationale: str, transcript: Optional[Transcript] = None)` — **field order changes** (`transcript` moves from position 2 to last, now with a default). All existing call sites use keyword arguments only (verified via `rg "TestCase\("` across `tests/` and `docs/`) so this is safe, but every task below that constructs a `TestCase` must use keyword arguments.

- [ ] **Step 1: Write the failing test**

Add to `tests/toy_agent/test_schema.py`:

```python
def test_testcase_transcript_defaults_to_none():
    case = TestCase(case_id="c1", label="benign", technique_target=None, rationale="r")
    assert case.transcript is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/toy_agent/test_schema.py::test_testcase_transcript_defaults_to_none -v`
Expected: FAIL — `TypeError: TestCase.__init__() missing 1 required positional argument: 'transcript'`

- [ ] **Step 3: Reorder fields and add the default**

In `src/toy_agent/schema.py`, replace the `TestCase` dataclass:

```python
@dataclass
class TestCase:
    case_id: str
    label: Label
    technique_target: Optional[str]
    rationale: str
    transcript: Optional[Transcript] = None

    def __post_init__(self) -> None:
        if self.label not in ("malicious", "benign"):
            raise ValueError(f"TestCase.label must be 'malicious' or 'benign', got {self.label!r}")
        if self.label == "benign" and self.technique_target is not None:
            raise ValueError("a benign TestCase must not declare a technique_target")
        if self.label == "malicious" and not self.technique_target:
            raise ValueError("a malicious TestCase must declare a technique_target")
        if not self.rationale.strip():
            raise ValueError("TestCase.rationale must not be empty")
```

(Only the field order and the `= None` default on `transcript` changed — `__post_init__` body is unchanged.)

- [ ] **Step 4: Run the full schema test suite**

Run: `pytest tests/toy_agent/test_schema.py -v`
Expected: PASS (all tests, including the pre-existing ones — they all use keyword arguments so field reordering does not break them)

- [ ] **Step 5: Run the full test suite to catch any missed positional call site**

Run: `pytest tests/toy_agent -v`
Expected: PASS. If any test fails with a `TypeError` about `TestCase.__init__`, it means a positional call site was missed — find it with `rg "TestCase\(" tests/` and convert it to keyword arguments before proceeding.

- [ ] **Step 6: Commit**

```bash
git add src/toy_agent/schema.py tests/toy_agent/test_schema.py
git commit -m "feat: make TestCase.transcript optional (Plan 4 decision 4)"
```

---

## Task 2: `serialization.py` — dict ↔ dataclass conversion

**Files:**
- Create: `src/toy_agent/serialization.py`
- Test: `tests/toy_agent/test_serialization.py`

**Interfaces:**
- Consumes: `toy_agent.schema.{Transcript, Turn, ToolCall, Verdict}` (Task 1's `Verdict`/`Transcript` shapes, unchanged by Task 1).
- Produces: `transcript_from_dict(d: dict) -> Transcript`, `verdict_from_dict(d: dict) -> Verdict`. Both raise whatever exception the underlying dataclass constructor raises (`ValueError` from `__post_init__`, `KeyError` for a missing required key) — callers are responsible for catching (Task 5).

- [ ] **Step 1: Write the failing tests**

Create `tests/toy_agent/test_serialization.py`:

```python
import pytest

from toy_agent.run_case import transcript_to_dict
from toy_agent.schema import ToolCall, Transcript, Turn, Verdict
from toy_agent.serialization import transcript_from_dict, verdict_from_dict


def test_transcript_round_trips_through_dict():
    original = Transcript(
        session_id="sess_1",
        turns=[
            Turn(seq=0, role="user", content="hello"),
            Turn(
                seq=1,
                role="tool",
                content="",
                tool_call=ToolCall(tool_name="query_customer_db", arguments={"id": "1"}, result="ok", status="ok"),
            ),
        ],
        stop_reason="completed",
    )
    rebuilt = transcript_from_dict(transcript_to_dict(original))
    assert rebuilt == original


def test_transcript_from_dict_defaults_stop_reason_to_none():
    t = transcript_from_dict({"session_id": "s1", "turns": []})
    assert t.stop_reason is None
    assert t.turns == []


def test_verdict_from_dict_builds_an_ok_verdict():
    d = {
        "case_id": "c1", "tool_name": "agentic_threat_detection", "status": "ok",
        "label": "malicious", "confidence": 0.9, "technique_detected": "T0001",
        "rationale": "r", "cost_usd": None, "latency_s": 1.2,
    }
    v = verdict_from_dict(d)
    assert v.case_id == "c1"
    assert v.confidence == 0.9
    assert v.latency_s == 1.2


def test_verdict_from_dict_ignores_extra_keys_not_in_the_schema():
    d = {
        "case_id": "c1", "tool_name": "agentic_threat_detection", "status": "error",
        "error_kind": "infra", "rationale": "boom",
        "in_tokens": 100, "out_tokens": 50,
    }
    v = verdict_from_dict(d)
    assert v.status == "error"
    assert v.rationale == "boom"
    assert not hasattr(v, "error_kind")
    assert not hasattr(v, "in_tokens")


def test_verdict_from_dict_raises_on_out_of_range_confidence():
    d = {"case_id": "c1", "tool_name": "x", "status": "ok", "label": "malicious", "confidence": 1.5}
    with pytest.raises(ValueError):
        verdict_from_dict(d)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/toy_agent/test_serialization.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'toy_agent.serialization'`

- [ ] **Step 3: Write the implementation**

Create `src/toy_agent/serialization.py`:

```python
from __future__ import annotations

from .schema import ToolCall, Transcript, Turn, Verdict


def _tool_call_from_dict(d: dict | None) -> ToolCall | None:
    if d is None:
        return None
    return ToolCall(tool_name=d["tool_name"], arguments=d["arguments"], result=d.get("result"), status=d["status"])


def _turn_from_dict(d: dict) -> Turn:
    return Turn(seq=d["seq"], role=d["role"], content=d["content"], tool_call=_tool_call_from_dict(d.get("tool_call")))


def transcript_from_dict(d: dict) -> Transcript:
    """Inverse of run_case.py::transcript_to_dict (design doc decision 3)."""
    return Transcript(
        session_id=d["session_id"],
        turns=[_turn_from_dict(t) for t in d.get("turns", [])],
        stop_reason=d.get("stop_reason"),
    )


_VERDICT_FIELDS = (
    "case_id", "tool_name", "status", "label", "confidence",
    "technique_detected", "rationale", "cost_usd", "latency_s",
)


def verdict_from_dict(d: dict) -> Verdict:
    """Inverse of detector_adapter's Verdict-shaped dicts (design doc decision 3).

    Only known Verdict fields are read — extra keys (in_tokens, out_tokens,
    error_kind) are silently ignored here; they are never lost, only absent
    from the in-memory dataclass, because the raw dict is persisted to disk
    before this function is ever called (decision 6)."""
    kwargs = {k: d[k] for k in _VERDICT_FIELDS if k in d}
    return Verdict(**kwargs)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/toy_agent/test_serialization.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/toy_agent/serialization.py tests/toy_agent/test_serialization.py
git commit -m "feat: add dict<->dataclass conversion for Transcript/Verdict (Plan 4 decision 3)"
```

---

## Task 3: `evidence.py` — fix the `_container_id()` crash on empty output

**Files:**
- Modify: `src/toy_agent/evidence.py:15-17, 40-49`
- Test: `tests/toy_agent/test_evidence.py`

**Interfaces:**
- Produces: `_container_id(service: str, run_command: CommandRunner) -> Optional[str]` (was `-> str`, raised `IndexError` on empty output). `collect_case_evidence()`'s public signature is unchanged; its behavior changes: a service whose container cannot be found is skipped for the `diff`/`stats` channels only (its `.logs.txt` channel, which does not need a container id, is unaffected).

This closes the design doc's mapping-table row on its own — the test below exercises `collect_case_evidence()`, not `_container_id()` in isolation, so no later task is required for this guarantee to hold (council-risk finding).

- [ ] **Step 1: Write the failing test**

Add to `tests/toy_agent/test_evidence.py`:

```python
def test_collect_case_evidence_skips_diff_and_stats_when_container_id_is_empty(tmp_path):
    runner = FakeRunner({
        ("docker", "compose", "logs", "--no-color", "agent"): b"",
        ("docker", "compose", "logs", "--no-color", "detector"): b"",
        ("docker", "compose", "logs", "--no-color", "egress-proxy"): b"",
        _ps_key("agent"): b"",  # container unreachable — no lines on stdout
        _ps_key("detector"): b"def456\n",
        ("docker", "diff", "def456"): b"C /var/log/vendor_proxy.jsonl\n",
        ("docker", "stats", "--no-stream", "def456"): b"detector stats\n",
    })

    written = collect_case_evidence("case_004", ("agent", "detector"), tmp_path, run_command=runner)

    assert "agent.diff" not in written
    assert "agent.stats" not in written
    assert not (tmp_path / "case_004" / "agent.diff.txt").exists()
    assert not (tmp_path / "case_004" / "agent.stats.txt").exists()
    assert "detector.diff" in written
    assert "detector.stats" in written
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/toy_agent/test_evidence.py::test_collect_case_evidence_skips_diff_and_stats_when_container_id_is_empty -v`
Expected: FAIL — `AssertionError: unscripted command: ['docker', 'diff', '']` (or an `IndexError` from `_container_id`, depending on dict ordering) — the current code calls `run_command(["docker", "diff", ""])`-shaped commands or crashes outright.

- [ ] **Step 3: Fix `_container_id()` and its caller**

In `src/toy_agent/evidence.py`, change the import line and the two functions:

```python
from typing import Callable, Optional
```

```python
def _container_id(service: str, run_command: CommandRunner) -> Optional[str]:
    output = run_command(["docker", "compose", "ps", "-q", service])
    lines = output.decode("utf-8", errors="replace").strip().splitlines()
    return lines[0] if lines else None
```

In `collect_case_evidence()`, replace the `for service in services:` block that builds diff/stats:

```python
    for service in services:
        container_id = _container_id(service, run_command)
        if container_id is None:
            # Service unreachable (e.g. Docker daemon instability) — degrade
            # this one case's evidence for this one channel, never crash the
            # batch (design doc, mapping Requisito -> Verifica).
            continue

        diff_path = case_dir / f"{service}.diff.txt"
        diff_path.write_bytes(run_command(["docker", "diff", container_id]))
        written[f"{service}.diff"] = diff_path

        stats_path = case_dir / f"{service}.stats.txt"
        stats_path.write_bytes(run_command(["docker", "stats", "--no-stream", container_id]))
        written[f"{service}.stats"] = stats_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/toy_agent/test_evidence.py -v`
Expected: PASS (all tests, including the new one and the pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add src/toy_agent/evidence.py tests/toy_agent/test_evidence.py
git commit -m "fix: evidence collection must not crash on an empty 'docker compose ps -q' result"
```

---

## Task 4: `pyproject.toml` + `dataset.py` — load the YAML dataset

**Files:**
- Modify: `pyproject.toml:5-8`
- Create: `src/toy_agent/dataset.py`
- Test: `tests/toy_agent/test_dataset.py`

**Interfaces:**
- Consumes: `toy_agent.schema.{TestCase, validate_unique_case_ids}` (Task 1), `toy_agent.serialization.transcript_from_dict` (Task 2).
- Produces: `CASE_ID_PATTERN: re.Pattern` (the allowlist regex, decision 12 — Plan 5 inherits this constant), `load_dataset(dataset_dir: Path) -> list[TestCase]`.

- [ ] **Step 1: Add the `pyyaml` dependency**

In `pyproject.toml`, change the `dependencies` list:

```toml
dependencies = [
    "openai>=1.0.0",
    "httpx>=0.26",
    "pyyaml>=6.0",
]
```

Run: `pip install -e .` (or the project's normal install command) to make `yaml` importable before writing any test that needs it.

- [ ] **Step 2: Write the failing tests**

Create `tests/toy_agent/test_dataset.py`:

```python
import pytest
import yaml

from toy_agent.dataset import load_dataset


def _entry(case_id: str, label: str = "benign", technique_target: str | None = None, rationale: str = "r") -> dict:
    return {
        "case_id": case_id,
        "label": label,
        "technique_target": technique_target,
        "rationale": rationale,
        "transcript": {
            "session_id": case_id,
            "turns": [{"seq": 0, "role": "user", "content": "hi", "tool_call": None}],
            "stop_reason": None,
        },
    }


def _write(dir_, filename: str, data: dict) -> None:
    (dir_ / filename).write_text(yaml.safe_dump(data), encoding="utf-8")


def test_load_dataset_reads_every_yaml_entry(tmp_path):
    _write(tmp_path, "case_001.yaml", _entry("case_001"))
    _write(tmp_path, "case_002.yaml", _entry("case_002", label="malicious", technique_target="T0001"))

    cases = load_dataset(tmp_path)

    assert {c.case_id for c in cases} == {"case_001", "case_002"}
    malicious = next(c for c in cases if c.case_id == "case_002")
    assert malicious.technique_target == "T0001"
    assert malicious.transcript.turns[0].content == "hi"


def test_load_dataset_rejects_a_case_id_with_a_path_separator(tmp_path):
    _write(tmp_path, "evil.yaml", _entry("../evil"))

    with pytest.raises(ValueError):
        load_dataset(tmp_path)


def test_load_dataset_rejects_a_case_id_with_a_space(tmp_path):
    _write(tmp_path, "evil.yaml", _entry("case 001"))

    with pytest.raises(ValueError):
        load_dataset(tmp_path)


def test_load_dataset_rejects_duplicate_case_ids(tmp_path):
    _write(tmp_path, "a.yaml", _entry("dup_case"))
    _write(tmp_path, "b.yaml", _entry("dup_case"))

    with pytest.raises(ValueError):
        load_dataset(tmp_path)


def test_load_dataset_does_not_write_to_the_dataset_dir(tmp_path):
    _write(tmp_path, "case_001.yaml", _entry("case_001"))
    before = (tmp_path / "case_001.yaml").read_text(encoding="utf-8")

    load_dataset(tmp_path)

    after = (tmp_path / "case_001.yaml").read_text(encoding="utf-8")
    assert before == after
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/toy_agent/test_dataset.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'toy_agent.dataset'`

- [ ] **Step 4: Write the implementation**

Create `src/toy_agent/dataset.py`:

```python
from __future__ import annotations

import re
from pathlib import Path

import yaml

from .schema import TestCase, validate_unique_case_ids
from .serialization import transcript_from_dict

# Plan 5 (dataset construction) inherits this constant — every case_id written
# to a dataset YAML file must match it (design doc decision 12).
CASE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _entry_to_test_case(data: dict, source: Path) -> TestCase:
    case_id = data.get("case_id")
    if not isinstance(case_id, str) or not CASE_ID_PATTERN.match(case_id):
        raise ValueError(
            f"{source}: case_id {case_id!r} does not match the allowed pattern {CASE_ID_PATTERN.pattern!r}"
        )
    return TestCase(
        case_id=case_id,
        label=data["label"],
        technique_target=data.get("technique_target"),
        rationale=data["rationale"],
        transcript=transcript_from_dict(data["transcript"]),
    )


def load_dataset(dataset_dir: Path) -> list[TestCase]:
    """Load every *.yaml TestCase entry under dataset_dir (design doc decision 1).

    Never writes to dataset_dir (decision 10). Each case_id is validated
    against CASE_ID_PATTERN before it is used for anything else, including
    before this function returns — no caller ever sees an unvalidated
    case_id (decision 12)."""
    cases: list[TestCase] = []
    for path in sorted(dataset_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        cases.append(_entry_to_test_case(data, path))
    validate_unique_case_ids(cases)
    return cases
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/toy_agent/test_dataset.py -v`
Expected: PASS

- [ ] **Step 6: Static check — no bare `yaml.load`**

Run: `rg "yaml\.load\(" src/toy_agent`
Expected: no output (only `yaml.safe_load` is used anywhere in `src/toy_agent`, per the design doc's static-check requirement).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/toy_agent/dataset.py tests/toy_agent/test_dataset.py
git commit -m "feat: add pyyaml dependency and dataset.py::load_dataset (Plan 4 decisions 1, 11, 12)"
```

---

## Task 5: `run_batch.py` — the per-case batch loop (`execute_batch`)

**Files:**
- Create: `src/toy_agent/run_batch.py`
- Test: `tests/toy_agent/test_run_batch.py`

**Interfaces:**
- Consumes: `toy_agent.schema.{TestCase, Verdict}` (Task 1), `toy_agent.serialization.{transcript_from_dict, verdict_from_dict}` (Task 2), `toy_agent.evidence.{collect_case_evidence, collect_thin_proxy_log}` (Task 3, signatures unchanged), `toy_agent.orchestrator.run_test_case` (existing, unchanged).
- Produces:
  - `AGENT_TIMEOUT_S = 120.0`, `DETECTOR_TIMEOUT_S = 180.0`, `BREAKER_THRESHOLD = 3`, `SERVICES = ("agent", "detector")` — module-level constants, consumed by Task 6.
  - `BatchResult` dataclass: `cases: list[TestCase]`, `verdicts: list[Verdict]`, `total_count: int`, `executed_count: int`, `breaker_tripped: bool`, `last_infra_rationale: Optional[str]`.
  - `execute_batch(dataset: list[TestCase], run_output_dir: Path, *, agent_timeout_s: float = AGENT_TIMEOUT_S, detector_timeout_s: float = DETECTOR_TIMEOUT_S, breaker_threshold: int = BREAKER_THRESHOLD, api_key: str = "", run_test_case_fn=run_test_case, collect_case_evidence_fn=evidence.collect_case_evidence, collect_thin_proxy_log_fn=evidence.collect_thin_proxy_log) -> BatchResult` — consumed by Task 6's `main()`.

- [ ] **Step 1: Write the failing tests**

Create `tests/toy_agent/test_run_batch.py`:

```python
import json

from toy_agent.run_batch import execute_batch
from toy_agent.schema import Transcript, Turn, TestCase


def _ground_truth(case_id, label="benign", technique_target=None, rationale="r", seed_content="hi"):
    transcript = Transcript(session_id=case_id, turns=[Turn(seq=0, role="user", content=seed_content)])
    return TestCase(case_id=case_id, label=label, technique_target=technique_target, rationale=rationale, transcript=transcript)


def _ok_result(case_id, label="benign", technique=None):
    return {
        "transcript": {"session_id": case_id, "turns": [], "stop_reason": "completed"},
        "verdict": {
            "case_id": case_id, "tool_name": "agentic_threat_detection", "status": "ok",
            "label": label, "confidence": 0.9, "technique_detected": technique,
            "rationale": "r", "cost_usd": None, "latency_s": 1.0,
            "in_tokens": 10, "out_tokens": 5,
        },
    }


def _infra_result(case_id):
    return {
        "transcript": None,
        "verdict": {
            "case_id": case_id, "tool_name": "agentic_threat_detection", "status": "error",
            "error_kind": "infra", "label": None, "confidence": None, "technique_detected": None,
            "rationale": "docker compose exec failed to start", "cost_usd": None, "latency_s": None,
        },
    }


def _application_result(case_id):
    return {
        "transcript": None,
        "verdict": {
            "case_id": case_id, "tool_name": "agentic_threat_detection", "status": "error",
            "error_kind": "application", "label": None, "confidence": None, "technique_detected": None,
            "rationale": "bad seed turn", "cost_usd": None, "latency_s": None,
        },
    }


class ScriptedRunTestCase:
    def __init__(self, script):
        self._script = list(script)
        self.calls = []

    def __call__(self, test_case, *, agent_timeout_s, detector_timeout_s):
        self.calls.append(test_case)
        if not self._script:
            raise AssertionError("script exhausted")
        result = self._script.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class RecordingEvidenceCollector:
    def __init__(self):
        self.calls = []

    def __call__(self, case_id, services, evidence_dir):
        self.calls.append(case_id)
        return {}


class RecordingProxyLogCollector:
    def __init__(self):
        self.calls = []

    def __call__(self, case_id, evidence_dir, api_key):
        self.calls.append(case_id)
        return evidence_dir / case_id / "detector.vendor_proxy.jsonl"


def test_ground_truth_never_reaches_run_test_case(tmp_path):
    dataset = [_ground_truth("c1", label="malicious", technique_target="T0001", rationale="secret rationale", seed_content="hello")]
    runner = ScriptedRunTestCase([_ok_result("c1")])

    execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                  collect_case_evidence_fn=RecordingEvidenceCollector(),
                  collect_thin_proxy_log_fn=RecordingProxyLogCollector())

    sent = runner.calls[0]
    assert set(sent.keys()) == {"case_id", "transcript"}
    assert sent["case_id"] == "c1"
    assert sent["transcript"]["turns"] == [{"seq": 0, "role": "user", "content": "hello", "tool_call": None}]
    assert "secret rationale" not in json.dumps(sent)
    assert "T0001" not in json.dumps(sent)


def test_every_case_id_appears_in_both_output_lists_even_on_failure(tmp_path):
    dataset = [_ground_truth("c1"), _ground_truth("c2")]
    runner = ScriptedRunTestCase([_application_result("c1"), _ok_result("c2")])

    result = execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                            collect_case_evidence_fn=RecordingEvidenceCollector(),
                            collect_thin_proxy_log_fn=RecordingProxyLogCollector())

    assert [c.case_id for c in result.cases] == ["c1", "c2"]
    assert [v.case_id for v in result.verdicts] == ["c1", "c2"]
    assert result.verdicts[0].status == "error"


def test_circuit_breaker_trips_after_three_consecutive_infra_failures(tmp_path):
    dataset = [_ground_truth(f"c{i}") for i in range(1, 5)]
    runner = ScriptedRunTestCase([_infra_result("c1"), _infra_result("c2"), _infra_result("c3")])

    result = execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                            collect_case_evidence_fn=RecordingEvidenceCollector(),
                            collect_thin_proxy_log_fn=RecordingProxyLogCollector())

    assert len(runner.calls) == 3  # c4 never attempted
    assert result.breaker_tripped is True
    assert result.executed_count == 3
    assert result.total_count == 4
    assert result.last_infra_rationale == "docker compose exec failed to start"


def test_non_infra_verdict_resets_the_breaker_counter(tmp_path):
    dataset = [_ground_truth(f"c{i}") for i in range(1, 6)]
    runner = ScriptedRunTestCase([
        _infra_result("c1"), _infra_result("c2"), _ok_result("c3"),
        _infra_result("c4"), _infra_result("c5"),
    ])

    result = execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                            collect_case_evidence_fn=RecordingEvidenceCollector(),
                            collect_thin_proxy_log_fn=RecordingProxyLogCollector())

    assert len(runner.calls) == 5  # never tripped — counter reset at c3
    assert result.breaker_tripped is False


def test_per_case_data_is_persisted_immediately_even_if_a_later_case_raises(tmp_path):
    dataset = [_ground_truth("c1"), _ground_truth("c2"), _ground_truth("c3")]
    runner = ScriptedRunTestCase([_ok_result("c1"), _ok_result("c2"), RuntimeError("simulated crash")])

    try:
        execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                      collect_case_evidence_fn=RecordingEvidenceCollector(),
                      collect_thin_proxy_log_fn=RecordingProxyLogCollector())
        assert False, "expected RuntimeError to propagate"
    except RuntimeError:
        pass

    lines = (tmp_path / "verdicts.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["case_id"] == "c1"
    assert json.loads(lines[1])["case_id"] == "c2"
    assert (tmp_path / "raw" / "c1.transcript.json").exists()
    assert (tmp_path / "raw" / "c2.transcript.json").exists()
    assert not (tmp_path / "raw" / "c3.transcript.json").exists()


def test_transcript_is_none_when_the_agent_invocation_never_produced_one(tmp_path):
    dataset = [_ground_truth("c1", label="malicious", technique_target="T0001")]
    runner = ScriptedRunTestCase([_infra_result("c1")])

    result = execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                            collect_case_evidence_fn=RecordingEvidenceCollector(),
                            collect_thin_proxy_log_fn=RecordingProxyLogCollector())

    assert result.cases[0].transcript is None
    assert result.cases[0].label == "malicious"  # ground truth still present (decision 2 is independent of decision 4)


def test_conversion_failure_falls_back_to_an_error_verdict_and_does_not_trip_the_breaker(tmp_path):
    # c1: infra failure, c2: an ok-status verdict with an out-of-range
    # confidence (the concrete scenario decision 14 was written for), c3/c4:
    # two more infra failures. If "conversion" resets the breaker like
    # "application" does, the batch must not trip (max run of 2 infra at a time).
    dataset = [_ground_truth("c1"), _ground_truth("c2"), _ground_truth("c3"), _ground_truth("c4")]
    bad_confidence_result = _ok_result("c2")
    bad_confidence_result["verdict"]["confidence"] = 1.5
    runner = ScriptedRunTestCase([
        _infra_result("c1"), bad_confidence_result, _infra_result("c3"), _infra_result("c4"),
    ])

    result = execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                            collect_case_evidence_fn=RecordingEvidenceCollector(),
                            collect_thin_proxy_log_fn=RecordingProxyLogCollector())

    assert len(runner.calls) == 4  # never tripped
    assert result.breaker_tripped is False
    c2_verdict = result.verdicts[1]
    assert c2_verdict.status == "error"
    assert "conversion failed: ValueError" in c2_verdict.rationale
    # the raw (malformed) dict is still on disk, untouched
    lines = (tmp_path / "verdicts.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert json.loads(lines[1])["confidence"] == 1.5


def test_evidence_is_collected_for_every_case_regardless_of_outcome(tmp_path):
    dataset = [_ground_truth("c1"), _ground_truth("c2")]
    runner = ScriptedRunTestCase([_infra_result("c1"), _ok_result("c2")])
    evidence_collector = RecordingEvidenceCollector()
    proxy_collector = RecordingProxyLogCollector()

    execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                  collect_case_evidence_fn=evidence_collector,
                  collect_thin_proxy_log_fn=proxy_collector)

    assert evidence_collector.calls == ["c1", "c2"]
    assert proxy_collector.calls == ["c1", "c2"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/toy_agent/test_run_batch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'toy_agent.run_batch'`

- [ ] **Step 3: Write the implementation**

Create `src/toy_agent/run_batch.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import evidence
from .orchestrator import run_test_case
from .schema import TestCase, Verdict
from .serialization import transcript_from_dict, verdict_from_dict

AGENT_TIMEOUT_S = 120.0
DETECTOR_TIMEOUT_S = 180.0
BREAKER_THRESHOLD = 3
SERVICES = ("agent", "detector")


@dataclass
class BatchResult:
    cases: list[TestCase]
    verdicts: list[Verdict]
    total_count: int
    executed_count: int
    breaker_tripped: bool
    last_infra_rationale: Optional[str] = None


def _agent_input(case: TestCase) -> dict:
    """Reduced dict sent to run_test_case(): only case_id and the seed turn's
    content — never label/technique_target/rationale (design doc decision 2)."""
    seed = case.transcript.turns[0]
    return {
        "case_id": case.case_id,
        "transcript": {"turns": [{"seq": seed.seq, "role": seed.role, "content": seed.content, "tool_call": None}]},
    }


def _fallback_verdict(case_id: str, exc: Exception) -> Verdict:
    return Verdict(
        case_id=case_id,
        tool_name="agentic_threat_detection",
        status="error",
        rationale=f"dict-to-dataclass conversion failed: {type(exc).__name__}",
    )


def _append_jsonl(path: Path, obj: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj) + "\n")


def execute_batch(
    dataset: list[TestCase],
    run_output_dir: Path,
    *,
    agent_timeout_s: float = AGENT_TIMEOUT_S,
    detector_timeout_s: float = DETECTOR_TIMEOUT_S,
    breaker_threshold: int = BREAKER_THRESHOLD,
    api_key: str = "",
    run_test_case_fn: Callable[..., dict] = run_test_case,
    collect_case_evidence_fn: Callable = evidence.collect_case_evidence,
    collect_thin_proxy_log_fn: Callable = evidence.collect_thin_proxy_log,
) -> BatchResult:
    """Drive `dataset` through run_test_case_fn one case at a time (design doc,
    'Orchestrazione del run', Plan 4 decisions 2, 5, 6, 8, 14).

    Never imports detector_adapter or aidr — same boundary orchestrator.py
    already declares."""
    raw_dir = run_output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    verdicts_path = run_output_dir / "verdicts.jsonl"

    cases: list[TestCase] = []
    verdicts: list[Verdict] = []
    consecutive_infra = 0
    last_infra_rationale: Optional[str] = None
    breaker_tripped = False

    for ground_truth in dataset:
        case_id = ground_truth.case_id
        result = run_test_case_fn(
            _agent_input(ground_truth),
            agent_timeout_s=agent_timeout_s,
            detector_timeout_s=detector_timeout_s,
        )
        raw_transcript_dict = result["transcript"]
        raw_verdict_dict = result["verdict"]

        # Persist raw data immediately (decision 6) — before any conversion
        # attempt, so a malformed dict is still inspectable on disk even if
        # verdict_from_dict() below raises on it.
        _append_jsonl(verdicts_path, raw_verdict_dict)
        if raw_transcript_dict is not None:
            (raw_dir / f"{case_id}.transcript.json").write_text(json.dumps(raw_transcript_dict), encoding="utf-8")

        # External evidence, unconditionally, before moving to the next case
        # (decision 5) — evidence.py itself never raises on an unreachable
        # container (Task 3 fix), so this is not wrapped here.
        collect_case_evidence_fn(case_id, SERVICES, run_output_dir)
        collect_thin_proxy_log_fn(case_id, run_output_dir, api_key)

        conversion_failed = False
        try:
            verdict_obj = verdict_from_dict(raw_verdict_dict)
        except Exception as exc:
            conversion_failed = True
            verdict_obj = _fallback_verdict(case_id, exc)

        transcript_obj = None
        if raw_transcript_dict is not None:
            try:
                transcript_obj = transcript_from_dict(raw_transcript_dict)
            except Exception:
                transcript_obj = None

        cases.append(TestCase(
            case_id=case_id,
            label=ground_truth.label,
            technique_target=ground_truth.technique_target,
            rationale=ground_truth.rationale,
            transcript=transcript_obj,
        ))
        verdicts.append(verdict_obj)

        breaker_kind = "conversion" if conversion_failed else raw_verdict_dict.get("error_kind")
        if breaker_kind == "infra":
            consecutive_infra += 1
            last_infra_rationale = raw_verdict_dict.get("rationale")
        else:
            consecutive_infra = 0

        if consecutive_infra >= breaker_threshold:
            breaker_tripped = True
            break

    return BatchResult(
        cases=cases,
        verdicts=verdicts,
        total_count=len(dataset),
        executed_count=len(cases),
        breaker_tripped=breaker_tripped,
        last_infra_rationale=last_infra_rationale,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/toy_agent/test_run_batch.py -v`
Expected: PASS (all 8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/toy_agent/run_batch.py tests/toy_agent/test_run_batch.py
git commit -m "feat: add run_batch.py::execute_batch, the per-case batch loop (Plan 4 decisions 2, 5, 6, 8, 14)"
```

---

## Task 6: `run_batch.py` — CLI wiring (`main()`) and whole-flow tests

**Files:**
- Modify: `src/toy_agent/run_batch.py` (append to the file created in Task 5)
- Test: `tests/toy_agent/test_run_batch.py` (append)

**Interfaces:**
- Consumes: `toy_agent.dataset.load_dataset` (Task 4), `execute_batch`/`BatchResult` (Task 5), `toy_agent.metrics.compute_metrics`, `toy_agent.report.render_report` (existing, unchanged).
- Produces: `main(argv: list[str] | None = None) -> None` (entry point for `python -m toy_agent.run_batch <dataset_dir> <run_output_dir>`), `_setup_notes(result: BatchResult, agent_timeout_s: float, detector_timeout_s: float, breaker_threshold: int) -> str`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/toy_agent/test_run_batch.py`:

```python
import os
from pathlib import Path

import yaml

from toy_agent import run_batch
from toy_agent.run_batch import BatchResult
from toy_agent.schema import Verdict


def _dataset_yaml_entry(case_id: str) -> dict:
    return {
        "case_id": case_id, "label": "benign", "technique_target": None, "rationale": "r",
        "transcript": {"session_id": case_id, "turns": [{"seq": 0, "role": "user", "content": "hi", "tool_call": None}], "stop_reason": None},
    }


def _write_dataset(dataset_dir: Path, case_ids: list[str]) -> None:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    for case_id in case_ids:
        (dataset_dir / f"{case_id}.yaml").write_text(yaml.safe_dump(_dataset_yaml_entry(case_id)), encoding="utf-8")


def test_main_requires_exactly_two_arguments():
    try:
        run_batch.main([])
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert exc.code == 2


def test_main_never_modifies_the_dataset_dir(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])
    before = (dataset_dir / "c1.yaml").read_text(encoding="utf-8")

    def fake_execute_batch(dataset, output_dir, *, api_key=""):
        case = dataset[0]
        return BatchResult(
            cases=[case],
            verdicts=[Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")],
            total_count=1, executed_count=1, breaker_tripped=False,
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    run_batch.main([str(dataset_dir), str(run_output_dir)])

    after = (dataset_dir / "c1.yaml").read_text(encoding="utf-8")
    assert before == after


def test_main_writes_a_report_declaring_operational_parameters(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])

    def fake_execute_batch(dataset, output_dir, *, api_key=""):
        case = dataset[0]
        return BatchResult(
            cases=[case],
            verdicts=[Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")],
            total_count=1, executed_count=1, breaker_tripped=False,
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    run_batch.main([str(dataset_dir), str(run_output_dir)])

    report = (run_output_dir / "report.md").read_text(encoding="utf-8")
    assert f"agent_timeout_s={run_batch.AGENT_TIMEOUT_S}" in report
    assert f"detector_timeout_s={run_batch.DETECTOR_TIMEOUT_S}" in report
    assert f"circuit_breaker_threshold={run_batch.BREAKER_THRESHOLD}" in report


def test_main_declares_a_circuit_breaker_trip_in_the_report(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1", "c2"])

    def fake_execute_batch(dataset, output_dir, *, api_key=""):
        case = dataset[0]
        return BatchResult(
            cases=[case],
            verdicts=[Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="error")],
            total_count=2, executed_count=1, breaker_tripped=True,
            last_infra_rationale="docker compose exec failed to start the agent invocation",
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    run_batch.main([str(dataset_dir), str(run_output_dir)])

    report = (run_output_dir / "report.md").read_text(encoding="utf-8")
    assert "1/2" in report
    assert "docker compose exec failed to start the agent invocation" in report


def test_main_reads_the_detector_api_key_from_the_environment(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])
    monkeypatch.setenv("DETECTOR_OPENROUTER_API_KEY", "sk-test-key")

    captured = {}

    def fake_execute_batch(dataset, output_dir, *, api_key=""):
        captured["api_key"] = api_key
        case = dataset[0]
        return BatchResult(
            cases=[case],
            verdicts=[Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")],
            total_count=1, executed_count=1, breaker_tripped=False,
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    run_batch.main([str(dataset_dir), str(run_output_dir)])

    assert captured["api_key"] == "sk-test-key"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/toy_agent/test_run_batch.py -v -k "main"`
Expected: FAIL — `AttributeError: module 'toy_agent.run_batch' has no attribute 'main'`

- [ ] **Step 3: Write the implementation**

Append to `src/toy_agent/run_batch.py`:

```python
import os
import sys

from .dataset import load_dataset
from .metrics import compute_metrics
from .report import render_report


def _setup_notes(result: BatchResult, agent_timeout_s: float, detector_timeout_s: float, breaker_threshold: int) -> str:
    notes = [
        f"agent_timeout_s={agent_timeout_s}",
        f"detector_timeout_s={detector_timeout_s}",
        f"circuit_breaker_threshold={breaker_threshold}",
    ]
    if result.breaker_tripped:
        notes.insert(
            0,
            f"circuit breaker tripped after {result.executed_count}/{result.total_count} cases executed; "
            f"last infra failure: {result.last_infra_rationale}",
        )
    return " | ".join(notes)


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: python -m toy_agent.run_batch <dataset_dir> <run_output_dir>", file=sys.stderr)
        raise SystemExit(2)

    dataset_dir = Path(args[0])
    run_output_dir = Path(args[1])

    dataset = load_dataset(dataset_dir)
    api_key = os.environ.get("DETECTOR_OPENROUTER_API_KEY", "")
    result = execute_batch(dataset, run_output_dir, api_key=api_key)

    metrics = compute_metrics(result.cases, result.verdicts)
    setup_notes = _setup_notes(result, AGENT_TIMEOUT_S, DETECTOR_TIMEOUT_S, BREAKER_THRESHOLD)
    report = render_report(result.cases, result.verdicts, metrics, setup_notes=setup_notes)
    run_output_dir.mkdir(parents=True, exist_ok=True)
    (run_output_dir / "report.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
```

Move the `import json` / `from dataclasses import dataclass` / etc. block at the top of the file if needed so all imports stay together — the final file should have a single import block at the top (Task 5's imports plus `os`, `sys`, `from .dataset import load_dataset`, `from .metrics import compute_metrics`, `from .report import render_report`), not two separate blocks. `if __name__ == "__main__":` must be the last two lines of the file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/toy_agent/test_run_batch.py -v`
Expected: PASS (all tests from Task 5 and Task 6)

- [ ] **Step 5: Run the full test suite**

Run: `pytest tests/toy_agent -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/toy_agent/run_batch.py tests/toy_agent/test_run_batch.py
git commit -m "feat: add run_batch.py::main, the run_batch CLI entry point (Plan 4 decisions 9, 10, 13)"
```

---

## Task 7: `report.py` — regression test for `transcript=None`

**Files:**
- Test: `tests/toy_agent/test_report.py`

No production code changes — the design doc verified (and this task's test locks in) that `report.py`'s existing code already handles `TestCase.transcript is None` safely, because `_find_misclassified_cases()` excludes `status == "error"` cases before `_format_transcript_excerpt()` ever reads `.transcript`.

**Interfaces:**
- Consumes: `toy_agent.schema.{TestCase, Verdict}` (Task 1), `toy_agent.metrics.compute_metrics`, `toy_agent.report.render_report` (both existing, unchanged).

- [ ] **Step 1: Write the test**

Add to `tests/toy_agent/test_report.py`:

```python
def test_render_report_handles_a_transcript_none_case_without_crashing():
    from toy_agent.schema import TestCase, Verdict

    error_case = TestCase(case_id="c1", label="malicious", technique_target="T0001", rationale="r", transcript=None)
    error_verdict = Verdict(case_id="c1", tool_name="agentic_threat_detection", status="error")

    metrics = compute_metrics([error_case], [error_verdict])
    report = render_report([error_case], [error_verdict], metrics)

    assert "No misclassifications detected." in report
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/toy_agent/test_report.py::test_render_report_handles_a_transcript_none_case_without_crashing -v`
Expected: PASS immediately — this locks in existing behavior, it is not expected to fail first (there is no implementation step; the design doc already verified this against the real code before this plan was written).

If it unexpectedly fails, stop and re-read `src/toy_agent/report.py::_find_misclassified_cases` — it means the design doc's verification (lines 119-125 of the design doc) was wrong, and this is a real bug to fix, not a formality.

- [ ] **Step 3: Run the full report test suite**

Run: `pytest tests/toy_agent/test_report.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/toy_agent/test_report.py
git commit -m "test: lock in render_report()'s existing safe handling of transcript=None (Plan 4 decision 4)"
```

---

## Task 8: Manual end-to-end verification

Not automated (same scope decision already made for `verify_sourcelens.py`, Gap 4) — this is the plan's final gate before Plan 4 is declared complete.

- [ ] **Step 1: Run the full automated test suite one more time**

Run: `pytest tests/toy_agent -v`
Expected: PASS, all tests.

- [ ] **Step 2: Build a minimal manual dataset**

Create a scratch directory (not under `datasets/` — Plan 5 owns that convention, not yet built) with 2-3 YAML files shaped like the fixtures in Task 4/6's tests: one `benign` case with an innocuous seed turn, one `malicious` case with a `technique_target` and a seed turn containing an actual prompt-injection attempt, so the run exercises both branches of the primary metric.

- [ ] **Step 3: Bring up the real stack and run the batch**

```bash
docker compose up --build -d
python -m toy_agent.run_batch <path-to-scratch-dataset> <path-to-scratch-output>
docker compose down
```

- [ ] **Step 4: Inspect the output**

Verify by hand:
- `report.md` exists, contains the two metrics tables and does not contain `None%` or a Python traceback.
- `verdicts.jsonl` has one line per case, `cost_usd` is `null` on every line, `in_tokens`/`out_tokens` are non-null for `status: "ok"` lines.
- `raw/<case_id>.transcript.json` exists for every case that produced a transcript.
- A per-`case_id` evidence subdirectory exists under the output directory with `agent.logs.txt`, `detector.logs.txt`, `egress-proxy.logs.txt`, `agent.diff.txt`, `detector.diff.txt`, `agent.stats.txt`, `detector.stats.txt`, `detector.vendor_proxy.jsonl` — and `detector.vendor_proxy.jsonl` does not contain the real `DETECTOR_OPENROUTER_API_KEY` value in cleartext.
- The scratch dataset directory's files are byte-identical to what they were before the run.

- [ ] **Step 5: Record the outcome**

If everything above holds, Plan 4 is complete — update `docs/design/2026-08-14-toy-agent-gap-tracking.md` (Gap 6) to mark it resolved, referencing this plan and the design doc. If anything fails, treat it as a bug against the specific task that owns the broken guarantee (see the Files section of each task above) rather than patching it ad hoc in Task 8.
