import json
import urllib.error

from toy_agent import registra_versioni as rv


def _sessions(tmp_path, ids):
    s = tmp_path / "sessioni"; s.mkdir()
    (s / "a_1.json").write_text(json.dumps({"call_log": [{"generation_id": i, "error": None} for i in ids]
                                             + [{"generation_id": None, "error": "timeout"}]}), encoding="utf-8")
    return s


def test_every_answered_call_gets_its_record_and_a_failed_attempt_is_skipped(tmp_path):
    s = _sessions(tmp_path, ["g1", "g2"])
    seen = []

    def fetch(gid):
        seen.append(gid)
        return {"model": "m-20260317", "provider_name": "P", "created_at": "t", "native_tokens_reasoning": 0, "secret": "x"}

    out = tmp_path / "gens.json"
    assert rv.collect(s, out, fetch, sleep=lambda s: None) == (2, 0)
    records = json.loads(out.read_text(encoding="utf-8"))
    assert seen == ["g1", "g2"] and records["g1"]["model"] == "m-20260317" and "secret" not in records["g1"]


def test_a_record_not_ready_is_retried_and_one_that_never_comes_is_saved_as_an_error(tmp_path):
    s = _sessions(tmp_path, ["g1", "g2"])
    calls = {"g1": 0}

    def fetch(gid):
        if gid == "g1":
            calls["g1"] += 1
            if calls["g1"] < 3:
                raise urllib.error.HTTPError("u", 404, "not found", {}, None)
            return {"model": "m", "provider_name": "P"}
        raise urllib.error.HTTPError("u", 404, "not found", {}, None)

    out = tmp_path / "gens.json"
    assert rv.collect(s, out, fetch, sleep=lambda s: None) == (1, 1)
    records = json.loads(out.read_text(encoding="utf-8"))
    assert calls["g1"] == 3 and records["g1"]["model"] == "m" and records["g2"] == {"error": "HTTP 404"}


def test_a_record_already_saved_is_not_fetched_again_but_an_error_is_retried(tmp_path):
    s = _sessions(tmp_path, ["g1", "g2"])
    out = tmp_path / "gens.json"
    out.write_text(json.dumps({"g1": {"model": "m", "provider_name": "P"}, "g2": {"error": "HTTP 404"}}), encoding="utf-8")
    seen = []
    rv.collect(s, out, lambda gid: seen.append(gid) or {"model": "m2", "provider_name": "P"}, sleep=lambda s: None)
    assert seen == ["g2"]
