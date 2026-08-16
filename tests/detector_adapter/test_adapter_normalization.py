from types import SimpleNamespace

from detector_adapter.adapter import (
    DETECTOR_TOOL_NAME,
    AgenticThreatDetectionAdapter,
    detection_result_to_verdict,
)


def _result(**overrides):
    base = dict(is_malicious=False, confidence=0.0, technique="N/A", explanation="", latency_s=1.5, in_tokens=100, out_tokens=20)
    base.update(overrides)
    return SimpleNamespace(**base)


def test_malicious_result_maps_to_malicious_verdict():
    v = detection_result_to_verdict("case_1", _result(is_malicious=True, confidence=0.9, technique="T0007", explanation="hidden escalation"))
    assert v["case_id"] == "case_1"
    assert v["tool_name"] == DETECTOR_TOOL_NAME
    assert v["status"] == "ok"
    assert v["label"] == "malicious"
    assert v["confidence"] == 0.9
    assert v["technique_detected"] == "T0007"
    assert v["rationale"] == "hidden escalation"
    assert v["cost_usd"] is None  # computed later by the metrics module (design doc, "Schema di misura")
    assert v["latency_s"] == 1.5


def test_benign_result_normalizes_na_technique_to_none():
    v = detection_result_to_verdict("case_2", _result(technique="N/A"))
    assert v["label"] == "benign"
    assert v["technique_detected"] is None


def test_empty_explanation_normalizes_to_none_rationale():
    v = detection_result_to_verdict("case_3", _result(explanation=""))
    assert v["rationale"] is None


def test_token_counts_are_preserved_not_discarded():
    # council-skeptic finding, Gap 9 targeted council: DetectionResult is the
    # only object that ever has in_tokens/out_tokens — discarding them here
    # would make cost_usd permanently uncomputable by Plan 4's metrics module,
    # not just "computed later".
    v = detection_result_to_verdict("case_4", _result(in_tokens=1234, out_tokens=567))
    assert v["in_tokens"] == 1234
    assert v["out_tokens"] == 567


class _FakeProc:
    def __init__(self, alive: bool):
        self._alive = alive
        self.terminated = False
        self.killed = False

    def poll(self):
        return None if self._alive else 0

    def terminate(self):
        self.terminated = True
        self._alive = False

    def wait(self, timeout=None):
        pass

    def kill(self):
        self.killed = True


class _FakeMCPClient:
    def __init__(self, proc):
        self.proc = proc


def test_terminate_subprocesses_terminates_only_live_mcp_clients():
    live_proc = _FakeProc(alive=True)
    dead_proc = _FakeProc(alive=False)
    fake_pipeline = SimpleNamespace(
        inspector=SimpleNamespace(
            router=SimpleNamespace(clients={"sourcelens": _FakeMCPClient(live_proc), "threatlens": _FakeMCPClient(dead_proc)})
        )
    )
    adapter = AgenticThreatDetectionAdapter(pipeline=fake_pipeline)
    adapter.terminate_subprocesses()
    assert live_proc.terminated is True
    assert dead_proc.terminated is False  # already dead — no redundant signal


def test_terminate_subprocesses_never_raises_without_a_router():
    adapter = AgenticThreatDetectionAdapter(pipeline=SimpleNamespace())
    adapter.terminate_subprocesses()  # must not raise — called from an except branch
