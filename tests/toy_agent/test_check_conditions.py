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


def test_a_judge_with_expected_pairs_and_no_record_of_who_answered_is_a_problem(tmp_path):
    (tmp_path / "s_aidr_1.json").write_text(json.dumps({"judge": "aidr", "served_by": {}}), encoding="utf-8")
    (tmp_path / "s_promptguard_1.json").write_text(json.dumps({"judge": "promptguard", "served_by": {}}), encoding="utf-8")
    problems = cc.check_verdicts(tmp_path, {"aidr": ["a | B"], "promptguard": []})
    assert len(problems) == 1 and "s_aidr_1" in problems[0] and "log not read" in problems[0]  # a local judge expects no pairs


def test_the_reviewer_instructions_fingerprint_is_checked_when_the_expected_file_names_it(tmp_path):
    (tmp_path / "S1.json").write_text(json.dumps({"model": "g", "provider": "G"}), encoding="utf-8")
    expected = {"model": "g", "provider": "G", "instructions_sha256": "abc"}
    assert "fingerprint None" in cc.check_reviewer(tmp_path, expected)[0]  # no sistema.sha256 saved
    (tmp_path / "sistema.sha256").write_text("abd", encoding="utf-8")
    assert "fingerprint 'abd'" in cc.check_reviewer(tmp_path, expected)[0]
    (tmp_path / "sistema.sha256").write_text("abc", encoding="utf-8")
    assert cc.check_reviewer(tmp_path, expected) == []


def test_generation_records_must_name_the_dated_version_and_provider(tmp_path):
    sessions = tmp_path / "s"; sessions.mkdir()
    (sessions / "a_1.json").write_text(json.dumps({"call_log": [
        {"generation_id": "g1", "error": None}, {"generation_id": "g2", "error": None},
        {"generation_id": "g3", "error": None}, {"generation_id": "g4", "error": None}, {"generation_id": None, "error": "x"}]}), encoding="utf-8")
    gens = tmp_path / "gens.json"
    gens.write_text(json.dumps({
        "g1": {"model": "m-20260317", "provider_name": "P"},
        "g2": {"model": "m-OTHER", "provider_name": "P"},
        "g3": {"error": "HTTP 404"}}), encoding="utf-8")
    problems = cc.check_generations(sessions, gens, {"version": "m-20260317", "provider": "P"})
    assert len(problems) == 3
    assert any("'m-OTHER'" in p for p in problems) and any("HTTP 404" in p for p in problems) and any("g4" in p and "not fetched" in p for p in problems)


def test_an_answered_call_without_a_generation_id_is_a_problem_not_a_silent_pass(tmp_path):
    sessions = tmp_path / "s"; sessions.mkdir()
    (sessions / "a_1.json").write_text(json.dumps({"call_log": [
        {"generation_id": "g1", "error": None}, {"generation_id": None, "error": None}, {"error": None}]}), encoding="utf-8")
    gens = tmp_path / "gens.json"
    gens.write_text(json.dumps({"g1": {"model": "m-20260317", "provider_name": "P"}}), encoding="utf-8")
    problems = cc.check_generations(sessions, gens, {"version": "m-20260317", "provider": "P"})
    assert len(problems) == 2 and all("answered call without a generation_id" in p for p in problems)
    assert any("call 1" in p for p in problems) and any("call 2" in p for p in problems)


def test_a_failed_call_without_an_identifier_is_still_not_a_problem(tmp_path):
    sessions = tmp_path / "s"; sessions.mkdir()
    (sessions / "a_1.json").write_text(json.dumps({"call_log": [{"generation_id": None, "error": "Timeout"}]}), encoding="utf-8")
    gens = tmp_path / "gens.json"
    gens.write_text("{}", encoding="utf-8")
    assert cc.check_generations(sessions, gens, {"version": "v", "provider": "P"}) == []


def test_the_frozen_expected_file_names_the_dated_version_and_the_instructions_fingerprint():
    from pathlib import Path
    expected = json.loads((Path(__file__).resolve().parents[2] / "dataset_v3" / "condizioni_attese.json").read_text(encoding="utf-8"))
    assert expected["agent"]["version"] == "openai/gpt-5.4-mini-20260317"
    assert len(expected["reviewer"]["instructions_sha256"]) == 64


def test_an_empty_folder_or_a_session_without_call_log_is_a_problem_not_a_silent_pass(tmp_path):
    gens = tmp_path / "gens.json"
    gens.write_text("{}", encoding="utf-8")
    vuota = tmp_path / "vuota"; vuota.mkdir()
    assert any("no session file" in p for p in cc.check_generations(vuota, gens, {"version": "v", "provider": "P"}))
    sessions = tmp_path / "s"; sessions.mkdir()
    (sessions / "senza_chiave_1.json").write_text(json.dumps({"transcript": []}), encoding="utf-8")
    (sessions / "vuoto_1.json").write_text(json.dumps({"call_log": []}), encoding="utf-8")
    problems = cc.check_generations(sessions, gens, {"version": "v", "provider": "P"})
    assert len(problems) == 2 and all("no call_log" in p for p in problems)
