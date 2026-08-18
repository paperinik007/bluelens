import json

from toy_agent.orchestrator import CommandResult, run_test_case

_TEST_CASE = {
    "case_id": "case_001",
    "transcript": {"session_id": "case_001", "turns": [{"seq": 0, "role": "user", "content": "hi", "tool_call": None}], "stop_reason": None},
    "label": "benign", "technique_target": None, "rationale": "smoke test",
}

_TRANSCRIPT_JSON = json.dumps({"session_id": "case_001", "turns": [], "stop_reason": "completed"}).encode()
_VERDICT_JSON = json.dumps({"case_id": "case_001", "tool_name": "x", "status": "ok", "label": "benign"}).encode()
_TRUNCATE_OK = CommandResult(returncode=0, stdout=b"", stderr=b"")  # the thin-proxy log truncation call, always issued right before the detector invocation


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
        _TRUNCATE_OK,
        CommandResult(returncode=0, stdout=_VERDICT_JSON, stderr=b""),
    ])
    result = run_test_case(_TEST_CASE, run_command=runner)
    assert result["transcript"] == json.loads(_TRANSCRIPT_JSON)
    assert result["verdict"] == json.loads(_VERDICT_JSON)
    assert len(runner.calls) == 3
    assert runner.calls[0][0][:4] == ["docker", "compose", "exec", "-T"]
    assert "agent" in runner.calls[0][0]
    assert "detector" in runner.calls[1][0] and "sh" in runner.calls[1][0]  # the truncate call
    assert "detector" in runner.calls[2][0]
    assert runner.calls[2][1] == _TRANSCRIPT_JSON  # agent's stdout piped straight into detector's stdin


def test_verdict_case_id_is_overwritten_with_the_true_case_id():
    # Gap 14, A1: session_id is now an opaque per-invocation UUID (never
    # case_id), so the detector's echoed case_id must never be trusted —
    # the orchestrator already knows the real case_id independently.
    detector_verdict = json.dumps(
        {"case_id": "some-opaque-uuid-the-detector-echoed-back", "tool_name": "x", "status": "ok", "label": "benign"}
    ).encode()
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _TRUNCATE_OK,
        CommandResult(returncode=0, stdout=detector_verdict, stderr=b""),
    ])
    result = run_test_case(_TEST_CASE, run_command=runner)
    assert result["verdict"]["case_id"] == "case_001"


def test_agent_failed_to_start_is_classified_as_infra():
    runner = ScriptedRunner([CommandResult(returncode=-1, stdout=b"", stderr=b"", failed_to_start=True)])
    result = run_test_case(_TEST_CASE, run_command=runner)
    assert result["transcript"] is None
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "infra"
    assert result["verdict"]["label"] is None
    assert len(runner.calls) == 1  # never attempted the truncate or detector invocation


def test_agent_nonzero_exit_is_classified_as_application():
    runner = ScriptedRunner([CommandResult(returncode=1, stdout=b"", stderr=b"bad seed turn")])
    result = run_test_case(_TEST_CASE, run_command=runner)
    assert result["transcript"] is None
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"
    assert "bad seed turn" in result["verdict"]["rationale"]


def test_detector_timeout_is_classified_as_infra_and_triggers_both_cleanup_calls():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _TRUNCATE_OK,
        CommandResult(returncode=-1, stdout=b"", stderr=b"", timed_out=True),
        CommandResult(returncode=0, stdout=b"", stderr=b""),  # pkill detector_adapter.evaluate_case — last-resort fallback
        CommandResult(returncode=0, stdout=b"", stderr=b""),  # pkill aidr/providers — last-resort fallback
    ])
    result = run_test_case(_TEST_CASE, run_command=runner)
    assert result["transcript"] == json.loads(_TRANSCRIPT_JSON)
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "infra"
    assert len(runner.calls) == 5
    assert "detector_adapter.evaluate_case" in runner.calls[3][0]
    assert "aidr/providers" in runner.calls[4][0]


def test_detector_nonzero_exit_with_internal_timeout_in_stderr_triggers_both_cleanup_calls():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _TRUNCATE_OK,
        CommandResult(returncode=1, stdout=b"", stderr=b"evaluate_case failed: TimeoutError"),
        CommandResult(returncode=0, stdout=b"", stderr=b""),  # pkill detector_adapter.evaluate_case — fallback for a hang during adapter construction
        CommandResult(returncode=0, stdout=b"", stderr=b""),  # pkill aidr/providers — same fallback
    ])
    result = run_test_case(_TEST_CASE, run_command=runner)
    assert result["transcript"] == json.loads(_TRANSCRIPT_JSON)
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"  # process exited cleanly — only the cleanup calls fire, no reclassification to infra
    assert len(runner.calls) == 5
    assert "detector_adapter.evaluate_case" in runner.calls[3][0]
    assert "aidr/providers" in runner.calls[4][0]


def test_detector_nonzero_exit_without_timeout_in_stderr_skips_cleanup_calls():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _TRUNCATE_OK,
        CommandResult(returncode=1, stdout=b"", stderr=b"evaluate_case failed: ValueError"),
    ])
    result = run_test_case(_TEST_CASE, run_command=runner)
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"
    assert len(runner.calls) == 3  # no fallback pkill calls — ordinary application error, no internal-deadline signal in stderr


def test_detector_malformed_stdout_despite_exit_zero_is_classified_as_application():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _TRUNCATE_OK,
        CommandResult(returncode=0, stdout=b"noise before json\n" + _VERDICT_JSON, stderr=b""),
    ])
    result = run_test_case(_TEST_CASE, run_command=runner)
    assert result["transcript"] == json.loads(_TRANSCRIPT_JSON)
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"


def test_agent_malformed_stdout_despite_exit_zero_never_reaches_detector():
    runner = ScriptedRunner([CommandResult(returncode=0, stdout=b"not json", stderr=b"")])
    result = run_test_case(_TEST_CASE, run_command=runner)
    assert result["transcript"] is None
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"
    assert len(runner.calls) == 1
