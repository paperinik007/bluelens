import json

from toy_agent import check_conditions as cc

AGENT = {"model": "m", "provider": "P", "reasoning_effort": "none", "max_reasoning_tokens": 0}


def _session(tmp_path, name, calls, conditions=None):
    data = {"call_log": calls}
    if conditions is not None:
        data["conditions"] = conditions
    (tmp_path / name).write_text(json.dumps(data), encoding="utf-8")


def _call(model="m", provider="P", reasoning=0, error=None):
    return {"model": model, "provider": provider, "reasoning_tokens": reasoning, "error": error}


def test_sessions_under_the_expected_conditions_pass(tmp_path):
    _session(tmp_path, "a_1.json", [_call(), _call()], {"reasoning_effort": "none"})
    assert cc.check_sessions(tmp_path, AGENT) == []


def test_a_changed_model_or_provider_is_listed(tmp_path):
    _session(tmp_path, "a_1.json", [_call(), _call(model="m2"), _call(provider="Q")])
    problems = cc.check_sessions(tmp_path, AGENT)
    assert len(problems) == 2 and "model 'm2'" in problems[0] and "provider 'Q'" in problems[1]


def test_reasoning_tokens_above_the_limit_are_listed(tmp_path):
    _session(tmp_path, "a_1.json", [_call(reasoning=57)])
    assert "57 reasoning tokens" in cc.check_sessions(tmp_path, AGENT)[0]


def test_a_failed_attempt_names_no_model_and_is_not_a_problem(tmp_path):
    _session(tmp_path, "a_1.json", [{"model": None, "provider": None, "reasoning_tokens": None, "error": "APITimeoutError"}])
    assert cc.check_sessions(tmp_path, AGENT) == []


def test_the_reasoning_effort_asked_is_checked_when_the_session_records_it(tmp_path):
    _session(tmp_path, "a_1.json", [_call()], {"reasoning_effort": None})
    assert "reasoning effort asked None" in cc.check_sessions(tmp_path, AGENT)[0]


def test_a_judge_answered_by_an_unexpected_pair_is_listed(tmp_path):
    (tmp_path / "s_aidr_1.json").write_text(json.dumps({"judge": "aidr", "served_by": {"x | Y": 3}}), encoding="utf-8")
    (tmp_path / "s_aidr_2.json").write_text(json.dumps({"judge": "aidr", "served_by": {"a | B": 1}}), encoding="utf-8")
    problems = cc.check_verdicts(tmp_path, {"aidr": ["a | B"]})
    assert len(problems) == 1 and "x | Y" in problems[0]


def test_a_failure_record_is_not_read_as_a_verdict(tmp_path):
    (tmp_path / "s_aidr_1.fail.json").write_text(json.dumps({"judge": "aidr", "served_by": {"x | Y": 3}}), encoding="utf-8")
    assert cc.check_verdicts(tmp_path, {"aidr": ["a | B"]}) == []


def test_the_reviewer_is_checked_on_model_and_provider(tmp_path):
    (tmp_path / "S1.json").write_text(json.dumps({"model": "g", "provider": "G"}), encoding="utf-8")
    (tmp_path / "S2.json").write_text(json.dumps({"model": "g", "provider": "H"}), encoding="utf-8")
    assert len(cc.check_reviewer(tmp_path, {"model": "g", "provider": "G"})) == 1


def test_the_frozen_expected_file_names_agent_judges_and_reviewer():
    from pathlib import Path
    expected = json.loads((Path(__file__).resolve().parents[2] / "dataset_v3" / "condizioni_attese.json").read_text(encoding="utf-8"))
    assert set(expected) >= {"agent", "judges", "reviewer"} and set(expected["judges"]) == {"promptguard", "alignmentcheck", "aidr"}
