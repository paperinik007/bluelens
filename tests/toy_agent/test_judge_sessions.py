"""Runs the judges on saved sessions (pilot, plan part 9): one verdict per call, spend counted from the proxies'
logs, a ceiling that stops the run before it is passed, saved verdicts never redone."""
import json

import pytest

from toy_agent import judge_sessions as js
from toy_agent.orchestrator import CommandResult


def _log_line(cost=None, error=None):
    entry = {"request": {"model": "m"}}
    if error:
        entry["error"] = error
    else:
        entry["response"] = {"model": "m", "usage": {"prompt_tokens": 10, "completion_tokens": 2, **({"cost": cost} if cost is not None else {})}}
    return json.dumps(entry)


def test_the_cost_of_a_verdict_is_the_sum_of_the_costs_the_provider_reported_in_the_log_lines():
    text = "\n".join([_log_line(0.0005), _log_line(0.0007), ""])
    assert js.cost_of_log(text) == (pytest.approx(0.0012), 2, 0)


def test_a_call_with_no_reported_cost_or_with_an_error_is_counted_as_unknown_not_as_free():
    text = "\n".join([_log_line(0.001), _log_line(None), _log_line(error="boom"), "not json", "[marker] x"])
    cost, calls, unknown = js.cost_of_log(text)
    assert cost == pytest.approx(0.001) and calls == 3 and unknown == 2


def test_the_ledger_adds_up_across_runs_and_keeps_the_largest_verdict_cost(tmp_path):
    path = tmp_path / "gasto.json"
    ledger = js.Ledger(path)
    ledger.add("aidr", 0.002)
    ledger.add("alignmentcheck", 0.0035)
    again = js.Ledger(path)  # a restart reads what was written
    assert again.spent == pytest.approx(0.0055) and again.largest == pytest.approx(0.0035) and again.verdicts == 2
    assert again.by_judge == {"aidr": pytest.approx(0.002), "alignmentcheck": pytest.approx(0.0035)}


def test_two_runs_writing_the_same_ledger_do_not_overwrite_each_others_totals(tmp_path):
    path = tmp_path / "g.json"
    first, second = js.Ledger(path), js.Ledger(path)  # both started before either spent anything
    first.add("alignmentcheck", 0.004)
    second.add("promptguard", 0.0)
    first.add("alignmentcheck", 0.003)
    assert js.Ledger(path).spent == pytest.approx(0.007)
    assert second.may_continue(0.02, worst_first=0.0) is True and second.spent == pytest.approx(0.007)  # it looks again


def test_it_stops_before_the_ceiling_would_be_passed_by_the_next_verdict(tmp_path):
    ledger = js.Ledger(tmp_path / "g.json")
    for _ in range(11):
        ledger.add("aidr", 0.20)  # the largest verdict so far is 0.20
    assert ledger.may_continue(2.5, worst_first=0.01) is True    # 2.20 + 0.20 <= 2.5
    ledger.add("aidr", 0.15)
    assert ledger.may_continue(2.5, worst_first=0.01) is False   # 2.35 + 0.20 > 2.5


def test_before_any_verdict_the_worst_case_is_a_prudent_default_not_zero(tmp_path):
    ledger = js.Ledger(tmp_path / "g.json")
    assert ledger.may_continue(0.005, worst_first=0.01) is False
    assert ledger.may_continue(2.5, worst_first=0.01) is True


def test_the_tasks_go_round_by_round_so_that_stopping_early_leaves_every_session_with_the_same_number_of_verdicts(tmp_path):
    sessions = tmp_path / "s"
    sessions.mkdir()
    for name in ("pb", "pa"):
        (sessions / f"{name}.json").write_text("{}", encoding="utf-8")
    out = tmp_path / "out"
    tasks = js.plan_tasks(sessions, "aidr", repeats=2, out=out, ids=None)
    assert [(t.session_id, t.repeat) for t in tasks] == [("pa", 1), ("pb", 1), ("pa", 2), ("pb", 2)]


def test_a_saved_verdict_is_never_redone(tmp_path):
    sessions = tmp_path / "s"
    sessions.mkdir()
    (sessions / "pa.json").write_text("{}", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    (out / "pa_aidr_1.json").write_text("{}", encoding="utf-8")
    tasks = js.plan_tasks(sessions, "aidr", repeats=2, out=out, ids=None)
    assert [(t.session_id, t.repeat) for t in tasks] == [("pa", 2)]


def test_only_the_listed_sessions_are_used_when_a_list_is_given(tmp_path):
    sessions = tmp_path / "s"
    sessions.mkdir()
    for name in ("pa", "pb", "pc"):
        (sessions / f"{name}.json").write_text("{}", encoding="utf-8")
    tasks = js.plan_tasks(sessions, "aidr", repeats=1, out=tmp_path / "o", ids=["pc", "pa"])
    assert [t.session_id for t in tasks] == ["pa", "pc"]


def test_the_compose_command_carries_the_env_files_and_compose_files_before_the_subcommand():
    cmd = js.compose_command(["a.yml", "b.yml"], [".env.aidr"])
    assert cmd == ["docker", "compose", "--env-file", ".env.aidr", "-f", "a.yml", "-f", "b.yml"]
    assert js.compose_command([], []) == ["docker", "compose"]


def test_an_unknown_judge_is_refused():
    with pytest.raises(ValueError, match="unknown judge"):
        js.judge_config("nope")


def test_the_money_judges_have_a_log_to_read_and_promptguard_has_none():
    assert js.judge_config("alignmentcheck").log_path == "/var/log/llamafirewall_proxy.jsonl"
    assert js.judge_config("aidr").log_path == "/var/log/vendor_proxy.jsonl"
    assert js.judge_config("promptguard").log_path is None


class FakeDocker:
    """Answers the docker calls of one verdict: the line count of the log, the evaluation, the new log lines."""

    def __init__(self, verdict, new_log_lines, evaluate_returncode=0):
        self.calls = []
        self.verdict = verdict
        self.new_log_lines = new_log_lines
        self.evaluate_returncode = evaluate_returncode

    def __call__(self, cmd, stdin_bytes, timeout_s):
        self.calls.append((cmd, stdin_bytes))
        joined = " ".join(cmd)
        if "wc -l" in joined:
            return CommandResult(0, b"7\n", b"")
        if "tail -n" in joined:
            return CommandResult(0, ("\n".join(self.new_log_lines) + "\n").encode(), b"")
        return CommandResult(self.evaluate_returncode, json.dumps(self.verdict).encode(), b"boom" if self.evaluate_returncode else b"")


def _task(tmp_path, judge="aidr"):
    sessions = tmp_path / "s"
    sessions.mkdir(exist_ok=True)
    (sessions / "pa.json").write_text(json.dumps({"session_id": "pa", "turns": []}), encoding="utf-8")
    return js.plan_tasks(sessions, judge, repeats=1, out=tmp_path / "out", ids=None)[0]


def test_one_verdict_sends_the_session_on_stdin_saves_the_verdict_with_its_cost_and_adds_to_the_ledger(tmp_path):
    docker = FakeDocker({"case_id": "pa", "status": "ok", "label": "benign"}, [_log_line(0.0004), _log_line(0.0006)])
    ledger = js.Ledger(tmp_path / "g.json")
    ok = js.run_one(_task(tmp_path), ["docker", "compose"], ledger, run_command=docker)
    assert ok is True
    evaluate = [c for c in docker.calls if "evaluate_case" in " ".join(c[0])][0]
    assert json.loads(evaluate[1]) == {"session_id": "pa", "turns": []}
    assert "detector_adapter.vendors.aidr.evaluate_case" in " ".join(evaluate[0])
    saved = json.loads((tmp_path / "out" / "pa_aidr_1.json").read_text(encoding="utf-8"))
    assert saved["verdict"]["label"] == "benign" and saved["cost_usd"] == pytest.approx(0.001) and saved["calls"] == 2
    assert ledger.spent == pytest.approx(0.001)


def test_the_log_is_read_from_the_line_after_the_ones_that_were_there_before(tmp_path):
    docker = FakeDocker({"case_id": "pa", "status": "ok", "label": "benign"}, [_log_line(0.001)])
    js.run_one(_task(tmp_path), ["docker", "compose"], js.Ledger(tmp_path / "g.json"), run_command=docker)
    tail = [c for c in docker.calls if "tail -n" in " ".join(c[0])][0]
    assert "+8" in " ".join(tail[0])  # 7 lines before: read from line 8


def test_promptguard_costs_nothing_and_reads_no_log(tmp_path):
    docker = FakeDocker({"case_id": "pa", "status": "ok", "label": "benign"}, [])
    ledger = js.Ledger(tmp_path / "g.json")
    assert js.run_one(_task(tmp_path, "promptguard"), ["docker", "compose"], ledger, run_command=docker) is True
    assert not any("wc -l" in " ".join(c[0]) for c in docker.calls)
    assert ledger.spent == 0


def test_a_failed_attempt_leaves_a_record_of_why_beside_where_the_verdict_would_be(tmp_path):
    docker = FakeDocker({}, [_log_line(0.0004)], evaluate_returncode=1)
    js.run_one(_task(tmp_path), ["docker", "compose"], js.Ledger(tmp_path / "g.json"), run_command=docker)
    record = json.loads((tmp_path / "out" / "pa_aidr_1.fail.json").read_text(encoding="utf-8"))
    assert record["returncode"] == 1 and record["timed_out"] is False and "boom" in record["stderr_tail"]
    assert record["cost_usd"] == pytest.approx(0.0004)


def test_a_failure_record_does_not_count_as_a_saved_verdict(tmp_path):
    docker = FakeDocker({}, [], evaluate_returncode=1)
    task = _task(tmp_path)
    js.run_one(task, ["docker", "compose"], js.Ledger(tmp_path / "g.json"), run_command=docker)
    again = js.plan_tasks(tmp_path / "s", "aidr", repeats=1, out=tmp_path / "out", ids=None)
    assert [(t.session_id, t.repeat) for t in again] == [("pa", 1)]


def test_a_failed_evaluation_saves_no_verdict_and_returns_false(tmp_path):
    docker = FakeDocker({}, [_log_line(0.0004)], evaluate_returncode=1)
    ledger = js.Ledger(tmp_path / "g.json")
    assert js.run_one(_task(tmp_path), ["docker", "compose"], ledger, run_command=docker) is False
    assert not (tmp_path / "out" / "pa_aidr_1.json").exists()
    assert ledger.spent == pytest.approx(0.0004)  # what the provider charged for the attempt still counts


def _served_line(model, provider):
    response = {"model": model, "usage": {"cost": 0.001}, **({"provider": provider} if provider else {})}
    return json.dumps({"request": {"model": "tier"}, "response": response})


def test_served_by_counts_the_model_and_provider_each_call_was_answered_by():
    text = "\n".join([_served_line("meta/m", "Parasail"), _served_line("meta/m", "Parasail"), _served_line("meta/m", "Novita"),
                      _log_line(error="boom"), "not json"])
    assert js.served_by(text) == {"meta/m | Parasail": 2, "meta/m | Novita": 1}


def test_a_response_that_names_no_provider_is_recorded_as_unknown_not_dropped():
    assert js.served_by(_served_line("meta/m", None)) == {"meta/m | ?": 1}


def test_the_saved_verdict_says_which_model_and_provider_answered(tmp_path):
    docker = FakeDocker({"case_id": "pa", "status": "ok", "label": "benign"}, [_served_line("meta/m", "Parasail")])
    js.run_one(_task(tmp_path), ["docker", "compose"], js.Ledger(tmp_path / "g.json"), run_command=docker)
    saved = json.loads((tmp_path / "out" / "pa_aidr_1.json").read_text(encoding="utf-8"))
    assert saved["served_by"] == {"meta/m | Parasail": 1}


def test_a_failed_attempt_also_says_who_answered(tmp_path):
    docker = FakeDocker({}, [_served_line("meta/m", "Parasail")], evaluate_returncode=1)
    js.run_one(_task(tmp_path), ["docker", "compose"], js.Ledger(tmp_path / "g.json"), run_command=docker)
    failed = json.loads((tmp_path / "out" / "pa_aidr_1.fail.json").read_text(encoding="utf-8"))
    assert failed["served_by"] == {"meta/m | Parasail": 1}


def test_a_verdict_the_judge_marks_as_error_is_a_failed_attempt_not_a_saved_verdict(tmp_path):
    docker = FakeDocker({"case_id": "pa", "status": "error", "label": None}, [_log_line(0.0004)])
    task = _task(tmp_path)
    ledger = js.Ledger(tmp_path / "g.json")
    assert js.run_one(task, ["docker", "compose"], ledger, run_command=docker) is False
    assert not (tmp_path / "out" / "pa_aidr_1.json").exists()
    record = json.loads((tmp_path / "out" / "pa_aidr_1.fail.json").read_text(encoding="utf-8"))
    assert record["verdict_status"] == "error" and record["attempts"] == 1 and record["returncode"] == 0
    assert ledger.spent == pytest.approx(0.0004)
    again = js.plan_tasks(tmp_path / "s", "aidr", repeats=1, out=tmp_path / "out", ids=None)
    assert [(t.session_id, t.repeat) for t in again] == [("pa", 1)]  # a rerun redoes it


def test_the_count_of_attempts_survives_a_rerun(tmp_path):
    docker = FakeDocker({"case_id": "pa", "status": "error", "label": None}, [])
    task = _task(tmp_path)
    for _ in range(2):
        js.run_one(task, ["docker", "compose"], js.Ledger(tmp_path / "g.json"), run_command=docker)
    record = json.loads((tmp_path / "out" / "pa_aidr_1.fail.json").read_text(encoding="utf-8"))
    assert record["attempts"] == 2


def test_after_the_first_attempt_and_two_reruns_a_failed_verdict_is_no_verdict_and_is_not_tried_again(tmp_path):
    docker = FakeDocker({"case_id": "pa", "status": "error", "label": None}, [])
    task = _task(tmp_path)
    for _ in range(3):
        js.run_one(task, ["docker", "compose"], js.Ledger(tmp_path / "g.json"), run_command=docker)
    assert js.plan_tasks(tmp_path / "s", "aidr", repeats=1, out=tmp_path / "out", ids=None) == []
