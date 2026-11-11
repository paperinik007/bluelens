import json

from toy_agent.sposta_guasti import move_faults


def _s(path, reason):
    path.write_text(json.dumps({"transcript": {"stop_reason": reason}}), encoding="utf-8")


def test_valid_sessions_stay_and_environment_faults_move(tmp_path):
    s, f = tmp_path / "s", tmp_path / "f"
    s.mkdir()
    for name, reason in [("a_1.json", "completed"), ("a_2.json", "max_turns"), ("b_1.json", "model_error"), ("b_2.json", "max_cost")]:
        _s(s / name, reason)
    moved = move_faults(s, f)
    assert moved == [("b_1.json", "model_error"), ("b_2.json", "max_cost")]
    assert sorted(p.name for p in s.glob("*.json")) == ["a_1.json", "a_2.json"]
    assert sorted(p.name for p in f.glob("*.json")) == ["b_1.json", "b_2.json"]


def test_nothing_is_created_when_there_is_no_fault(tmp_path):
    s, f = tmp_path / "s", tmp_path / "f"
    s.mkdir()
    _s(s / "a_1.json", "completed")
    assert move_faults(s, f) == [] and not f.exists()


def test_a_second_fault_of_the_same_session_keeps_both_files(tmp_path):
    s, f = tmp_path / "s", tmp_path / "f"
    s.mkdir()
    _s(s / "b_1.json", "model_error")
    move_faults(s, f)
    _s(s / "b_1.json", "model_error")
    move_faults(s, f)
    assert len(list(f.glob("b_1*"))) == 2
