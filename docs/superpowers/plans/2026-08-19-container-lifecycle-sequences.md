# Container Lifecycle & Sequences Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the declarative sequence schema (`open`/`command`/`close`) that closes Gap 14 cluster B/C (container lifecycle as an explicit orchestrator parameter) and Gap 15 (composed scripts vs. the atomic primitive) under one construct, replacing today's implicit "containers are already up externally" assumption with an orchestrator that owns `agent`/`detector`'s lifecycle explicitly.

**Architecture:** A new `sequence.py` module owns the three step types, a fail-fast static validator, the Docker open/close mechanics (auto-healing `open`, real-removal `close`), and `execute_sequence()` — the sequence-aware successor to today's per-case loop inside `execute_batch`. `run_batch.py` becomes a thin generator: it builds the default whole-dataset sequence (`reused` = one open/close around the whole batch; `per-case` = one open/close per case) from a new `--container-lifecycle` flag and delegates to `execute_sequence`. `orchestrator.py`'s `run_test_case` gains a `command_index` parameter so it can mark — never again truncate — the thin-proxy log with each command's position in its enclosing sequence. `detector_adapter/adapter.py` gets one isolated field fix (`call_id`) unrelated to the sequence machinery, bundled here because it's the same "signal that reveals a test session" family (Gap 14, A5).

**Tech Stack:** Python 3.11+, pytest, `docker compose` CLI invoked via `subprocess` (already the pattern in `orchestrator.py`). No new dependencies — `uuid`, `shlex`, `argparse`, `datetime` are all stdlib.

**Spec:** `docs/design/2026-08-19-container-lifecycle-e-sequenze-design.md` (companion: `docs/design/2026-08-14-toy-agent-gap-tracking.md`, Gap 14/Gap 15 sections). Executors should read both this plan and the spec — the spec has the "why" behind constraints this plan states as fact.

## Global Constraints

- Only `agent`/`detector` are part of the sequence vocabulary — `egress-proxy` is never managed by a sequence, it stays up externally (design doc, "Meccanica Docker per open/close").
- `close` is always `docker compose rm -f -s -v <service>` — never a bare `stop` (design doc, same section: `stop` would leave the writable filesystem intact and defeat the guarantee).
- `open` always precedes creation with the same best-effort `rm -f -s -v <service>`, then `docker compose up -d <service>` — auto-healing, so it recovers from any residual state (a crashed prior orchestrator run included), not only the clean path (design doc, "Correzione dopo council: crash dell'orchestratore a metà sequenza").
- Static validation of a sequence always runs before any real Docker/LLM command is issued (design doc, "Validazione statica" — fail fast, zero cost, mirrors `CASE_ID_PATTERN`/`validate_unique_case_ids` in `dataset.py`).
- `counts_toward_metric` is a boolean on a single `command`, never at sequence level; the filter into `compute_metrics` always happens before calling it (in `execute_sequence`/`run_batch.py`), never inside `metrics.py` (design doc, "Meccanismo del filtro").
- The raw verdict/transcript of every `command` — `counts_toward_metric` true or false — is always persisted to disk, regardless of the flag (design doc, "Chiarimento dopo council... semantica di `counts_toward_metric=false`").
- The thin-proxy log is never truncated again — only appended (`>>`) with one JSON marker line `{"marker": true, "case_id": ..., "command_index": ..., "timestamp": ...}` (design doc, "Raccolta prove del thin-proxy log").
- `detector_adapter` never imports `toy_agent` (pre-existing project boundary, Gap 9) — holds for the `call_id` fix in this plan too (it needs only `uuid`, no new import of `toy_agent`).
- Circuit breaker threshold is unchanged: 3 consecutive `error_kind: "infra"` verdicts, now tracked across the whole sequence rather than per container.
- `run_batch.py` assumes a single operator running one sequence at a time — no lock against a concurrent second invocation, or against a human manually running `docker compose` commands mid-batch (council-risk finding, this plan's checkpoint). Already implicit in the project's existing single-audit-at-a-time workflow; not a new restriction, but now worth naming because `open`/`close` make container removal an active, automatic side effect instead of a manual one.

---

## Task 1: `sequence.py` — step types and the static validator

**Files:**
- Create: `src/toy_agent/sequence.py`
- Test: `tests/toy_agent/test_sequence.py`

**Interfaces:**
- Produces: `OpenStep(containers: tuple[str, ...])`, `CommandStep(case_id: str, counts_toward_metric: bool)`, `CloseStep(containers: tuple[str, ...])` (all frozen dataclasses), `SequenceStep = Union[OpenStep, CommandStep, CloseStep]`, `KNOWN_CONTAINERS = ("agent", "detector")`, `validate_sequence(steps: list[SequenceStep], known_case_ids: set[str]) -> None` (raises `ValueError` on any of the 5 static failure modes, `TypeError` on an unknown step type; returns `None` silently on a valid sequence).

- [ ] **Step 1: Write the failing tests**

Create `tests/toy_agent/test_sequence.py`:

```python
import pytest

from toy_agent.sequence import CloseStep, CommandStep, OpenStep, validate_sequence


def test_valid_reused_sequence_passes():
    steps = [
        OpenStep(containers=("agent", "detector")),
        CommandStep(case_id="c1", counts_toward_metric=True),
        CommandStep(case_id="c2", counts_toward_metric=True),
        CloseStep(containers=("agent", "detector")),
    ]
    validate_sequence(steps, known_case_ids={"c1", "c2"})  # must not raise


def test_reopening_an_already_open_container_is_rejected():
    steps = [
        OpenStep(containers=("agent",)),
        OpenStep(containers=("agent", "detector")),
    ]
    with pytest.raises(ValueError, match="re-opens already-open"):
        validate_sequence(steps, known_case_ids=set())


def test_command_on_a_container_that_is_not_open_is_rejected():
    steps = [OpenStep(containers=("agent",)), CommandStep(case_id="c1", counts_toward_metric=True)]
    with pytest.raises(ValueError, match="requires containers not open"):
        validate_sequence(steps, known_case_ids={"c1"})


def test_closing_a_container_that_is_not_open_is_rejected():
    steps = [OpenStep(containers=("agent",)), CloseStep(containers=("agent", "detector"))]
    with pytest.raises(ValueError, match="closes containers not open"):
        validate_sequence(steps, known_case_ids=set())


def test_sequence_ending_with_open_containers_is_rejected():
    steps = [OpenStep(containers=("agent", "detector"))]
    with pytest.raises(ValueError, match="still open"):
        validate_sequence(steps, known_case_ids=set())


def test_command_referencing_an_unknown_case_id_is_rejected():
    steps = [OpenStep(containers=("agent", "detector")), CommandStep(case_id="ghost", counts_toward_metric=True)]
    with pytest.raises(ValueError, match="unknown case_id"):
        validate_sequence(steps, known_case_ids={"c1"})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/toy_agent/test_sequence.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'toy_agent.sequence'`

- [ ] **Step 3: Write the implementation**

Create `src/toy_agent/sequence.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Union

# Only agent/detector are part of the sequence vocabulary — egress-proxy is
# shared infrastructure, never managed by a sequence (design doc, "Meccanica
# Docker per open/close").
KNOWN_CONTAINERS = ("agent", "detector")


@dataclass(frozen=True)
class OpenStep:
    containers: tuple[str, ...]


@dataclass(frozen=True)
class CommandStep:
    case_id: str
    counts_toward_metric: bool


@dataclass(frozen=True)
class CloseStep:
    containers: tuple[str, ...]


SequenceStep = Union[OpenStep, CommandStep, CloseStep]


def validate_sequence(steps: list[SequenceStep], known_case_ids: set[str]) -> None:
    """Fail-fast static validation (design doc, 'Validazione statica') — a
    scan over `steps` tracking which containers are open, before any Docker
    or LLM call is issued. Mirrors CASE_ID_PATTERN/validate_unique_case_ids
    in dataset.py: cheap, structural checks first, never a wasted real call
    on a malformed sequence."""
    open_containers: set[str] = set()
    for step in steps:
        if isinstance(step, OpenStep):
            already_open = open_containers & set(step.containers)
            if already_open:
                raise ValueError(f"open step re-opens already-open containers: {sorted(already_open)}")
            open_containers |= set(step.containers)
        elif isinstance(step, CommandStep):
            missing = set(KNOWN_CONTAINERS) - open_containers
            if missing:
                raise ValueError(
                    f"command step {step.case_id!r} requires containers not open: {sorted(missing)}"
                )
            if step.case_id not in known_case_ids:
                raise ValueError(f"command step references unknown case_id: {step.case_id!r}")
        elif isinstance(step, CloseStep):
            not_open = set(step.containers) - open_containers
            if not_open:
                raise ValueError(f"close step closes containers not open: {sorted(not_open)}")
            open_containers -= set(step.containers)
        else:
            raise TypeError(f"unknown sequence step type: {type(step).__name__}")
    if open_containers:
        raise ValueError(f"sequence ends with containers still open: {sorted(open_containers)}")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/toy_agent/test_sequence.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/toy_agent/sequence.py tests/toy_agent/test_sequence.py
git commit -m "feat: add sequence step types and static validator (Gap 14/15)"
```

---

## Task 2: `orchestrator.py` — mark the thin-proxy log instead of truncating it

**Files:**
- Modify: `src/toy_agent/orchestrator.py:1-13,88-104`
- Test: `tests/toy_agent/test_orchestrator.py` (full rewrite of the truncate-related assertions)

**Interfaces:**
- Consumes: nothing new.
- Produces: `run_test_case(test_case: dict, *, command_index: int, agent_timeout_s: float = 120.0, detector_timeout_s: float = 180.0, run_command: CommandRunner = default_command_runner) -> dict` — same return contract as today (`{"transcript": ..., "verdict": ...}`), one new **required** keyword-only parameter `command_index`. Every caller of `run_test_case` (Task 4 onward) must supply it.

- [ ] **Step 1: Write the failing tests**

Replace `tests/toy_agent/test_orchestrator.py` in full:

```python
import json
import shlex
from datetime import datetime

from toy_agent.orchestrator import CommandResult, run_test_case

_TEST_CASE = {
    "case_id": "case_001",
    "transcript": {"session_id": "case_001", "turns": [{"seq": 0, "role": "user", "content": "hi", "tool_call": None}], "stop_reason": None},
    "label": "benign", "technique_target": None, "rationale": "smoke test",
}

_TRANSCRIPT_JSON = json.dumps({"session_id": "case_001", "turns": [], "stop_reason": "completed"}).encode()
_VERDICT_JSON = json.dumps({"case_id": "case_001", "tool_name": "x", "status": "ok", "label": "benign"}).encode()
_MARKER_OK = CommandResult(returncode=0, stdout=b"", stderr=b"")  # the thin-proxy log marker call, always issued right before the detector invocation


class ScriptedRunner:
    """Returns one scripted CommandResult per call, in order — mirrors the
    FakeModelClient pattern already used in tests/toy_agent/test_agent_loop.py."""

    def __init__(self, script: list[CommandResult]):
        self._script = list(script)
        self.calls: list[tuple[list[str], bytes, float]] = []

    def __call__(self, cmd, stdin_bytes, timeout_s):
        self.calls.append((cmd, stdin_bytes, timeout_s))
        if not self._script:
            raise AssertionError("ScriptedRunner script exhausted")
        return self._script.pop(0)


def test_happy_path_returns_the_transcript_and_the_detector_verdict():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        CommandResult(returncode=0, stdout=_VERDICT_JSON, stderr=b""),
    ])
    result = run_test_case(_TEST_CASE, command_index=0, run_command=runner)
    assert result["transcript"] == json.loads(_TRANSCRIPT_JSON)
    assert result["verdict"] == json.loads(_VERDICT_JSON)
    assert len(runner.calls) == 3
    assert runner.calls[0][0][:4] == ["docker", "compose", "exec", "-T"]
    assert "agent" in runner.calls[0][0]
    assert "detector" in runner.calls[1][0] and "sh" in runner.calls[1][0]  # the marker call
    assert "detector" in runner.calls[2][0]
    assert runner.calls[2][1] == _TRANSCRIPT_JSON  # agent's stdout piped straight into detector's stdin


def test_thin_proxy_log_is_appended_with_a_json_marker_never_truncated():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        CommandResult(returncode=0, stdout=_VERDICT_JSON, stderr=b""),
    ])
    run_test_case(_TEST_CASE, command_index=7, run_command=runner)

    marker_cmd = runner.calls[1][0]
    shell_arg = marker_cmd[-1]
    assert ">>" in shell_arg
    assert shell_arg.count(">") == 2  # only the ">>" redirection — never a lone truncating ">"

    tokens = shlex.split(shell_arg)
    marker_json = json.loads(tokens[1])
    assert marker_json["marker"] is True
    assert marker_json["case_id"] == "case_001"
    assert marker_json["command_index"] == 7
    datetime.fromisoformat(marker_json["timestamp"])  # must be a valid ISO 8601 timestamp


def test_verdict_case_id_is_overwritten_with_the_true_case_id():
    # Gap 14, A1: session_id is now an opaque per-invocation UUID (never
    # case_id), so the detector's echoed case_id must never be trusted —
    # the orchestrator already knows the real case_id independently.
    detector_verdict = json.dumps(
        {"case_id": "some-opaque-uuid-the-detector-echoed-back", "tool_name": "x", "status": "ok", "label": "benign"}
    ).encode()
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        CommandResult(returncode=0, stdout=detector_verdict, stderr=b""),
    ])
    result = run_test_case(_TEST_CASE, command_index=0, run_command=runner)
    assert result["verdict"]["case_id"] == "case_001"


def test_agent_failed_to_start_is_classified_as_infra():
    runner = ScriptedRunner([CommandResult(returncode=-1, stdout=b"", stderr=b"", failed_to_start=True)])
    result = run_test_case(_TEST_CASE, command_index=0, run_command=runner)
    assert result["transcript"] is None
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "infra"
    assert result["verdict"]["label"] is None
    assert len(runner.calls) == 1  # never attempted the marker or detector invocation


def test_agent_nonzero_exit_is_classified_as_application():
    runner = ScriptedRunner([CommandResult(returncode=1, stdout=b"", stderr=b"bad seed turn")])
    result = run_test_case(_TEST_CASE, command_index=0, run_command=runner)
    assert result["transcript"] is None
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"
    assert "bad seed turn" in result["verdict"]["rationale"]


def test_detector_timeout_is_classified_as_infra_and_triggers_both_cleanup_calls():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        CommandResult(returncode=-1, stdout=b"", stderr=b"", timed_out=True),
        CommandResult(returncode=0, stdout=b"", stderr=b""),  # pkill detector_adapter.evaluate_case — last-resort fallback
        CommandResult(returncode=0, stdout=b"", stderr=b""),  # pkill aidr/providers — last-resort fallback
    ])
    result = run_test_case(_TEST_CASE, command_index=0, run_command=runner)
    assert result["transcript"] == json.loads(_TRANSCRIPT_JSON)
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "infra"
    assert len(runner.calls) == 5
    assert "detector_adapter.evaluate_case" in runner.calls[3][0]
    assert "aidr/providers" in runner.calls[4][0]


def test_detector_nonzero_exit_with_internal_timeout_in_stderr_triggers_both_cleanup_calls():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        CommandResult(returncode=1, stdout=b"", stderr=b"evaluate_case failed: TimeoutError"),
        CommandResult(returncode=0, stdout=b"", stderr=b""),  # pkill detector_adapter.evaluate_case — fallback for a hang during adapter construction
        CommandResult(returncode=0, stdout=b"", stderr=b""),  # pkill aidr/providers — same fallback
    ])
    result = run_test_case(_TEST_CASE, command_index=0, run_command=runner)
    assert result["transcript"] == json.loads(_TRANSCRIPT_JSON)
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"  # process exited cleanly — only the cleanup calls fire, no reclassification to infra
    assert len(runner.calls) == 5
    assert "detector_adapter.evaluate_case" in runner.calls[3][0]
    assert "aidr/providers" in runner.calls[4][0]


def test_detector_nonzero_exit_without_timeout_in_stderr_skips_cleanup_calls():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        CommandResult(returncode=1, stdout=b"", stderr=b"evaluate_case failed: ValueError"),
    ])
    result = run_test_case(_TEST_CASE, command_index=0, run_command=runner)
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"
    assert len(runner.calls) == 3  # no fallback pkill calls — ordinary application error, no internal-deadline signal in stderr


def test_detector_malformed_stdout_despite_exit_zero_is_classified_as_application():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        CommandResult(returncode=0, stdout=b"noise before json\n" + _VERDICT_JSON, stderr=b""),
    ])
    result = run_test_case(_TEST_CASE, command_index=0, run_command=runner)
    assert result["transcript"] == json.loads(_TRANSCRIPT_JSON)
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"


def test_agent_malformed_stdout_despite_exit_zero_never_reaches_detector():
    runner = ScriptedRunner([CommandResult(returncode=0, stdout=b"not json", stderr=b"")])
    result = run_test_case(_TEST_CASE, command_index=0, run_command=runner)
    assert result["transcript"] is None
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"
    assert len(runner.calls) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/toy_agent/test_orchestrator.py -v`
Expected: FAIL — `TypeError: run_test_case() missing 1 required keyword-only argument: 'command_index'` on every test.

- [ ] **Step 3: Modify the implementation**

In `src/toy_agent/orchestrator.py`, change the imports at the top:

```python
from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
```

Change the `run_test_case` signature (add `command_index`):

```python
def run_test_case(
    test_case: dict,
    *,
    command_index: int,
    agent_timeout_s: float = 120.0,
    detector_timeout_s: float = 180.0,
    run_command: CommandRunner = default_command_runner,
) -> dict:
```

Replace the truncation block (currently `run_command(["docker", "compose", "exec", "-T", "detector", "sh", "-c", f"> {THIN_PROXY_LOG_PATH}"], b"", 10.0,)` plus its comment) with:

```python
    # Append-only marker instead of truncating (design doc, Gap 14/15,
    # 'Raccolta prove del thin-proxy log'): the old truncation existed only
    # for per-case attribution (vendor_proxy runs as one long-lived process
    # for the detector container's whole life), never a security mechanism —
    # deleting log content in the observed container proves nothing about
    # what the container itself retains. The marker turns the log into a
    # complete, continuous corpus for the whole sequence instead: nothing is
    # ever lost, and command_index (this command's position in the calling
    # sequence, supplied by execute_sequence) plus case_id let a reader
    # attribute every line without needing to isolate files per case.
    marker = json.dumps({
        "marker": True,
        "case_id": case_id,
        "command_index": command_index,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    run_command(
        ["docker", "compose", "exec", "-T", "detector", "sh", "-c", f"echo {shlex.quote(marker)} >> {THIN_PROXY_LOG_PATH}"],
        b"",
        10.0,
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/toy_agent/test_orchestrator.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Run the full test suite to catch any missed call site**

Run: `pytest tests/toy_agent tests/detector_adapter -v`
Expected: Only `tests/toy_agent/test_run_batch.py` fails at this point (`run_test_case_fn` doubles there don't yet accept `command_index` — fixed in Task 6). No other file should fail.

- [ ] **Step 6: Commit**

```bash
git add src/toy_agent/orchestrator.py tests/toy_agent/test_orchestrator.py
git commit -m "feat: mark thin-proxy log instead of truncating it, add command_index (Gap 14/15)"
```

---

## Task 3: `sequence.py` — Docker open/close mechanics

**Files:**
- Modify: `src/toy_agent/sequence.py`
- Test: `tests/toy_agent/test_sequence.py`

**Interfaces:**
- Consumes: `toy_agent.orchestrator.CommandRunner`, `CommandResult`.
- Produces: `OPEN_CLOSE_TIMEOUT_S: float`, `_open_container(service: str, run_command: CommandRunner) -> None`, `_close_container(service: str, run_command: CommandRunner) -> None`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/toy_agent/test_sequence.py`:

```python
from toy_agent.orchestrator import CommandResult
from toy_agent.sequence import _close_container, _open_container


class RecordingCommandRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, stdin_bytes, timeout_s):
        self.calls.append(cmd)
        return CommandResult(returncode=0, stdout=b"", stderr=b"")


def test_open_container_removes_before_recreating():
    runner = RecordingCommandRunner()
    _open_container("detector", runner)
    assert runner.calls[0] == ["docker", "compose", "rm", "-f", "-s", "-v", "detector"]
    assert runner.calls[1] == ["docker", "compose", "up", "-d", "detector"]
    assert len(runner.calls) == 2


def test_close_container_removes_never_just_stops():
    runner = RecordingCommandRunner()
    _close_container("agent", runner)
    assert runner.calls == [["docker", "compose", "rm", "-f", "-s", "-v", "agent"]]
    assert not any("stop" in call for call in runner.calls)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/toy_agent/test_sequence.py -v`
Expected: FAIL — `ImportError: cannot import name '_open_container' from 'toy_agent.sequence'`

- [ ] **Step 3: Write the implementation**

Add to `src/toy_agent/sequence.py`, after the type definitions and before/after `validate_sequence`:

```python
from .orchestrator import CommandRunner, default_command_runner

OPEN_CLOSE_TIMEOUT_S = 30.0


def _open_container(service: str, run_command: CommandRunner) -> None:
    """Auto-healing open (design doc, 'Meccanica Docker per open/close';
    council-risk finding, crash dell'orchestratore a metà sequenza): the
    best-effort rm before up recovers from any residual state regardless of
    what happened before it — a crashed prior run included, not only the
    path where everything went cleanly."""
    run_command(["docker", "compose", "rm", "-f", "-s", "-v", service], b"", OPEN_CLOSE_TIMEOUT_S)
    run_command(["docker", "compose", "up", "-d", service], b"", OPEN_CLOSE_TIMEOUT_S)


def _close_container(service: str, run_command: CommandRunner) -> None:
    """Real removal, never a bare stop (design doc, 'Meccanica Docker per
    open/close'): rm -f -s -v deletes the container's writable layer by
    Docker's own command contract — that contract is the guarantee, not an
    empirical check of what's left on disk.

    The CommandResult's returncode is not checked here — same best-effort
    discipline orchestrator.py already applies to its own cleanup calls
    (the pkill fallbacks). A failed rm/up is not silently hidden forever: a
    container that's still broken will make the next docker compose exec in
    the sequence fail too, which run_test_case classifies as an infra error
    and the circuit breaker will trip on within a bounded number of
    commands (council-risk finding, this plan's checkpoint)."""
    run_command(["docker", "compose", "rm", "-f", "-s", "-v", service], b"", OPEN_CLOSE_TIMEOUT_S)
```

(Add the `from .orchestrator import ...` line to the existing `from __future__ import annotations` import block at the top of the file, not as a second copy.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/toy_agent/test_sequence.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/toy_agent/sequence.py tests/toy_agent/test_sequence.py
git commit -m "feat: add auto-healing open / real-removal close Docker mechanics"
```

---

## Task 4: `sequence.py` — `execute_sequence()` happy path, persistence, and the `counts_toward_metric` split

**Files:**
- Modify: `src/toy_agent/sequence.py`
- Test: `tests/toy_agent/test_sequence.py`

**Interfaces:**
- Consumes: Task 1's `OpenStep`/`CommandStep`/`CloseStep`/`validate_sequence`/`KNOWN_CONTAINERS`; Task 2's `run_test_case(..., command_index=...)`; Task 3's `_open_container`/`_close_container`; `toy_agent.evidence.{collect_case_evidence, collect_thin_proxy_log}`; `toy_agent.serialization.{transcript_from_dict, verdict_from_dict}`; `toy_agent.schema.{TestCase, Verdict}`.
- Produces: `BatchResult` dataclass — `cases: list[TestCase]`, `verdicts: list[Verdict]`, `metric_cases: list[TestCase]`, `metric_verdicts: list[Verdict]`, `total_count: int`, `executed_count: int`, `breaker_tripped: bool`, `last_infra_rationale: Optional[str] = None`, `transcript_conversion_failure_count: int = 0`, `verdict_conversion_failure_count: int = 0`. `execute_sequence(steps: list[SequenceStep], dataset_by_case_id: dict[str, TestCase], run_output_dir: Path, *, agent_timeout_s: float = 120.0, detector_timeout_s: float = 180.0, breaker_threshold: int = 3, api_key: str = "", run_test_case_fn: Callable[..., dict] = run_test_case, collect_case_evidence_fn: Callable = evidence.collect_case_evidence, collect_thin_proxy_log_fn: Callable = evidence.collect_thin_proxy_log, run_command: CommandRunner = default_command_runner) -> BatchResult`.

- [ ] **Step 1: Write the failing tests**

First, replace the import block at the top of `tests/toy_agent/test_sequence.py` (consolidating what Tasks 1 and 3 added into one block, plus what this task needs) with:

```python
import json

import pytest

from toy_agent.orchestrator import CommandResult
from toy_agent.schema import TestCase, Transcript, Turn
from toy_agent.sequence import (
    CloseStep,
    CommandStep,
    OpenStep,
    _close_container,
    _open_container,
    execute_sequence,
    validate_sequence,
)
```

This consolidated block replaces the inline `from toy_agent.orchestrator import CommandResult` / `from toy_agent.sequence import _close_container, _open_container` lines Task 3 added in the middle of the file (in front of `class RecordingCommandRunner`) — delete those two now-redundant lines from that spot, since the same names are imported at the top instead.

Then add to the bottom of `tests/toy_agent/test_sequence.py`:

```python
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


class ScriptedRunTestCase:
    def __init__(self, script):
        self._script = list(script)
        self.calls = []

    def __call__(self, test_case, *, command_index, agent_timeout_s, detector_timeout_s):
        self.calls.append((test_case, command_index))
        if not self._script:
            raise AssertionError("script exhausted")
        result = self._script.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class NoOpCommandRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, stdin_bytes, timeout_s):
        self.calls.append(cmd)
        return CommandResult(returncode=0, stdout=b"", stderr=b"")


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


def _reused_sequence(case_ids):
    return (
        [OpenStep(containers=("agent", "detector"))]
        + [CommandStep(case_id=cid, counts_toward_metric=True) for cid in case_ids]
        + [CloseStep(containers=("agent", "detector"))]
    )


def test_command_step_reaches_run_test_case_with_its_position_in_the_sequence(tmp_path):
    dataset = {"c1": _ground_truth("c1")}
    steps = _reused_sequence(["c1"])
    runner = ScriptedRunTestCase([_ok_result("c1")])

    execute_sequence(steps, dataset, tmp_path, run_test_case_fn=runner,
                      collect_case_evidence_fn=RecordingEvidenceCollector(),
                      collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                      run_command=NoOpCommandRunner())

    sent_case, command_index = runner.calls[0]
    assert sent_case["case_id"] == "c1"
    assert command_index == 1  # steps[0] is the OpenStep, steps[1] is this command


def test_open_and_close_are_issued_around_the_commands(tmp_path):
    dataset = {"c1": _ground_truth("c1")}
    steps = _reused_sequence(["c1"])
    runner = ScriptedRunTestCase([_ok_result("c1")])
    command_runner = NoOpCommandRunner()

    execute_sequence(steps, dataset, tmp_path, run_test_case_fn=runner,
                      collect_case_evidence_fn=RecordingEvidenceCollector(),
                      collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                      run_command=command_runner)

    assert command_runner.calls[0] == ["docker", "compose", "rm", "-f", "-s", "-v", "agent"]
    assert command_runner.calls[-1][:6] == ["docker", "compose", "rm", "-f", "-s", "-v"]


def test_counts_toward_metric_false_is_excluded_from_the_metric_lists_but_kept_in_cases(tmp_path):
    dataset = {"c1": _ground_truth("c1"), "c2": _ground_truth("c2")}
    steps = [
        OpenStep(containers=("agent", "detector")),
        CommandStep(case_id="c1", counts_toward_metric=False),
        CommandStep(case_id="c2", counts_toward_metric=True),
        CloseStep(containers=("agent", "detector")),
    ]
    runner = ScriptedRunTestCase([_ok_result("c1"), _ok_result("c2")])

    result = execute_sequence(steps, dataset, tmp_path, run_test_case_fn=runner,
                               collect_case_evidence_fn=RecordingEvidenceCollector(),
                               collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                               run_command=NoOpCommandRunner())

    assert [c.case_id for c in result.cases] == ["c1", "c2"]
    assert [c.case_id for c in result.metric_cases] == ["c2"]
    assert [v.case_id for v in result.verdicts] == ["c1", "c2"]
    assert [v.case_id for v in result.metric_verdicts] == ["c2"]
    # c1's raw verdict is still persisted to disk even though excluded from metrics
    lines = (tmp_path / "verdicts.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert json.loads(lines[0])["case_id"] == "c1"


def test_circuit_breaker_trips_after_three_consecutive_infra_failures(tmp_path):
    dataset = {f"c{i}": _ground_truth(f"c{i}") for i in range(1, 5)}
    steps = _reused_sequence([f"c{i}" for i in range(1, 5)])
    runner = ScriptedRunTestCase([_infra_result("c1"), _infra_result("c2"), _infra_result("c3")])

    result = execute_sequence(steps, dataset, tmp_path, run_test_case_fn=runner,
                               collect_case_evidence_fn=RecordingEvidenceCollector(),
                               collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                               run_command=NoOpCommandRunner())

    assert len(runner.calls) == 3  # c4 never attempted
    assert result.breaker_tripped is True
    assert result.executed_count == 3
    assert result.total_count == 4
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/toy_agent/test_sequence.py -v`
Expected: FAIL — `ImportError: cannot import name 'execute_sequence' from 'toy_agent.sequence'`

- [ ] **Step 3: Write the implementation**

Add to `src/toy_agent/sequence.py`. First, extend the imports at the top of the file to:

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Union

from . import evidence
from .orchestrator import CommandRunner, default_command_runner, run_test_case
from .schema import TestCase, Verdict
from .serialization import transcript_from_dict, verdict_from_dict
```

Then append:

```python
@dataclass
class BatchResult:
    cases: list[TestCase]
    verdicts: list[Verdict]
    total_count: int
    executed_count: int
    breaker_tripped: bool
    last_infra_rationale: Optional[str] = None
    transcript_conversion_failure_count: int = 0
    verdict_conversion_failure_count: int = 0
    metric_cases: list[TestCase] = field(default_factory=list)
    metric_verdicts: list[Verdict] = field(default_factory=list)


def _agent_input(case: TestCase) -> dict:
    """Reduced dict sent to run_test_case(): only case_id and the seed turn's
    content — never label/technique_target/rationale (design doc decision 2,
    Plan 4)."""
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


def execute_sequence(
    steps: list[SequenceStep],
    dataset_by_case_id: dict[str, TestCase],
    run_output_dir: Path,
    *,
    agent_timeout_s: float = 120.0,
    detector_timeout_s: float = 180.0,
    breaker_threshold: int = 3,
    api_key: str = "",
    run_test_case_fn: Callable[..., dict] = run_test_case,
    collect_case_evidence_fn: Callable = evidence.collect_case_evidence,
    collect_thin_proxy_log_fn: Callable = evidence.collect_thin_proxy_log,
    run_command: CommandRunner = default_command_runner,
) -> BatchResult:
    """Drive `steps` through open/command/close (design doc, 'Esecuzione') —
    the sequence-aware core that execute_batch (run_batch.py) generates its
    default whole-dataset sequence on top of. Never imports detector_adapter
    or aidr, same boundary run_test_case already declares."""
    validate_sequence(steps, set(dataset_by_case_id.keys()))

    raw_dir = run_output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    verdicts_path = run_output_dir / "verdicts.jsonl"
    verdicts_path.write_text("", encoding="utf-8")

    cases: list[TestCase] = []
    verdicts: list[Verdict] = []
    metric_cases: list[TestCase] = []
    metric_verdicts: list[Verdict] = []
    open_containers: set[str] = set()
    consecutive_infra = 0
    last_infra_rationale: Optional[str] = None
    breaker_tripped = False
    transcript_conversion_failure_count = 0
    verdict_conversion_failure_count = 0
    total_count = sum(1 for step in steps if isinstance(step, CommandStep))

    for step_index, step in enumerate(steps):
        if isinstance(step, OpenStep):
            for service in step.containers:
                _open_container(service, run_command)
                open_containers.add(service)
            continue

        if isinstance(step, CloseStep):
            for service in step.containers:
                _close_container(service, run_command)
                open_containers.discard(service)
            continue

        ground_truth = dataset_by_case_id[step.case_id]
        case_id = ground_truth.case_id
        result = run_test_case_fn(
            _agent_input(ground_truth),
            command_index=step_index,
            agent_timeout_s=agent_timeout_s,
            detector_timeout_s=detector_timeout_s,
        )
        raw_transcript_dict = result["transcript"]
        raw_verdict_dict = result["verdict"]

        # Persist raw data immediately, before any conversion attempt — a
        # malformed dict stays inspectable on disk even if verdict_from_dict()
        # below raises on it (Plan 4 decision 6, unchanged).
        _append_jsonl(verdicts_path, raw_verdict_dict)
        if raw_transcript_dict is not None:
            (raw_dir / f"{case_id}.transcript.json").write_text(json.dumps(raw_transcript_dict), encoding="utf-8")

        # External evidence unconditionally, before moving to the next step
        # (Plan 4 decision 5) — evidence.py never raises on an unreachable
        # container.
        collect_case_evidence_fn(case_id, KNOWN_CONTAINERS, run_output_dir)
        collect_thin_proxy_log_fn(case_id, run_output_dir, api_key)

        conversion_failed = False
        try:
            verdict_obj = verdict_from_dict(raw_verdict_dict)
        except Exception as exc:
            conversion_failed = True
            verdict_conversion_failure_count += 1
            verdict_obj = _fallback_verdict(case_id, exc)

        transcript_obj = None
        if raw_transcript_dict is not None:
            try:
                transcript_obj = transcript_from_dict(raw_transcript_dict)
            except Exception:
                transcript_obj = None
                transcript_conversion_failure_count += 1

        case_obj = TestCase(
            case_id=case_id,
            label=ground_truth.label,
            technique_target=ground_truth.technique_target,
            rationale=ground_truth.rationale,
            transcript=transcript_obj,
        )
        cases.append(case_obj)
        verdicts.append(verdict_obj)
        if step.counts_toward_metric:
            metric_cases.append(case_obj)
            metric_verdicts.append(verdict_obj)

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
        metric_cases=metric_cases,
        metric_verdicts=metric_verdicts,
        total_count=total_count,
        executed_count=len(cases),
        breaker_tripped=breaker_tripped,
        last_infra_rationale=last_infra_rationale,
        transcript_conversion_failure_count=transcript_conversion_failure_count,
        verdict_conversion_failure_count=verdict_conversion_failure_count,
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/toy_agent/test_sequence.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
git add src/toy_agent/sequence.py tests/toy_agent/test_sequence.py
git commit -m "feat: execute_sequence happy path with counts_toward_metric split"
```

---

## Task 5: `sequence.py` — close every still-open container on early exit, whether a circuit-breaker trip or an uncaught exception

**Files:**
- Modify: `src/toy_agent/sequence.py`
- Test: `tests/toy_agent/test_sequence.py`

**Interfaces:**
- No signature change — `execute_sequence` keeps the same interface as Task 4; this task only changes behavior on the early-exit paths.

**Note (council-risk finding, this plan's checkpoint):** the original version of this task only handled the circuit-breaker trip. But `execute_sequence` doesn't wrap `run_test_case_fn`/evidence collection in a `try` at all (mirroring the pre-existing `execute_batch`, per `test_per_case_data_is_persisted_immediately_even_if_a_later_case_raises`) — under the *old* `execute_batch` that was harmless, because containers were assumed externally managed. Under this plan, `run_batch.py` exclusively owns Docker lifecycle (Task 6), so an uncaught exception from `run_test_case_fn` now has a different consequence: it leaves `agent`/`detector` running with no cleanup attempt at all. The fix below closes both paths with one mechanism — a `try/finally` around the loop — rather than only checking `breaker_tripped` after a normal (non-exceptional) loop exit.

- [ ] **Step 1: Write the failing tests**

Add to `tests/toy_agent/test_sequence.py`:

```python
def test_breaker_trip_closes_every_still_open_container_before_returning(tmp_path):
    dataset = {f"c{i}": _ground_truth(f"c{i}") for i in range(1, 5)}
    steps = _reused_sequence([f"c{i}" for i in range(1, 5)])
    runner = ScriptedRunTestCase([_infra_result("c1"), _infra_result("c2"), _infra_result("c3")])
    command_runner = NoOpCommandRunner()

    result = execute_sequence(steps, dataset, tmp_path, run_test_case_fn=runner,
                               collect_case_evidence_fn=RecordingEvidenceCollector(),
                               collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                               run_command=command_runner)

    assert result.breaker_tripped is True
    # The written sequence's own CloseStep is never reached (the loop broke
    # before it) — these rm calls only exist because early exit closes
    # whatever is still open.
    rm_calls = [c for c in command_runner.calls if c[:6] == ["docker", "compose", "rm", "-f", "-s", "-v"]]
    assert len(rm_calls) == 4  # 2 auto-heal rm's from the initial open + 2 explicit closes on trip
    assert {c[6] for c in rm_calls[2:]} == {"agent", "detector"}


def test_an_uncaught_exception_from_run_test_case_still_closes_every_open_container(tmp_path):
    dataset = {"c1": _ground_truth("c1"), "c2": _ground_truth("c2")}
    steps = _reused_sequence(["c1", "c2"])
    runner = ScriptedRunTestCase([_ok_result("c1"), RuntimeError("simulated crash")])
    command_runner = NoOpCommandRunner()

    try:
        execute_sequence(steps, dataset, tmp_path, run_test_case_fn=runner,
                          collect_case_evidence_fn=RecordingEvidenceCollector(),
                          collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                          run_command=command_runner)
        assert False, "expected RuntimeError to propagate"
    except RuntimeError:
        pass

    rm_calls = [c for c in command_runner.calls if c[:6] == ["docker", "compose", "rm", "-f", "-s", "-v"]]
    assert len(rm_calls) == 4  # 2 auto-heal rm's from open + 2 explicit closes despite the exception
    assert {c[6] for c in rm_calls[2:]} == {"agent", "detector"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/toy_agent/test_sequence.py -v`
Expected: `test_breaker_trip_closes_every_still_open_container_before_returning` FAILs with `assert 2 == 4` (only the initial `open`'s 2 `rm` calls exist); `test_an_uncaught_exception_from_run_test_case_still_closes_every_open_container` FAILs the same way (the `RuntimeError` propagates correctly already, but no `rm` calls follow it).

- [ ] **Step 3: Modify the implementation**

Replace the entire `execute_sequence` function in `src/toy_agent/sequence.py` (written in Task 4) with:

```python
def execute_sequence(
    steps: list[SequenceStep],
    dataset_by_case_id: dict[str, TestCase],
    run_output_dir: Path,
    *,
    agent_timeout_s: float = 120.0,
    detector_timeout_s: float = 180.0,
    breaker_threshold: int = 3,
    api_key: str = "",
    run_test_case_fn: Callable[..., dict] = run_test_case,
    collect_case_evidence_fn: Callable = evidence.collect_case_evidence,
    collect_thin_proxy_log_fn: Callable = evidence.collect_thin_proxy_log,
    run_command: CommandRunner = default_command_runner,
) -> BatchResult:
    """Drive `steps` through open/command/close (design doc, 'Esecuzione') —
    the sequence-aware core that execute_batch (run_batch.py) generates its
    default whole-dataset sequence on top of. Never imports detector_adapter
    or aidr, same boundary run_test_case already declares."""
    validate_sequence(steps, set(dataset_by_case_id.keys()))

    raw_dir = run_output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    verdicts_path = run_output_dir / "verdicts.jsonl"
    verdicts_path.write_text("", encoding="utf-8")

    cases: list[TestCase] = []
    verdicts: list[Verdict] = []
    metric_cases: list[TestCase] = []
    metric_verdicts: list[Verdict] = []
    open_containers: set[str] = set()
    consecutive_infra = 0
    last_infra_rationale: Optional[str] = None
    breaker_tripped = False
    transcript_conversion_failure_count = 0
    verdict_conversion_failure_count = 0
    total_count = sum(1 for step in steps if isinstance(step, CommandStep))

    try:
        for step_index, step in enumerate(steps):
            if isinstance(step, OpenStep):
                for service in step.containers:
                    _open_container(service, run_command)
                    open_containers.add(service)
                continue

            if isinstance(step, CloseStep):
                for service in step.containers:
                    _close_container(service, run_command)
                    open_containers.discard(service)
                continue

            ground_truth = dataset_by_case_id[step.case_id]
            case_id = ground_truth.case_id
            result = run_test_case_fn(
                _agent_input(ground_truth),
                command_index=step_index,
                agent_timeout_s=agent_timeout_s,
                detector_timeout_s=detector_timeout_s,
            )
            raw_transcript_dict = result["transcript"]
            raw_verdict_dict = result["verdict"]

            # Persist raw data immediately, before any conversion attempt —
            # a malformed dict stays inspectable on disk even if
            # verdict_from_dict() below raises on it (Plan 4 decision 6,
            # unchanged).
            _append_jsonl(verdicts_path, raw_verdict_dict)
            if raw_transcript_dict is not None:
                (raw_dir / f"{case_id}.transcript.json").write_text(json.dumps(raw_transcript_dict), encoding="utf-8")

            # External evidence unconditionally, before moving to the next
            # step (Plan 4 decision 5) — evidence.py never raises on an
            # unreachable container.
            collect_case_evidence_fn(case_id, KNOWN_CONTAINERS, run_output_dir)
            collect_thin_proxy_log_fn(case_id, run_output_dir, api_key)

            conversion_failed = False
            try:
                verdict_obj = verdict_from_dict(raw_verdict_dict)
            except Exception as exc:
                conversion_failed = True
                verdict_conversion_failure_count += 1
                verdict_obj = _fallback_verdict(case_id, exc)

            transcript_obj = None
            if raw_transcript_dict is not None:
                try:
                    transcript_obj = transcript_from_dict(raw_transcript_dict)
                except Exception:
                    transcript_obj = None
                    transcript_conversion_failure_count += 1

            case_obj = TestCase(
                case_id=case_id,
                label=ground_truth.label,
                technique_target=ground_truth.technique_target,
                rationale=ground_truth.rationale,
                transcript=transcript_obj,
            )
            cases.append(case_obj)
            verdicts.append(verdict_obj)
            if step.counts_toward_metric:
                metric_cases.append(case_obj)
                metric_verdicts.append(verdict_obj)

            breaker_kind = "conversion" if conversion_failed else raw_verdict_dict.get("error_kind")
            if breaker_kind == "infra":
                consecutive_infra += 1
                last_infra_rationale = raw_verdict_dict.get("rationale")
            else:
                consecutive_infra = 0

            if consecutive_infra >= breaker_threshold:
                breaker_tripped = True
                break
    finally:
        # Whatever ends the loop early — a circuit-breaker trip or an
        # uncaught exception from run_test_case_fn/evidence collection —
        # close every container still open (design doc, 'Interruzione a
        # metà (circuit breaker)'; extended per council-risk finding on this
        # plan to cover the exception path too, not only a controlled
        # trip). On normal completion open_containers is already empty
        # (validate_sequence guarantees a valid sequence ends closed), so
        # this is a no-op on the happy path. run_command is documented not
        # to raise (default_command_runner catches subprocess errors); a
        # custom run_command that does raise here would suppress an
        # in-flight exception — accepted, same best-effort discipline
        # orchestrator.py already applies to its own cleanup calls.
        for service in sorted(open_containers):
            _close_container(service, run_command)

    return BatchResult(
        cases=cases,
        verdicts=verdicts,
        metric_cases=metric_cases,
        metric_verdicts=metric_verdicts,
        total_count=total_count,
        executed_count=len(cases),
        breaker_tripped=breaker_tripped,
        last_infra_rationale=last_infra_rationale,
        transcript_conversion_failure_count=transcript_conversion_failure_count,
        verdict_conversion_failure_count=verdict_conversion_failure_count,
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/toy_agent/test_sequence.py -v`
Expected: PASS (14 tests)

- [ ] **Step 5: Commit**

```bash
git add src/toy_agent/sequence.py tests/toy_agent/test_sequence.py
git commit -m "feat: close still-open containers on early exit (breaker trip or uncaught exception)"
```

---

## Task 6: `run_batch.py` — thin wrapper over `execute_sequence`, `--container-lifecycle` CLI flag, metrics filtering

**Files:**
- Modify: `src/toy_agent/run_batch.py` (full rewrite)
- Modify: `tests/toy_agent/test_run_batch.py` (full rewrite)
- Modify: `README.md` (the "Come eseguire" section)

**Interfaces:**
- Consumes: Task 1's `OpenStep`/`CommandStep`/`CloseStep`/`KNOWN_CONTAINERS`; Task 4/5's `BatchResult`/`execute_sequence`.
- Produces: `execute_batch(dataset: list[TestCase], run_output_dir: Path, *, container_lifecycle: str = "reused", agent_timeout_s: float = AGENT_TIMEOUT_S, detector_timeout_s: float = DETECTOR_TIMEOUT_S, breaker_threshold: int = BREAKER_THRESHOLD, api_key: str = "", run_test_case_fn=..., collect_case_evidence_fn=..., collect_thin_proxy_log_fn=..., run_command: CommandRunner = default_command_runner) -> BatchResult`; `main(argv: list[str] | None = None) -> None` with a new `--container-lifecycle {reused,per-case}` flag (default `reused`); `BatchResult` re-exported from `.sequence` for backward compatibility (`from toy_agent.run_batch import BatchResult` keeps working).

- [ ] **Step 1: Write the failing tests**

Replace `tests/toy_agent/test_run_batch.py` in full:

```python
import json
import os
from pathlib import Path

import yaml

from toy_agent import run_batch
from toy_agent.orchestrator import CommandResult
from toy_agent.run_batch import BatchResult
from toy_agent.schema import Transcript, Turn, TestCase, Verdict


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


class ScriptedRunTestCase:
    def __init__(self, script):
        self._script = list(script)
        self.calls = []

    def __call__(self, test_case, *, command_index, agent_timeout_s, detector_timeout_s):
        self.calls.append(test_case)
        if not self._script:
            raise AssertionError("script exhausted")
        result = self._script.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class NoOpCommandRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, cmd, stdin_bytes, timeout_s):
        self.calls.append(cmd)
        return CommandResult(returncode=0, stdout=b"", stderr=b"")


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

    run_batch.execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                             collect_case_evidence_fn=RecordingEvidenceCollector(),
                             collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                             run_command=NoOpCommandRunner())

    sent = runner.calls[0]
    assert set(sent.keys()) == {"case_id", "transcript"}
    assert sent["case_id"] == "c1"
    assert sent["transcript"]["turns"] == [{"seq": 0, "role": "user", "content": "hello", "tool_call": None}]
    assert "secret rationale" not in json.dumps(sent)
    assert "T0001" not in json.dumps(sent)


def test_reused_lifecycle_opens_and_closes_once_around_the_whole_dataset(tmp_path):
    dataset = [_ground_truth("c1"), _ground_truth("c2")]
    runner = ScriptedRunTestCase([_ok_result("c1"), _ok_result("c2")])
    command_runner = NoOpCommandRunner()

    run_batch.execute_batch(dataset, tmp_path, container_lifecycle="reused", run_test_case_fn=runner,
                             collect_case_evidence_fn=RecordingEvidenceCollector(),
                             collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                             run_command=command_runner)

    up_calls = [c for c in command_runner.calls if c[:3] == ["docker", "compose", "up"]]
    assert len(up_calls) == 2  # one up per container, once for the whole batch


def test_per_case_lifecycle_opens_and_closes_around_every_single_case(tmp_path):
    dataset = [_ground_truth("c1"), _ground_truth("c2")]
    runner = ScriptedRunTestCase([_ok_result("c1"), _ok_result("c2")])
    command_runner = NoOpCommandRunner()

    run_batch.execute_batch(dataset, tmp_path, container_lifecycle="per-case", run_test_case_fn=runner,
                             collect_case_evidence_fn=RecordingEvidenceCollector(),
                             collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                             run_command=command_runner)

    up_calls = [c for c in command_runner.calls if c[:3] == ["docker", "compose", "up"]]
    assert len(up_calls) == 4  # one up per container, once per case (2 cases x 2 containers)


def test_every_case_id_appears_in_both_output_lists_even_on_failure(tmp_path):
    dataset = [_ground_truth("c1"), _ground_truth("c2")]
    runner = ScriptedRunTestCase([_infra_result("c1"), _ok_result("c2")])

    result = run_batch.execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                                      collect_case_evidence_fn=RecordingEvidenceCollector(),
                                      collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                                      run_command=NoOpCommandRunner())

    assert [c.case_id for c in result.cases] == ["c1", "c2"]
    assert [v.case_id for v in result.verdicts] == ["c1", "c2"]
    assert result.verdicts[0].status == "error"


def test_circuit_breaker_trips_after_three_consecutive_infra_failures(tmp_path):
    dataset = [_ground_truth(f"c{i}") for i in range(1, 5)]
    runner = ScriptedRunTestCase([_infra_result("c1"), _infra_result("c2"), _infra_result("c3")])

    result = run_batch.execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                                      collect_case_evidence_fn=RecordingEvidenceCollector(),
                                      collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                                      run_command=NoOpCommandRunner())

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

    result = run_batch.execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                                      collect_case_evidence_fn=RecordingEvidenceCollector(),
                                      collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                                      run_command=NoOpCommandRunner())

    assert len(runner.calls) == 5  # never tripped — counter reset at c3
    assert result.breaker_tripped is False


def test_per_case_data_is_persisted_immediately_even_if_a_later_case_raises(tmp_path):
    dataset = [_ground_truth("c1"), _ground_truth("c2"), _ground_truth("c3")]
    runner = ScriptedRunTestCase([_ok_result("c1"), _ok_result("c2"), RuntimeError("simulated crash")])

    try:
        run_batch.execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                                 collect_case_evidence_fn=RecordingEvidenceCollector(),
                                 collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                                 run_command=NoOpCommandRunner())
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

    result = run_batch.execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                                      collect_case_evidence_fn=RecordingEvidenceCollector(),
                                      collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                                      run_command=NoOpCommandRunner())

    assert result.cases[0].transcript is None
    assert result.cases[0].label == "malicious"


def test_conversion_failure_falls_back_to_an_error_verdict_and_does_not_trip_the_breaker(tmp_path):
    dataset = [_ground_truth("c1"), _ground_truth("c2"), _ground_truth("c3"), _ground_truth("c4")]
    bad_confidence_result = _ok_result("c2")
    bad_confidence_result["verdict"]["confidence"] = 1.5
    runner = ScriptedRunTestCase([
        _infra_result("c1"), bad_confidence_result, _infra_result("c3"), _infra_result("c4"),
    ])

    result = run_batch.execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                                      collect_case_evidence_fn=RecordingEvidenceCollector(),
                                      collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                                      run_command=NoOpCommandRunner())

    assert len(runner.calls) == 4  # never tripped
    assert result.breaker_tripped is False
    c2_verdict = result.verdicts[1]
    assert c2_verdict.status == "error"
    assert "conversion failed: ValueError" in c2_verdict.rationale
    lines = (tmp_path / "verdicts.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert json.loads(lines[1])["confidence"] == 1.5


def _malformed_transcript_result(case_id, label="benign"):
    return {
        "transcript": {"turns": [], "stop_reason": "completed"},
        "verdict": {
            "case_id": case_id, "tool_name": "agentic_threat_detection", "status": "ok",
            "label": label, "confidence": 0.9, "technique_detected": None,
            "rationale": "r", "cost_usd": None, "latency_s": 1.0,
            "in_tokens": 10, "out_tokens": 5,
        },
    }


def test_transcript_conversion_failure_is_counted_and_leaves_transcript_none(tmp_path):
    dataset = [_ground_truth("c1")]
    runner = ScriptedRunTestCase([_malformed_transcript_result("c1")])

    result = run_batch.execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                                      collect_case_evidence_fn=RecordingEvidenceCollector(),
                                      collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                                      run_command=NoOpCommandRunner())

    assert result.transcript_conversion_failure_count == 1
    assert result.verdict_conversion_failure_count == 0
    assert result.cases[0].transcript is None
    assert result.verdicts[0].status == "ok"


def test_verdict_conversion_failure_is_counted(tmp_path):
    dataset = [_ground_truth("c1")]
    bad_confidence_result = _ok_result("c1")
    bad_confidence_result["verdict"]["confidence"] = 1.5
    runner = ScriptedRunTestCase([bad_confidence_result])

    result = run_batch.execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                                      collect_case_evidence_fn=RecordingEvidenceCollector(),
                                      collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                                      run_command=NoOpCommandRunner())

    assert result.verdict_conversion_failure_count == 1
    assert result.transcript_conversion_failure_count == 0


def test_setup_notes_includes_conversion_failure_and_exclusion_counts_only_when_nonzero():
    from toy_agent.run_batch import BatchResult, _setup_notes

    zero_result = BatchResult(
        cases=[], verdicts=[], total_count=0, executed_count=0, breaker_tripped=False,
        metric_cases=[], metric_verdicts=[],
    )
    notes = _setup_notes(zero_result, 120.0, 180.0, 3)
    assert "transcript_conversion_failures" not in notes
    assert "verdict_conversion_failures" not in notes
    assert "excluded from precision/recall" not in notes

    case = _ground_truth("c1")
    verdict = Verdict(case_id="c1", tool_name="agentic_threat_detection", status="ok", label="benign")
    nonzero_result = BatchResult(
        cases=[case], verdicts=[verdict], total_count=1, executed_count=1, breaker_tripped=False,
        transcript_conversion_failure_count=2, verdict_conversion_failure_count=1,
        metric_cases=[], metric_verdicts=[],  # c1 excluded from metrics
    )
    notes = _setup_notes(nonzero_result, 120.0, 180.0, 3)
    assert "transcript_conversion_failures=2" in notes
    assert "verdict_conversion_failures=1" in notes
    assert "1 command(s) excluded from precision/recall" in notes


def test_verdicts_jsonl_is_truncated_at_the_start_of_a_run_not_appended_across_reruns(tmp_path):
    (tmp_path / "verdicts.jsonl").write_text(json.dumps({"case_id": "stale", "stale": True}) + "\n", encoding="utf-8")

    dataset = [_ground_truth("c1")]
    runner = ScriptedRunTestCase([_ok_result("c1")])

    run_batch.execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                             collect_case_evidence_fn=RecordingEvidenceCollector(),
                             collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                             run_command=NoOpCommandRunner())

    lines = (tmp_path / "verdicts.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["case_id"] == "c1"


def test_evidence_is_collected_for_every_case_regardless_of_outcome(tmp_path):
    dataset = [_ground_truth("c1"), _ground_truth("c2")]
    runner = ScriptedRunTestCase([_infra_result("c1"), _ok_result("c2")])
    evidence_collector = RecordingEvidenceCollector()
    proxy_collector = RecordingProxyLogCollector()

    run_batch.execute_batch(dataset, tmp_path, run_test_case_fn=runner,
                             collect_case_evidence_fn=evidence_collector,
                             collect_thin_proxy_log_fn=proxy_collector,
                             run_command=NoOpCommandRunner())

    assert evidence_collector.calls == ["c1", "c2"]
    assert proxy_collector.calls == ["c1", "c2"]


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

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key=""):
        case = dataset[0]
        verdict = Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")
        return BatchResult(
            cases=[case], verdicts=[verdict],
            total_count=1, executed_count=1, breaker_tripped=False,
            metric_cases=[case], metric_verdicts=[verdict],
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    run_batch.main([str(dataset_dir), str(run_output_dir)])

    after = (dataset_dir / "c1.yaml").read_text(encoding="utf-8")
    assert before == after


def test_main_writes_a_report_declaring_operational_parameters(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key=""):
        case = dataset[0]
        verdict = Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")
        return BatchResult(
            cases=[case], verdicts=[verdict],
            total_count=1, executed_count=1, breaker_tripped=False,
            metric_cases=[case], metric_verdicts=[verdict],
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

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key=""):
        case = dataset[0]
        return BatchResult(
            cases=[case], verdicts=[Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="error")],
            total_count=2, executed_count=1, breaker_tripped=True,
            last_infra_rationale="docker compose exec failed to start the agent invocation",
            metric_cases=[], metric_verdicts=[],
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

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key=""):
        captured["api_key"] = api_key
        case = dataset[0]
        verdict = Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")
        return BatchResult(
            cases=[case], verdicts=[verdict],
            total_count=1, executed_count=1, breaker_tripped=False,
            metric_cases=[case], metric_verdicts=[verdict],
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    run_batch.main([str(dataset_dir), str(run_output_dir)])

    assert captured["api_key"] == "sk-test-key"


def test_main_accepts_the_container_lifecycle_flag_and_defaults_to_reused(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])

    captured = {}

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key=""):
        captured["container_lifecycle"] = container_lifecycle
        case = dataset[0]
        verdict = Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")
        return BatchResult(
            cases=[case], verdicts=[verdict],
            total_count=1, executed_count=1, breaker_tripped=False,
            metric_cases=[case], metric_verdicts=[verdict],
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)

    run_batch.main([str(dataset_dir), str(run_output_dir)])
    assert captured["container_lifecycle"] == "reused"

    run_batch.main([str(dataset_dir), str(run_output_dir), "--container-lifecycle", "per-case"])
    assert captured["container_lifecycle"] == "per-case"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/toy_agent/test_run_batch.py -v`
Expected: FAIL — `TypeError: execute_batch() got an unexpected keyword argument 'container_lifecycle'` (and related) on most tests.

- [ ] **Step 3: Write the implementation**

Replace `src/toy_agent/run_batch.py` in full:

```python
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable

from . import evidence
from .dataset import load_dataset
from .metrics import compute_metrics
from .orchestrator import CommandRunner, default_command_runner, run_test_case
from .report import render_report
from .schema import TestCase
from .sequence import BatchResult, CloseStep, CommandStep, KNOWN_CONTAINERS, OpenStep, execute_sequence

AGENT_TIMEOUT_S = 120.0
DETECTOR_TIMEOUT_S = 180.0
BREAKER_THRESHOLD = 3


def _default_sequence(dataset: list[TestCase], container_lifecycle: str) -> list:
    """The whole-dataset sequence is never hand-written (design doc, 'Il
    caso comune non si scrive a mano') — generated here from the dataset and
    the chosen lifecycle. 'reused' and 'per-case' are the two mechanical
    extremes of the same open/command/close spectrum a hand-written script
    (Gap 15 mode 2) also uses, not a third category."""
    if container_lifecycle == "reused":
        return (
            [OpenStep(containers=KNOWN_CONTAINERS)]
            + [CommandStep(case_id=c.case_id, counts_toward_metric=True) for c in dataset]
            + [CloseStep(containers=KNOWN_CONTAINERS)]
        )
    if container_lifecycle == "per-case":
        steps: list = []
        for c in dataset:
            steps.append(OpenStep(containers=KNOWN_CONTAINERS))
            steps.append(CommandStep(case_id=c.case_id, counts_toward_metric=True))
            steps.append(CloseStep(containers=KNOWN_CONTAINERS))
        return steps
    raise ValueError(f"unknown container_lifecycle: {container_lifecycle!r}")


def execute_batch(
    dataset: list[TestCase],
    run_output_dir: Path,
    *,
    container_lifecycle: str = "reused",
    agent_timeout_s: float = AGENT_TIMEOUT_S,
    detector_timeout_s: float = DETECTOR_TIMEOUT_S,
    breaker_threshold: int = BREAKER_THRESHOLD,
    api_key: str = "",
    run_test_case_fn: Callable[..., dict] = run_test_case,
    collect_case_evidence_fn: Callable = evidence.collect_case_evidence,
    collect_thin_proxy_log_fn: Callable = evidence.collect_thin_proxy_log,
    run_command: CommandRunner = default_command_runner,
) -> BatchResult:
    """Builds the default sequence for a whole-dataset run and delegates to
    execute_sequence (sequence.py) — the sequence-aware core. Kept as a thin
    wrapper so run_batch.py's public signature does not break (design doc,
    touch point 2)."""
    dataset_by_case_id = {c.case_id: c for c in dataset}
    steps = _default_sequence(dataset, container_lifecycle)
    return execute_sequence(
        steps, dataset_by_case_id, run_output_dir,
        agent_timeout_s=agent_timeout_s, detector_timeout_s=detector_timeout_s,
        breaker_threshold=breaker_threshold, api_key=api_key,
        run_test_case_fn=run_test_case_fn,
        collect_case_evidence_fn=collect_case_evidence_fn,
        collect_thin_proxy_log_fn=collect_thin_proxy_log_fn,
        run_command=run_command,
    )


def _setup_notes(result: BatchResult, agent_timeout_s: float, detector_timeout_s: float, breaker_threshold: int) -> str:
    notes = [
        f"agent_timeout_s={agent_timeout_s}",
        f"detector_timeout_s={detector_timeout_s}",
        f"circuit_breaker_threshold={breaker_threshold}",
    ]
    excluded = len(result.cases) - len(result.metric_cases)
    if excluded > 0:
        notes.append(
            f"{excluded} command(s) excluded from precision/recall via counts_toward_metric=false "
            f"(raw verdict still persisted to disk, reviewable by hand)"
        )
    if result.transcript_conversion_failure_count > 0:
        notes.append(f"transcript_conversion_failures={result.transcript_conversion_failure_count}")
    if result.verdict_conversion_failure_count > 0:
        notes.append(f"verdict_conversion_failures={result.verdict_conversion_failure_count}")
    if result.breaker_tripped:
        notes.insert(
            0,
            f"circuit breaker tripped after {result.executed_count}/{result.total_count} cases executed; "
            f"last infra failure: {result.last_infra_rationale}",
        )
    return " | ".join(notes)


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="python -m toy_agent.run_batch")
    parser.add_argument("dataset_dir")
    parser.add_argument("run_output_dir")
    parser.add_argument(
        "--container-lifecycle", choices=["reused", "per-case"], default="reused",
        help="'reused' (default): one agent/detector container for the whole batch, cheap "
             "(no per-case rebuild) and faithful to the vendor's own declared measurement "
             "condition (Gauntlet's Pipeline() is instantiated once for all 300 sessions), "
             "but any state that persists across calls in that shared container is a "
             "declared limitation, not eliminated. "
             "'per-case': a fresh container per case (extra docker compose rm+up per case, "
             "small but nonzero added time), no residual state between cases by "
             "construction. See docs/design/2026-08-19-container-lifecycle-e-sequenze-design.md.",
    )
    parsed = parser.parse_args(args)

    dataset_dir = Path(parsed.dataset_dir)
    run_output_dir = Path(parsed.run_output_dir)

    dataset = load_dataset(dataset_dir)
    api_key = os.environ.get("DETECTOR_OPENROUTER_API_KEY", "")
    result = execute_batch(dataset, run_output_dir, container_lifecycle=parsed.container_lifecycle, api_key=api_key)

    metrics = compute_metrics(result.metric_cases, result.metric_verdicts)
    setup_notes = _setup_notes(result, AGENT_TIMEOUT_S, DETECTOR_TIMEOUT_S, BREAKER_THRESHOLD)
    report = render_report(result.cases, result.verdicts, metrics, setup_notes=setup_notes)
    run_output_dir.mkdir(parents=True, exist_ok=True)
    (run_output_dir / "report.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/toy_agent/test_run_batch.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Run the full test suite**

Run: `pytest tests/toy_agent tests/detector_adapter -v`
Expected: PASS (every test — Task 2's transitional failure in `test_run_batch.py` is now fixed)

- [ ] **Step 6: Update `README.md`**

In `README.md`, replace:

```
docker compose build
docker compose up -d
```

with:

```
docker compose build
docker compose up -d egress-proxy
```

Then replace:

```
Con lo stack sopra (`docker compose up -d`), il batch orchestrator si esegue **sull'host**,
non dentro un container:

```
python -m toy_agent.run_batch <dataset_dir> <run_output_dir>
```
```

with:

```
Con `egress-proxy` sopra, il batch orchestrator si esegue **sull'host**, non dentro un
container. A differenza di prima, possiede lui stesso il ciclo di vita di `agent`/`detector`
(li ricrea/rimuove via `docker compose`, non serve più avviarli a mano) — il parametro
`--container-lifecycle` sceglie come:

```
python -m toy_agent.run_batch <dataset_dir> <run_output_dir>
# equivalente a:
python -m toy_agent.run_batch <dataset_dir> <run_output_dir> --container-lifecycle reused
# un container fresco per ogni caso (isolamento massimo, costo più alto):
python -m toy_agent.run_batch <dataset_dir> <run_output_dir> --container-lifecycle per-case
```

`reused` (default) tiene `agent`/`detector` aperti per l'intero batch — fedele alla
condizione di misura dichiarata dal vendor (Gauntlet, `Pipeline()` istanziata una sola
volta per 300 sessioni). `per-case` ricrea entrambi i container a ogni caso, per costruzione
senza alcuno stato residuo tra un caso e il successivo. Dettagli:
`docs/design/2026-08-19-container-lifecycle-e-sequenze-design.md`.

`docker compose build` resta comunque necessario prima del primo run (costruisce le
immagini): il ciclo di vita che `run_batch.py` ora gestisce è solo avvio/rimozione dei
container, non il build. Se `agent`/`detector` risultano già in esecuzione da un run
precedente o da un avvio manuale, non serve fermarli a mano: il primo `open` della
sequenza li rimuove e ricrea comunque, in modo sicuro (auto-risanante per costruzione,
vedi design doc).

- [ ] **Step 7: Commit**

```bash
git add src/toy_agent/run_batch.py tests/toy_agent/test_run_batch.py README.md
git commit -m "feat: run_batch.py owns agent/detector lifecycle via --container-lifecycle"
```

---

## Task 7: `detector_adapter/adapter.py` — opaque `call_id` (Gap 14, A5)

**Files:**
- Modify: `src/detector_adapter/adapter.py:1-4,38`
- Test: `tests/detector_adapter/test_adapter_agent_event.py`

**Interfaces:**
- No public signature changes — `transcript_dict_to_agent_event` keeps its existing contract; only the `call_id` value it produces per tool call changes.

- [ ] **Step 1: Write the failing tests**

Add to `tests/detector_adapter/test_adapter_agent_event.py` (add `import re` to the existing `import pytest` line at the top):

```python
import re

import pytest
```

Then add at the end of the file:

```python
def test_tool_call_id_is_opaque_not_positional():
    # Gap 14, A5: call_id=f"call_{seq}" was a predictable, sequence-revealing
    # pattern — a real tool-calling integration typically emits opaque
    # hash/token ids, not a visible counter.
    ev = transcript_dict_to_agent_event(_TRANSCRIPT)
    calling = [m for m in ev.messages if m.message_type == "tool_calling"]
    call_id = calling[0].tool_calls[0].call_id
    assert call_id != "call_1"
    assert re.fullmatch(r"[0-9a-f]{32}", call_id)


def test_tool_call_id_is_unique_per_call():
    transcript_two_calls = {
        "session_id": "case_008",
        "turns": [
            {"seq": 0, "role": "user", "content": "do two things", "tool_call": None},
            {"seq": 1, "role": "tool", "content": "ok", "tool_call": {
                "tool_name": "update_account", "arguments": {}, "result": "ok", "status": "ok",
            }},
            {"seq": 2, "role": "tool", "content": "ok", "tool_call": {
                "tool_name": "update_account", "arguments": {}, "result": "ok", "status": "ok",
            }},
        ],
        "stop_reason": "completed",
    }
    ev = transcript_dict_to_agent_event(transcript_two_calls)
    calling = [m for m in ev.messages if m.message_type == "tool_calling"]
    ids = [c.tool_calls[0].call_id for c in calling]
    assert len(set(ids)) == len(ids) == 2
```

- [ ] **Step 2: Run the tests to verify they fail**

These tests are aidr-gated (`pytest.importorskip("aidr")`) — they only run for real inside the `detector` container, same as the rest of this file. On this host they SKIP rather than FAIL, which is expected and is not the TDD red step for this task; the meaningful red/green cycle happens inside the container in Step 3-5 below. Locally, confirm the test file at least imports cleanly:

Run: `pytest tests/detector_adapter/test_adapter_agent_event.py -v`
Expected: all tests in the file SKIPPED with reason "aidr is only installed inside the detector container"

- [ ] **Step 3: Write the implementation**

In `src/detector_adapter/adapter.py`, add `import uuid` to the top-level imports:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
```

In `_build_messages`, change the `ToolUsage` construction:

```python
            usage = ToolUsage(
                tool_name=f"{SERVER_NAME}.{call['tool_name']}",
                server_name=SERVER_NAME,
                arguments=call["arguments"],
                result=call.get("result"),
                status=call.get("status", "ok"),
                call_id=uuid.uuid4().hex,
            )
```

- [ ] **Step 4: Run the real, aidr-gated test suite inside the detector container**

This is the live verification the design doc's mapping table requires for A5 (not just a mocked unit test) — it exercises the fix against the real pinned `aidr` package. From the repo root, with the stack up:

```bash
docker compose up -d detector
sh docker/detector/run_adapter_tests.sh
```

Expected: all tests in `tests/detector_adapter/` PASS, including the two new ones, executed for real against `aidr` (pinned commit `7fad14d2478707e68a09b8ecd9942dec8fde1614`) inside the container — confirming `aidr.AgentEvent`/`ToolUsage` accepts the new opaque `call_id` format without raising.

- [ ] **Step 5: Run the full host-side test suite**

Run: `pytest tests/toy_agent tests/detector_adapter -v`
Expected: PASS (the two new tests SKIP on the host, as in Step 2 — that's expected; Step 4 is what proves them for real)

- [ ] **Step 6: Commit**

```bash
git add src/detector_adapter/adapter.py tests/detector_adapter/test_adapter_agent_event.py
git commit -m "fix: opaque call_id, never call_{seq} (Gap 14, A5)"
```

---

## Final Verification

- [ ] Run the entire host-side suite once more: `pytest tests/ -v` — expect all PASS or the two aidr-gated SKIPs from Task 7.
- [ ] Confirm the Mapping Requisito → Verifica table in the design doc (`docs/design/2026-08-19-container-lifecycle-e-sequenze-design.md`) has a passing test for every row:
  - Validator rejects every malformed sequence → Task 1
  - `close` removes, never just stops → Task 3
  - Thin-proxy log never truncated, only marked → Task 2
  - Mid-sequence interruption closes every still-open container → Task 5
  - `call_id` no longer reveals sequential position (A5), live-verified → Task 7
  - `open` is auto-healing regardless of prior state → Task 3
  - `counts_toward_metric=false` excluded from P/R, raw verdict still persisted → Task 4
- [ ] Update `docs/design/2026-08-14-toy-agent-gap-tracking.md`'s Gap 14/Gap 15 status lines from "risolto nel design" to "risolto nel codice", linking this plan's commits (per the doc's own "Come si chiude un gap" convention).
