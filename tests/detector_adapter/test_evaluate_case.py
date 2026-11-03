import io
import json
import signal
import time

import pytest

import detector_adapter.vendors.aidr.evaluate_case as evaluate_case_module
from detector_adapter.vendors.aidr.adapter import HALVARD_VERSIONS
from detector_adapter.vendors.aidr.evaluate_case import run_evaluate_case


class FakeAdapter:
    def __init__(self, result=None, raises=None):
        self._result = result
        self._raises = raises
        self.terminate_called = False

    def evaluate(self, transcript):
        if self._raises is not None:
            raise self._raises
        return self._result

    def terminate_subprocesses(self):
        self.terminate_called = True


class NoisyFakeAdapter(FakeAdapter):
    """Simulates real vendor Inspector code (pinned aidr commit): it prints
    tool-use tracing directly to stdout via a bare print(), not the logging
    module, whenever it invokes a tool during analysis (Gap 11, found live
    during Plan 4's Task 8 manual verification — the vendor's tracing lines
    landed on the same stdout stream evaluate_case.py writes its verdict
    JSON to, breaking json.loads() on the combined output)."""

    def evaluate(self, transcript):
        print("[inspector] tool_use: get_source_code(server_names=['toy_support'])")
        return super().evaluate(transcript)


class SlowFakeAdapter(FakeAdapter):
    """Sleeps past the internal deadline before returning — the only way to
    exercise the real signal.setitimer mechanism without mocking signal
    itself, which would defeat the point of testing it."""

    def __init__(self, sleep_s, result):
        super().__init__(result=result)
        self._sleep_s = sleep_s

    def evaluate(self, transcript):
        time.sleep(self._sleep_s)
        return super().evaluate(transcript)


def test_run_evaluate_case_returns_the_adapter_result_unchanged():
    fake_verdict = {"case_id": "c1", "tool_name": "x", "status": "ok", "label": "benign"}
    result = run_evaluate_case({"session_id": "c1", "turns": []}, FakeAdapter(result=fake_verdict))
    assert result == fake_verdict


@pytest.fixture(autouse=True)
def third_party_paths(tmp_path, monkeypatch):
    """main() puts the session's version of the integration at the registered path; here that is a temp dir."""
    versions = tmp_path / "versions"
    versions.mkdir()
    for version in HALVARD_VERSIONS:
        (versions / f"{version}.py").write_bytes(f"# code of {version}\n".encode())
    target = tmp_path / "servers" / "halvard_crm" / "halvard_crm.py"
    monkeypatch.setattr(evaluate_case_module, "HALVARD_VERSIONS_DIR", versions)
    monkeypatch.setattr(evaluate_case_module, "HALVARD_TARGET", target)
    return target


def test_main_installs_the_sessions_version_before_evaluating_and_reports_which_in_the_verdict(
        monkeypatch, capsys, third_party_paths):
    import hashlib

    seen = {}

    class Reading(FakeAdapter):
        def evaluate(self, transcript):
            seen["code_when_evaluated"] = third_party_paths.read_text(encoding="utf-8")
            return super().evaluate(transcript)

    session = {"session_id": "c1", "turns": [], "third_party_version": "compromised_data"}
    monkeypatch.setattr(evaluate_case_module.sys, "stdin", io.StringIO(json.dumps(session)))
    monkeypatch.setattr(evaluate_case_module, "AgenticThreatDetectionAdapter",
                        lambda: Reading(result={"case_id": "c1", "tool_name": "aidr", "status": "ok", "label": "benign"}))
    evaluate_case_module.main()
    verdict = json.loads(capsys.readouterr().out)
    assert seen["code_when_evaluated"] == "# code of compromised_data\n"
    assert verdict["third_party_version"] == "compromised_data"
    assert verdict["third_party_sha256"] == hashlib.sha256(b"# code of compromised_data\n").hexdigest()


def test_main_exits_nonzero_if_the_version_cannot_be_installed_never_evaluating_with_the_wrong_code(
        monkeypatch, capsys):
    session = {"session_id": "c1", "turns": [], "third_party_version": "backdoored"}
    monkeypatch.setattr(evaluate_case_module.sys, "stdin", io.StringIO(json.dumps(session)))
    monkeypatch.setattr(evaluate_case_module, "AgenticThreatDetectionAdapter",
                        lambda: FakeAdapter(result={"case_id": "c1", "status": "ok", "label": "benign"}))
    with pytest.raises(SystemExit) as exc_info:
        evaluate_case_module.main()
    assert exc_info.value.code == 1 and capsys.readouterr().out == ""


def test_main_writes_only_the_verdict_json_to_stdout(monkeypatch, capsys):
    fake_verdict = {"case_id": "c1", "tool_name": "x", "status": "ok", "label": "malicious"}
    monkeypatch.setattr(evaluate_case_module.sys, "stdin", io.StringIO(json.dumps({"session_id": "c1", "turns": []})))
    monkeypatch.setattr(evaluate_case_module, "AgenticThreatDetectionAdapter", lambda: FakeAdapter(result=fake_verdict))
    evaluate_case_module.main()
    captured = capsys.readouterr()
    assert captured.err == ""
    assert fake_verdict.items() <= json.loads(captured.out).items()  # the verdict, plus which version of the integration


def test_main_isolates_vendor_stdout_noise_from_the_verdict_json(monkeypatch, capsys):
    fake_verdict = {"case_id": "c1", "tool_name": "x", "status": "ok", "label": "malicious"}
    monkeypatch.setattr(evaluate_case_module.sys, "stdin", io.StringIO(json.dumps({"session_id": "c1", "turns": []})))
    monkeypatch.setattr(evaluate_case_module, "AgenticThreatDetectionAdapter", lambda: NoisyFakeAdapter(result=fake_verdict))
    evaluate_case_module.main()
    captured = capsys.readouterr()
    assert fake_verdict.items() <= json.loads(captured.out).items()  # the verdict, plus which version of the integration
    assert "tool_use" in captured.err


def test_main_exits_nonzero_on_adapter_exception_never_touching_stdout(monkeypatch, capsys):
    monkeypatch.setattr(evaluate_case_module.sys, "stdin", io.StringIO(json.dumps({"session_id": "c1", "turns": []})))
    monkeypatch.setattr(evaluate_case_module, "AgenticThreatDetectionAdapter", lambda: FakeAdapter(raises=RuntimeError("boom")))
    with pytest.raises(SystemExit) as exc_info:
        evaluate_case_module.main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "evaluate_case failed" in captured.err


@pytest.mark.skipif(not hasattr(signal, "SIGALRM"), reason="SIGALRM is Unix-only — the detector container is Linux-only by design, this test only runs where the real deadline mechanism exists")
def test_main_terminates_subprocesses_and_exits_nonzero_on_internal_deadline(monkeypatch, capsys):
    slow_adapter = SlowFakeAdapter(sleep_s=0.15, result={"case_id": "c1", "tool_name": "x", "status": "ok", "label": "benign"})
    monkeypatch.setenv("EVALUATE_CASE_DEADLINE_S", "0.05")
    monkeypatch.setattr(evaluate_case_module.sys, "stdin", io.StringIO(json.dumps({"session_id": "c1", "turns": []})))
    monkeypatch.setattr(evaluate_case_module, "AgenticThreatDetectionAdapter", lambda: slow_adapter)
    with pytest.raises(SystemExit) as exc_info:
        evaluate_case_module.main()
    assert exc_info.value.code == 1
    assert slow_adapter.terminate_called is True
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "TimeoutError" in captured.err
