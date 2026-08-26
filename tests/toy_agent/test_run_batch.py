import json
import os
from pathlib import Path

import pytest
import yaml

from toy_agent import provenance, run_batch
from toy_agent.orchestrator import CommandResult
from toy_agent.run_batch import BatchResult
from toy_agent.schema import Transcript, Turn, TestCase, Verdict, Always, ToolCall


def _run_dir(run_output_dir):
    dirs = [d for d in run_output_dir.iterdir() if d.is_dir() and d.name != "latest"]
    assert len(dirs) == 1, f"expected exactly one run dir, got {[d.name for d in dirs]}"
    return dirs[0]


def _ground_truth(case_id, label="benign", technique_target=None, rationale="r", seed_content="hi"):
    transcript = Transcript(session_id=case_id, turns=[Turn(seq=0, role="user", content=seed_content)])
    criteria = Always() if label == "malicious" else None
    return TestCase(
        case_id=case_id, label=label, technique_target=technique_target,
        rationale=rationale, transcript=transcript, attack_success_criteria=criteria,
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


def test_setup_notes_always_declares_gap17_technique_coverage():
    from toy_agent.run_batch import BatchResult, _setup_notes

    zero_result = BatchResult(
        cases=[], verdicts=[], total_count=0, executed_count=0, breaker_tripped=False,
        metric_cases=[], metric_verdicts=[],
    )
    notes = _setup_notes(zero_result, 120.0, 180.0, 3)
    assert "T0009" in notes
    assert "T0011" in notes
    assert "12/14" in notes


def test_setup_notes_reports_reclassified_and_unknown_outcome_counts():
    from toy_agent.run_batch import BatchResult, _setup_notes

    def _executed_case(case_id, attack_succeeded):
        t = Transcript(session_id=case_id, turns=[Turn(seq=0, role="user", content="hi")])
        return TestCase(
            case_id=case_id, label="malicious", technique_target="T0007", rationale="r",
            transcript=t, attack_success_criteria=Always(), attack_succeeded=attack_succeeded,
        )

    reclassified_case = _executed_case("c1", attack_succeeded=False)
    unknown_case = _executed_case("c2", attack_succeeded=None)
    verdict1 = Verdict(case_id="c1", tool_name="agentic_threat_detection", status="ok", label="benign")
    verdict2 = Verdict(case_id="c2", tool_name="agentic_threat_detection", status="ok", label="benign")

    result = BatchResult(
        cases=[reclassified_case, unknown_case], verdicts=[verdict1, verdict2],
        total_count=2, executed_count=2, breaker_tripped=False,
        metric_cases=[reclassified_case, unknown_case], metric_verdicts=[verdict1, verdict2],
    )
    notes = _setup_notes(result, 120.0, 180.0, 3)
    assert "1 malicious case(s) reclassified as benign for scoring" in notes
    assert "1 malicious case(s) have unknown attack outcome" in notes


def test_setup_notes_omits_reclassified_and_unknown_outcome_notes_when_zero():
    from toy_agent.run_batch import BatchResult, _setup_notes

    case = _ground_truth("c1")  # benign
    verdict = Verdict(case_id="c1", tool_name="agentic_threat_detection", status="ok", label="benign")
    result = BatchResult(
        cases=[case], verdicts=[verdict], total_count=1, executed_count=1, breaker_tripped=False,
        metric_cases=[case], metric_verdicts=[verdict],
    )
    notes = _setup_notes(result, 120.0, 180.0, 3)
    assert "reclassified as benign for scoring" not in notes
    assert "unknown attack outcome" not in notes


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

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key="", progress_fn=None):
        case = dataset[0]
        verdict = Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")
        return BatchResult(
            cases=[case], verdicts=[verdict],
            total_count=1, executed_count=1, breaker_tripped=False,
            metric_cases=[case], metric_verdicts=[verdict],
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    monkeypatch.setattr(run_batch, "preflight_check_models", lambda *a, **kw: [])
    run_batch.main([str(dataset_dir), str(run_output_dir)])

    after = (dataset_dir / "c1.yaml").read_text(encoding="utf-8")
    assert before == after


def test_main_writes_a_report_declaring_operational_parameters(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key="", progress_fn=None):
        case = dataset[0]
        verdict = Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")
        return BatchResult(
            cases=[case], verdicts=[verdict],
            total_count=1, executed_count=1, breaker_tripped=False,
            metric_cases=[case], metric_verdicts=[verdict],
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    monkeypatch.setattr(run_batch, "preflight_check_models", lambda *a, **kw: [])
    run_batch.main([str(dataset_dir), str(run_output_dir)])

    report = (_run_dir(run_output_dir) / "report.md").read_text(encoding="utf-8")
    assert f"agent_timeout_s={run_batch.AGENT_TIMEOUT_S}" in report
    assert f"detector_timeout_s={run_batch.DETECTOR_TIMEOUT_S}" in report
    assert f"circuit_breaker_threshold={run_batch.BREAKER_THRESHOLD}" in report


def test_main_declares_a_circuit_breaker_trip_in_the_report(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1", "c2"])

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key="", progress_fn=None):
        case = dataset[0]
        return BatchResult(
            cases=[case], verdicts=[Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="error")],
            total_count=2, executed_count=1, breaker_tripped=True,
            last_infra_rationale="docker compose exec failed to start the agent invocation",
            metric_cases=[], metric_verdicts=[],
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    monkeypatch.setattr(run_batch, "preflight_check_models", lambda *a, **kw: [])
    run_batch.main([str(dataset_dir), str(run_output_dir)])

    report = (_run_dir(run_output_dir) / "report.md").read_text(encoding="utf-8")
    assert "1/2" in report
    assert "docker compose exec failed to start the agent invocation" in report


def test_main_reads_the_detector_api_key_from_the_environment(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])
    monkeypatch.setenv("DETECTOR_OPENROUTER_API_KEY", "sk-test-key")

    captured = {}

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key="", progress_fn=None):
        captured["api_key"] = api_key
        case = dataset[0]
        verdict = Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")
        return BatchResult(
            cases=[case], verdicts=[verdict],
            total_count=1, executed_count=1, breaker_tripped=False,
            metric_cases=[case], metric_verdicts=[verdict],
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    monkeypatch.setattr(run_batch, "preflight_check_models", lambda *a, **kw: [])
    run_batch.main([str(dataset_dir), str(run_output_dir)])

    assert captured["api_key"] == "sk-test-key"


def test_main_accepts_the_container_lifecycle_flag_and_defaults_to_reused(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])

    captured = {}

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key="", progress_fn=None):
        captured["container_lifecycle"] = container_lifecycle
        case = dataset[0]
        verdict = Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")
        return BatchResult(
            cases=[case], verdicts=[verdict],
            total_count=1, executed_count=1, breaker_tripped=False,
            metric_cases=[case], metric_verdicts=[verdict],
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    monkeypatch.setattr(run_batch, "preflight_check_models", lambda *a, **kw: [])

    run_batch.main([str(dataset_dir), str(run_output_dir)])
    assert captured["container_lifecycle"] == "reused"

    run_batch.main([str(dataset_dir), str(run_output_dir), "--container-lifecycle", "per-case"])
    assert captured["container_lifecycle"] == "per-case"


def _case_with_tool_call(case_id, label, tool_name, technique_target=None):
    transcript = Transcript(
        session_id=case_id,
        turns=[
            Turn(seq=0, role="user", content="hi"),
            Turn(
                seq=1, role="tool", content="ok",
                tool_call=ToolCall(tool_name=tool_name, arguments={}, result="ok", status="ok"),
            ),
        ],
    )
    criteria = Always() if label == "malicious" else None
    return TestCase(
        case_id=case_id, label=label, technique_target=technique_target, rationale="r",
        transcript=transcript, attack_success_criteria=criteria,
    )


def test_find_malicious_only_tools_flags_a_tool_seen_only_in_malicious_cases():
    cases = [
        _case_with_tool_call("c1", "malicious", "bulk_export", technique_target="T0012"),
        _case_with_tool_call("c2", "benign", "query_customer_db"),
    ]
    assert run_batch.find_malicious_only_tools(cases) == {"bulk_export"}


def test_find_malicious_only_tools_ignores_a_tool_also_seen_in_a_benign_case():
    cases = [
        _case_with_tool_call("c1", "malicious", "update_account", technique_target="T0005"),
        _case_with_tool_call("c2", "benign", "update_account"),
    ]
    assert run_batch.find_malicious_only_tools(cases) == set()


def test_find_malicious_only_tools_skips_cases_with_no_transcript():
    dataset = [_ground_truth("c1", label="malicious", technique_target="T0001")]
    dataset[0].transcript = None
    assert run_batch.find_malicious_only_tools(dataset) == set()


def test_setup_notes_declares_the_shortcut_check_passed_when_no_shortcut_tools_found():
    from toy_agent.run_batch import BatchResult, _setup_notes

    case = _ground_truth("c1")  # benign, no tool_call turns -> find_malicious_only_tools returns empty
    verdict = Verdict(case_id="c1", tool_name="agentic_threat_detection", status="ok", label="benign")
    result = BatchResult(
        cases=[case], verdicts=[verdict], total_count=1, executed_count=1, breaker_tripped=False,
        metric_cases=[case], metric_verdicts=[verdict],
    )
    notes = _setup_notes(result, 120.0, 180.0, 3)
    assert "tool->label shortcut check: passed" in notes


def test_main_stderr_notes_a_truncated_run_when_the_breaker_tripped_and_a_shortcut_is_found(tmp_path, monkeypatch, capsys):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key="", progress_fn=None):
        malicious_case = _case_with_tool_call("c1", "malicious", "bulk_export", technique_target="T0012")
        verdict = Verdict(case_id="c1", tool_name="agentic_threat_detection", status="ok", label="malicious", technique_detected="T0012")
        return BatchResult(
            cases=[malicious_case], verdicts=[verdict],
            total_count=3, executed_count=1, breaker_tripped=True,
            last_infra_rationale="docker compose exec failed to start",
            metric_cases=[malicious_case], metric_verdicts=[verdict],
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    monkeypatch.setattr(run_batch, "preflight_check_models", lambda *a, **kw: [])

    try:
        run_batch.main([str(dataset_dir), str(run_output_dir)])
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert exc.code == 1
    captured = capsys.readouterr()
    assert "circuit breaker tripped" in captured.err
    assert "truncated" in captured.err
    assert not (_run_dir(run_output_dir) / "report.md").exists()


def _result_with_unusable(dataset, unusable_count, executed):
    cases = dataset[:executed]
    verdicts = [Verdict(case_id=c.case_id, tool_name="agentic_threat_detection", status="ok", label="benign") for c in cases]
    unusable = {c.case_id: "model_error" for c in cases[:unusable_count]}
    keep = [i for i, c in enumerate(cases) if c.case_id not in unusable]
    return BatchResult(
        cases=cases, verdicts=verdicts,
        total_count=executed, executed_count=executed, breaker_tripped=False,
        metric_cases=[cases[i] for i in keep], metric_verdicts=[verdicts[i] for i in keep],
        transcript_unusable=unusable,
    )


def test_the_gate_passes_at_or_below_the_declared_fraction():
    dataset = [_ground_truth(f"c{i}") for i in range(1, 11)]
    result = _result_with_unusable(dataset, unusable_count=1, executed=10)
    assert run_batch.transcript_unusable_gate_failure(result) is None


def test_the_gate_fails_above_the_declared_fraction():
    dataset = [_ground_truth(f"c{i}") for i in range(1, 11)]
    result = _result_with_unusable(dataset, unusable_count=2, executed=10)
    message = run_batch.transcript_unusable_gate_failure(result)
    assert message is not None
    assert "2/10" in message
    assert "model_error" in message


def test_main_refuses_to_write_the_report_past_the_threshold(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, [f"c{i}" for i in range(1, 11)])

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key="", progress_fn=None):
        cases = dataset[:10]
        verdicts = [Verdict(case_id=c.case_id, tool_name="agentic_threat_detection", status="ok", label="benign") for c in cases]
        unusable = {c.case_id: "model_error" for c in cases[:2]}
        keep = [i for i, c in enumerate(cases) if c.case_id not in unusable]
        return BatchResult(
            cases=cases, verdicts=verdicts,
            total_count=10, executed_count=10, breaker_tripped=False,
            metric_cases=[cases[i] for i in keep], metric_verdicts=[verdicts[i] for i in keep],
            transcript_unusable=unusable,
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    monkeypatch.setattr(run_batch, "preflight_check_models", lambda *a, **kw: [])

    try:
        run_batch.main([str(dataset_dir), str(run_output_dir)])
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert exc.code == 1
    assert not (_run_dir(run_output_dir) / "report.md").exists()


def test_main_refuses_to_write_the_report_when_a_tool_appears_only_in_malicious_cases(tmp_path, monkeypatch):
    # _write_dataset/_dataset_yaml_entry già esistono in questo file (usati da
    # test_main_never_modifies_the_dataset_dir e simili) — non ridefinirli qui,
    # producono già entry benigne valide, sufficienti perché main() carichi un
    # dataset non vuoto prima che fake_execute_batch prenda il controllo.
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key="", progress_fn=None):
        malicious_case = _case_with_tool_call("c1", "malicious", "bulk_export", technique_target="T0012")
        verdict = Verdict(case_id="c1", tool_name="agentic_threat_detection", status="ok", label="malicious", technique_detected="T0012")
        return BatchResult(
            cases=[malicious_case], verdicts=[verdict],
            total_count=1, executed_count=1, breaker_tripped=False,
            metric_cases=[malicious_case], metric_verdicts=[verdict],
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    monkeypatch.setattr(run_batch, "preflight_check_models", lambda *a, **kw: [])

    try:
        run_batch.main([str(dataset_dir), str(run_output_dir)])
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert exc.code == 1
    assert not (_run_dir(run_output_dir) / "report.md").exists()


def test_setup_notes_declares_every_experimental_condition_unconditionally():
    prov = provenance.collect_provenance({})
    notes = run_batch._setup_notes(
        BatchResult(cases=[], verdicts=[], total_count=0, executed_count=0, breaker_tripped=False),
        120.0, 180.0, 3, prov,
    )
    for token in ("measurer_commit=", "vendor_commit=", "agent_model=", "sifter_model=",
                  "inspector_model=", "embed_model=", "cost_source="):
        assert token in notes


def test_setup_notes_declares_the_unusable_threshold_even_when_nothing_was_excluded():
    notes = run_batch._setup_notes(
        BatchResult(cases=[], verdicts=[], total_count=0, executed_count=0, breaker_tripped=False),
        120.0, 180.0, 3, provenance.collect_provenance({}),
    )
    assert "transcript_unusable_threshold=" in notes


def test_setup_notes_reports_unusable_cases_by_cause():
    result = BatchResult(
        cases=[], verdicts=[], total_count=3, executed_count=3, breaker_tripped=False,
        transcript_unusable={"c1": "transcript_missing", "c2": "model_error", "c3": "arguments_parse_failed"},
    )
    notes = run_batch._setup_notes(result, 120.0, 180.0, 3, provenance.collect_provenance({}))
    assert "transcript_unusable=3/3" in notes
    for cause in ("transcript_missing=1", "model_error=1", "arguments_parse_failed=1"):
        assert cause in notes


def test_setup_notes_declares_an_unrecorded_provenance_rather_than_omitting_it():
    notes = run_batch._setup_notes(
        BatchResult(cases=[], verdicts=[], total_count=0, executed_count=0, breaker_tripped=False),
        120.0, 180.0, 3, None,
    )
    assert "not recorded" in notes


def test_main_passes_both_keys_to_the_preflight(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    _write_dataset(dataset_dir, ["c1"])
    monkeypatch.setenv("DETECTOR_OPENROUTER_API_KEY", "sk-detector")
    monkeypatch.setenv("AGENT_OPENROUTER_API_KEY", "sk-agent")
    captured = {}
    def fake_preflight(env, api_key, *, agent_api_key="", transport=None):
        captured["api_key"] = api_key
        captured["agent_api_key"] = agent_api_key
        return []
    monkeypatch.setattr(run_batch, "preflight_check_models", fake_preflight)
    monkeypatch.setattr(run_batch, "execute_batch", lambda dataset, output_dir, **kw: BatchResult(cases=[], verdicts=[], total_count=0, executed_count=0, breaker_tripped=False))
    run_batch.main([str(dataset_dir), str(tmp_path / "out")])
    assert captured == {"api_key": "sk-detector", "agent_api_key": "sk-agent"}


def test_main_writes_the_provenance_file_next_to_the_raw_data(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])
    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key="", progress_fn=None):
        case = dataset[0]
        verdict = Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")
        return BatchResult(cases=[case], verdicts=[verdict], total_count=1, executed_count=1,
                           breaker_tripped=False, metric_cases=[case], metric_verdicts=[verdict])
    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    monkeypatch.setattr(run_batch, "preflight_check_models", lambda *a, **kw: [])
    run_batch.main([str(dataset_dir), str(run_output_dir)])
    run_dir = _run_dir(run_output_dir)
    prov = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))
    assert prov["agent_model"] == "openai/gpt-4o-mini"
    assert "measurer_commit=" in (run_dir / "report.md").read_text(encoding="utf-8")


def test_run_id_format_matches_expected_pattern(tmp_path, monkeypatch):
    import re
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])
    captured = {}

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key="", progress_fn=None):
        captured["run_dir"] = output_dir
        case = dataset[0]
        verdict = Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")
        return BatchResult(
            cases=[case], verdicts=[verdict],
            total_count=1, executed_count=1, breaker_tripped=False,
            metric_cases=[case], metric_verdicts=[verdict],
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    monkeypatch.setattr(run_batch, "preflight_check_models", lambda *a, **kw: [])
    run_batch.main([str(dataset_dir), str(run_output_dir)])

    run_dir = captured["run_dir"]
    assert re.fullmatch(r"\d{8}-\d{6}-[0-9a-f]{6}", run_dir.name), run_dir.name
    assert run_dir.parent == run_output_dir


def test_each_run_creates_its_own_directory(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key="", progress_fn=None):
        case = dataset[0]
        verdict = Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")
        return BatchResult(
            cases=[case], verdicts=[verdict],
            total_count=1, executed_count=1, breaker_tripped=False,
            metric_cases=[case], metric_verdicts=[verdict],
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    monkeypatch.setattr(run_batch, "preflight_check_models", lambda *a, **kw: [])
    run_batch.main([str(dataset_dir), str(run_output_dir)])

    run_dir = _run_dir(run_output_dir)
    assert (run_dir / "report.md").exists()
    assert (run_dir / "provenance.json").exists()
    assert not (run_output_dir / "report.md").exists()
    assert not (run_output_dir / "provenance.json").exists()


def test_latest_points_to_the_run_that_ran(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key="", progress_fn=None):
        case = dataset[0]
        verdict = Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")
        return BatchResult(
            cases=[case], verdicts=[verdict],
            total_count=1, executed_count=1, breaker_tripped=False,
            metric_cases=[case], metric_verdicts=[verdict],
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    monkeypatch.setattr(run_batch, "preflight_check_models", lambda *a, **kw: [])
    run_batch.main([str(dataset_dir), str(run_output_dir)])

    run_dir = _run_dir(run_output_dir)
    latest = run_output_dir / "latest"
    assert latest.is_symlink()
    assert latest.resolve() == run_dir.resolve()

    # A failed preflight must not create or move latest.
    previous_target = latest.readlink()

    def fake_preflight_failing(env, api_key, *, agent_api_key="", transport=None):
        return ["model unavailable"]

    monkeypatch.setattr(run_batch, "preflight_check_models", fake_preflight_failing)

    try:
        run_batch.main([str(dataset_dir), str(run_output_dir)])
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert exc.code == 1

    assert latest.is_symlink()
    assert latest.readlink() == previous_target


def test_preflight_failure_writes_the_reason_into_run_log(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])

    def fake_preflight_failing(env, api_key, *, agent_api_key="", transport=None):
        return ["model unavailable"]

    monkeypatch.setattr(run_batch, "preflight_check_models", fake_preflight_failing)

    try:
        run_batch.main([str(dataset_dir), str(run_output_dir)])
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert exc.code == 1

    run_dir = _run_dir(run_output_dir)
    log = (run_dir / "run.log").read_text(encoding="utf-8")
    assert "preflight model check failed: model unavailable" in log


def test_run_log_contains_banner_and_summary(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "dataset"
    run_output_dir = tmp_path / "out"
    _write_dataset(dataset_dir, ["c1"])

    def fake_execute_batch(dataset, output_dir, *, container_lifecycle="reused", api_key="", progress_fn=None):
        case = dataset[0]
        verdict = Verdict(case_id=case.case_id, tool_name="agentic_threat_detection", status="ok", label="benign")
        return BatchResult(
            cases=[case], verdicts=[verdict],
            total_count=1, executed_count=1, breaker_tripped=False,
            metric_cases=[case], metric_verdicts=[verdict],
            total_in_tokens=10,
        )

    monkeypatch.setattr(run_batch, "execute_batch", fake_execute_batch)
    monkeypatch.setattr(run_batch, "preflight_check_models", lambda *a, **kw: [])
    run_batch.main([str(dataset_dir), str(run_output_dir)])

    run_dir = _run_dir(run_output_dir)
    log = (run_dir / "run.log").read_text(encoding="utf-8")
    assert "=== agentic-security-audits — run ===" in log
    assert "=== summary ===" in log


# --- runtime guard: refuse to run the wrong checkout's code ---

def _repo_root() -> Path:
    # tests/toy_agent/test_run_batch.py -> repo root
    return Path(__file__).resolve().parent.parent.parent


def test_working_tree_root_finds_the_repo_from_its_own_root(monkeypatch):
    monkeypatch.chdir(_repo_root())
    assert run_batch._working_tree_root() == _repo_root()


def test_working_tree_root_finds_the_repo_from_a_subdirectory(monkeypatch):
    monkeypatch.chdir(_repo_root() / "tests")
    assert run_batch._working_tree_root() == _repo_root()


def test_working_tree_root_returns_none_outside_any_checkout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert run_batch._working_tree_root() is None


def test_runtime_guard_passes_when_imported_from_the_working_tree(monkeypatch):
    monkeypatch.chdir(_repo_root())
    run_batch._assert_running_from_this_working_tree()  # must not exit


def test_runtime_guard_refuses_when_imported_from_elsewhere(monkeypatch):
    monkeypatch.chdir(_repo_root())
    monkeypatch.setattr(run_batch, "__file__", "/elsewhere/src/toy_agent/run_batch.py")
    try:
        run_batch._assert_running_from_this_working_tree()
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert exc.code == 1


def test_main_calls_the_guard_before_anything_else(monkeypatch, capsys):
    monkeypatch.chdir(_repo_root())
    monkeypatch.setattr(run_batch, "__file__", "/elsewhere/src/toy_agent/run_batch.py")
    try:
        run_batch.main(["dataset", "out"])
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert exc.code == 1
    captured = capsys.readouterr()
    assert "refusing to run" in captured.err
    assert "different checkout" in captured.err
