from types import SimpleNamespace

from detector_adapter.vendors.aidr.adapter import (
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


def test_terminate_subprocesses_never_raises_when_router_has_no_clients():
    # council-review finding: router can exist but be a partially-constructed
    # or malformed object without a .clients attribute — this is exactly the
    # mid-operation state evaluate_case.py's except TimeoutError handler is
    # calling into, so it must degrade to "did nothing", not propagate.
    fake_pipeline = SimpleNamespace(inspector=SimpleNamespace(router=SimpleNamespace()))
    adapter = AgenticThreatDetectionAdapter(pipeline=fake_pipeline)
    adapter.terminate_subprocesses()  # must not raise


# --- Task 7: retrofit fail-open aidr + rename DETECTOR_TOOL_NAME ---


class _FakeDetectionResult:
    def __init__(self, is_malicious, confidence=0.0, latency_s=0.1, in_tokens=1, out_tokens=1):
        self.is_malicious = is_malicious
        self.confidence = confidence
        self.technique = "N/A"
        self.explanation = ""
        self.latency_s = latency_s
        self.in_tokens = in_tokens
        self.out_tokens = out_tokens


class _FailingSifter:
    """Mirrors aidr.detector.sifter.Sifter's real shape (verified on the
    pinned vendor source): triage() raises, triage_safe() catches and
    defaults — exercising the wrapper installed on self._pipeline.sifter.triage."""
    def triage(self, transcript):
        raise RuntimeError("boom")

    def triage_safe(self, transcript):
        try:
            return self.triage(transcript)
        except Exception as e:
            return {"escalate": True, "tactic": "N/A", "in_tokens": 0, "out_tokens": 0, "note": f"fail-open: {e}"}


class _CleanSifter:
    def triage(self, transcript):
        return {"escalate": False, "tactic": "N/A", "in_tokens": 5, "out_tokens": 2}

    def triage_safe(self, transcript):
        return self.triage(transcript)


class _FakePipeline:
    def __init__(self, sifter, downstream_result):
        self.sifter = sifter
        self._downstream_result = downstream_result

    def analyze(self, ev):
        self.sifter.triage_safe("dummy transcript")  # mirrors pipeline.py:20
        return self._downstream_result


def test_sifter_fail_open_produces_an_error_verdict_never_a_label():
    # Even though the downstream result claims malicious (what Inspector
    # would conclude given tactic="N/A" after the fail-open), the recorded
    # exception must override it.
    downstream = _FakeDetectionResult(is_malicious=True, confidence=0.9)
    pipeline = _FakePipeline(_FailingSifter(), downstream)
    adapter = AgenticThreatDetectionAdapter(pipeline=pipeline)
    verdict = adapter._analyze_and_normalize("c1", ev=object())
    assert verdict["status"] == "error"
    assert verdict["label"] is None
    assert verdict["rationale"] == "vendor fail-open: RuntimeError"
    assert verdict["tool_name"] == "aidr"


def test_a_clean_sifter_result_is_unaffected():
    downstream = _FakeDetectionResult(is_malicious=False)
    pipeline = _FakePipeline(_CleanSifter(), downstream)
    adapter = AgenticThreatDetectionAdapter(pipeline=pipeline)
    verdict = adapter._analyze_and_normalize("c1", ev=object())
    assert verdict["status"] == "ok"
    assert verdict["label"] == "benign"


def test_the_flag_resets_between_cases_a_prior_fail_open_does_not_leak():
    downstream = _FakeDetectionResult(is_malicious=False)
    pipeline = _FakePipeline(_CleanSifter(), downstream)
    adapter = AgenticThreatDetectionAdapter(pipeline=pipeline)
    adapter._last_sifter_fail_open_exception_class = "StaleException"  # simulates leftover state
    verdict = adapter._analyze_and_normalize("c1", ev=object())
    assert verdict["status"] == "ok"


def test_no_sifter_attribute_degrades_to_a_no_op_wrapper():
    # A partially-constructed/malformed pipeline (same discipline as
    # terminate_subprocesses's existing degrade-to-no-op tests below).
    adapter = AgenticThreatDetectionAdapter(pipeline=SimpleNamespace())  # no .sifter at all
    downstream = _FakeDetectionResult(is_malicious=False)
    adapter._pipeline.analyze = lambda ev: downstream
    verdict = adapter._analyze_and_normalize("c1", ev=object())
    assert verdict["status"] == "ok"


def test_detector_tool_name_is_now_aidr_not_the_old_repo_name():
    assert DETECTOR_TOOL_NAME == "aidr"
