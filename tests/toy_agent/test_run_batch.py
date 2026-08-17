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
