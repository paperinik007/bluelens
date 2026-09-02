import json
import shlex
from datetime import datetime

import pytest

from toy_agent.orchestrator import CommandResult, VENDOR_DETECTOR_CONFIG, run_test_case

_TEST_CASE = {
    "case_id": "case_001",
    "transcript": {"session_id": "case_001", "turns": [{"seq": 0, "role": "user", "content": "hi", "tool_call": None}], "stop_reason": None},
    "label": "benign", "technique_target": None, "rationale": "smoke test",
}

_TRANSCRIPT_JSON = json.dumps({"session_id": "case_001", "turns": [], "stop_reason": "completed"}).encode()
_VERDICT_JSON = json.dumps({"case_id": "case_001", "tool_name": "x", "status": "ok", "label": "benign"}).encode()
_MARKER_OK = CommandResult(returncode=0, stdout=b"", stderr=b"")


class ScriptedRunner:
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
    result = run_test_case(_TEST_CASE, command_index=0, vendor="aidr", run_command=runner)
    assert result["transcript"] == json.loads(_TRANSCRIPT_JSON)
    assert result["verdict"] == json.loads(_VERDICT_JSON)
    assert len(runner.calls) == 3
    assert runner.calls[0][0][:4] == ["docker", "compose", "exec", "-T"]
    assert "agent" in runner.calls[0][0]
    assert "detector" in runner.calls[1][0] and "sh" in runner.calls[1][0]
    assert "detector" in runner.calls[2][0]
    assert runner.calls[2][1] == _TRANSCRIPT_JSON


def test_thin_proxy_log_is_appended_with_a_json_marker_never_truncated():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        CommandResult(returncode=0, stdout=_VERDICT_JSON, stderr=b""),
    ])
    run_test_case(_TEST_CASE, command_index=7, vendor="aidr", run_command=runner)

    marker_cmd = runner.calls[1][0]
    shell_arg = marker_cmd[-1]
    assert ">>" in shell_arg
    assert shell_arg.count(">") == 2

    tokens = shlex.split(shell_arg)
    marker_json = json.loads(tokens[1])
    assert marker_json["marker"] is True
    assert marker_json["case_id"] == "case_001"
    assert marker_json["command_index"] == 7
    datetime.fromisoformat(marker_json["timestamp"])
    assert "/var/log/vendor_proxy.jsonl" in shell_arg  # aidr's legacy path, unchanged


def test_secondary_log_is_also_marked_when_configured():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        _MARKER_OK,
        CommandResult(returncode=0, stdout=_VERDICT_JSON, stderr=b""),
    ])
    run_test_case(_TEST_CASE, command_index=3, vendor="llamafirewall-combined", run_command=runner)

    assert len(runner.calls) == 4
    secondary_marker_cmd = runner.calls[2][0]
    shell_arg = secondary_marker_cmd[-1]
    tokens = shlex.split(shell_arg)
    marker_json = json.loads(tokens[1])
    assert marker_json["marker"] is True
    assert marker_json["case_id"] == "case_001"
    assert marker_json["command_index"] == 3
    assert "/var/log/llamafirewall_promptguard_raw.jsonl" in shell_arg


def test_no_secondary_marker_when_secondary_log_path_is_none():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        CommandResult(returncode=0, stdout=_VERDICT_JSON, stderr=b""),
    ])
    run_test_case(_TEST_CASE, command_index=0, vendor="aidr", run_command=runner)
    assert len(runner.calls) == 3  # unchanged: no secondary marker for aidr


def test_verdict_case_id_is_overwritten_with_the_true_case_id():
    detector_verdict = json.dumps(
        {"case_id": "some-opaque-uuid-the-detector-echoed-back", "tool_name": "x", "status": "ok", "label": "benign"}
    ).encode()
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        CommandResult(returncode=0, stdout=detector_verdict, stderr=b""),
    ])
    result = run_test_case(_TEST_CASE, command_index=0, vendor="aidr", run_command=runner)
    assert result["verdict"]["case_id"] == "case_001"


def test_agent_failed_to_start_is_classified_as_infra():
    runner = ScriptedRunner([CommandResult(returncode=-1, stdout=b"", stderr=b"", failed_to_start=True)])
    result = run_test_case(_TEST_CASE, command_index=0, vendor="aidr", run_command=runner)
    assert result["transcript"] is None
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "infra"
    assert result["verdict"]["label"] is None
    assert len(runner.calls) == 1


def test_agent_nonzero_exit_is_classified_as_application():
    runner = ScriptedRunner([CommandResult(returncode=1, stdout=b"", stderr=b"bad seed turn")])
    result = run_test_case(_TEST_CASE, command_index=0, vendor="aidr", run_command=runner)
    assert result["transcript"] is None
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"
    assert "bad seed turn" in result["verdict"]["rationale"]


def test_detector_timeout_is_classified_as_infra_and_triggers_both_cleanup_calls_for_aidr():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        CommandResult(returncode=-1, stdout=b"", stderr=b"", timed_out=True),
        CommandResult(returncode=0, stdout=b"", stderr=b""),  # pkill evaluate_case module
        CommandResult(returncode=0, stdout=b"", stderr=b""),  # pkill aidr/providers — aidr-only fallback
    ])
    result = run_test_case(_TEST_CASE, command_index=0, vendor="aidr", run_command=runner)
    assert result["transcript"] == json.loads(_TRANSCRIPT_JSON)
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "infra"
    assert len(runner.calls) == 5
    assert "detector_adapter.vendors.aidr.evaluate_case" in runner.calls[3][0]
    assert "aidr/providers" in runner.calls[4][0]


def test_detector_timeout_triggers_a_single_cleanup_call_for_llamafirewall():
    # llamafirewall spawns no internal subprocesses (no MCP providers) — the
    # aidr-only second pkill fallback does not apply; only 4 calls total,
    # not 5.
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        CommandResult(returncode=-1, stdout=b"", stderr=b"", timed_out=True),
        CommandResult(returncode=0, stdout=b"", stderr=b""),  # pkill evaluate_case module (only one)
    ])
    result = run_test_case(_TEST_CASE, command_index=0, vendor="llamafirewall", run_command=runner)
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "infra"
    assert len(runner.calls) == 4
    assert "detector-llamafirewall" in runner.calls[2][0]
    assert "detector_adapter.vendors.llamafirewall.evaluate_case" in runner.calls[3][0]


def test_detector_nonzero_exit_with_internal_timeout_in_stderr_triggers_both_cleanup_calls_for_aidr():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        CommandResult(returncode=1, stdout=b"", stderr=b"evaluate_case failed: TimeoutError"),
        CommandResult(returncode=0, stdout=b"", stderr=b""),
        CommandResult(returncode=0, stdout=b"", stderr=b""),
    ])
    result = run_test_case(_TEST_CASE, command_index=0, vendor="aidr", run_command=runner)
    assert result["transcript"] == json.loads(_TRANSCRIPT_JSON)
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"
    assert len(runner.calls) == 5
    assert "detector_adapter.vendors.aidr.evaluate_case" in runner.calls[3][0]
    assert "aidr/providers" in runner.calls[4][0]


def test_detector_nonzero_exit_without_timeout_in_stderr_skips_cleanup_calls():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        CommandResult(returncode=1, stdout=b"", stderr=b"evaluate_case failed: ValueError"),
    ])
    result = run_test_case(_TEST_CASE, command_index=0, vendor="aidr", run_command=runner)
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"
    assert len(runner.calls) == 3


def test_detector_malformed_stdout_despite_exit_zero_is_classified_as_application():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _MARKER_OK,
        CommandResult(returncode=0, stdout=b"noise before json\n" + _VERDICT_JSON, stderr=b""),
    ])
    result = run_test_case(_TEST_CASE, command_index=0, vendor="aidr", run_command=runner)
    assert result["transcript"] == json.loads(_TRANSCRIPT_JSON)
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"


def test_agent_malformed_stdout_despite_exit_zero_never_reaches_detector():
    runner = ScriptedRunner([CommandResult(returncode=0, stdout=b"not json", stderr=b"")])
    result = run_test_case(_TEST_CASE, command_index=0, vendor="aidr", run_command=runner)
    assert result["transcript"] is None
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"
    assert len(runner.calls) == 1


def test_secondary_log_path_defaults_to_none_for_aidr_and_llamafirewall():
    assert VENDOR_DETECTOR_CONFIG["aidr"].secondary_log_path is None
    assert VENDOR_DETECTOR_CONFIG["llamafirewall"].secondary_log_path is None


def test_llamafirewall_combined_config_reuses_the_shared_detector_container():
    config = VENDOR_DETECTOR_CONFIG["llamafirewall-combined"]
    assert config.service == "detector-llamafirewall"
    assert config.module == "detector_adapter.vendors.llamafirewall.evaluate_case_combined"
    assert config.tool_name == "llamafirewall-combined"
    assert config.proxy_log_path == "/var/log/llamafirewall_proxy.jsonl"
    assert config.secondary_log_path == "/var/log/llamafirewall_promptguard_raw.jsonl"
    assert config.extra_pkill_pattern is None
    assert config.supports_technique_attribution is False


@pytest.mark.parametrize("vendor,expected_tool_name", [
    ("aidr", "aidr"),
    ("llamafirewall", "llamafirewall-alignmentcheck"),
    ("llamafirewall-combined", "llamafirewall-combined"),
])
def test_error_verdict_tool_name_matches_the_active_vendor(vendor, expected_tool_name):
    runner = ScriptedRunner([CommandResult(returncode=-1, stdout=b"", stderr=b"", failed_to_start=True)])
    result = run_test_case(_TEST_CASE, command_index=0, vendor=vendor, run_command=runner)
    assert result["verdict"]["tool_name"] == expected_tool_name


def test_vendor_is_a_required_keyword_argument():
    with pytest.raises(TypeError):
        run_test_case(_TEST_CASE, command_index=0, run_command=ScriptedRunner([]))  # type: ignore[call-arg]


def test_unknown_vendor_raises_a_clear_error():
    with pytest.raises(KeyError):
        run_test_case(_TEST_CASE, command_index=0, vendor="not-a-real-vendor", run_command=ScriptedRunner([]))
