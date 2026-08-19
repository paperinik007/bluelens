import pytest

from toy_agent.orchestrator import CommandResult
from toy_agent.sequence import CloseStep, CommandStep, OpenStep, validate_sequence, _close_container, _open_container


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
