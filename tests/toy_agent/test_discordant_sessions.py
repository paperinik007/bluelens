import json

from toy_agent.discordant_sessions import discordant


def _v(tmp_path, sid, judge, repeat, label, status="ok"):
    verdict = {"status": status, "label": label} if label else {"status": status}
    (tmp_path / f"{sid}_{judge}_{repeat}.json").write_text(json.dumps(
        {"session_id": sid, "judge": judge, "repeat": str(repeat), "verdict": verdict}))


def test_only_sessions_whose_first_two_labels_differ_are_listed(tmp_path):
    for sid, a, b in (("s1", "malicious", "malicious"), ("s2", "malicious", "benign"), ("s3", "benign", "benign")):
        _v(tmp_path, sid, "aidr", 1, a); _v(tmp_path, sid, "aidr", 2, b)
    assert discordant(tmp_path, "aidr") == ["s2"]


def test_a_session_that_already_has_a_third_verdict_is_left_out(tmp_path):
    _v(tmp_path, "s2", "aidr", 1, "malicious"); _v(tmp_path, "s2", "aidr", 2, "benign"); _v(tmp_path, "s2", "aidr", 3, "benign")
    assert discordant(tmp_path, "aidr") == []


def test_an_error_verdict_or_a_missing_second_verdict_is_not_a_disagreement(tmp_path):
    _v(tmp_path, "e1", "aidr", 1, "malicious"); _v(tmp_path, "e1", "aidr", 2, None, status="error")
    _v(tmp_path, "o1", "aidr", 1, "malicious")
    assert discordant(tmp_path, "aidr") == []


def test_other_judges_and_failure_files_are_ignored(tmp_path):
    _v(tmp_path, "s2", "alignmentcheck", 1, "malicious"); _v(tmp_path, "s2", "alignmentcheck", 2, "benign")
    (tmp_path / "s2_aidr_1.fail.json").write_text("{}")
    assert discordant(tmp_path, "aidr") == []
    assert discordant(tmp_path, "alignmentcheck") == ["s2"]


def test_the_real_control_verdicts_all_have_three_verdicts_so_nothing_is_asked_again():
    from pathlib import Path
    real = Path(__file__).resolve().parents[2] / "docs/research/2026-11-11-campioni-controllo/verdetti"
    if not real.exists():
        return
    for judge in ("alignmentcheck", "aidr", "promptguard"):
        assert discordant(real, judge) == []
