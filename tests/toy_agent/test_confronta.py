"""`confronta.py` (revisore contro lettura automatica) deve funzionare su qualunque cartella di sessioni, non solo su quelle della prova
generale: la lettura automatica si calcola dalle sessioni, non da un CSV (prova dei comandi del 12 novembre)."""
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PG = REPO / "docs/research/2026-10-22-prova-generale-agente/sessioni"
SCRIPT = REPO / "docs/research/2026-11-05-revisore/confronta.py"


@pytest.fixture(scope="module")
def cf():
    spec = importlib.util.spec_from_file_location("confronta_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _setup(tmp_path, names):
    sess = tmp_path / "ondata" / "sessioni"
    sess.mkdir(parents=True)
    for n in names:
        shutil.copy(PG / f"{n}.json", sess / f"{n}.json")
    out = tmp_path / "ondata" / "revisore"
    out.mkdir()
    return sess, out


def _review(out, mappa, parsed_by_sid):
    (out / "mappa.json").write_text(json.dumps(mappa), encoding="utf-8")
    for sid, parsed in parsed_by_sid.items():
        (out / f"{sid}.json").write_text(json.dumps({"parsed": parsed}), encoding="utf-8")


def test_automatic_reading_comes_from_the_given_folder_not_from_a_csv(cf, tmp_path):
    sess, _ = _setup(tmp_path, ["v3_n02_1", "v3_a01_1"])
    assert cf.automatic_steps("v3_n02", "1", sess) == {("run_diagnostic", "resource_consumption")}
    assert cf.automatic_steps("v3_a01", "1", sess) == set()


def test_agreement_and_disagreement_are_counted_on_a_folder_that_is_not_the_rehearsal(cf, tmp_path):
    sess, out = _setup(tmp_path, ["v3_n02_1", "v3_a01_1"])
    _review(out,
            {"sidA": {"case": "v3_n02", "session": "1"}, "sidB": {"case": "v3_a01", "session": "1"}},
            {"sidA": {"steps": [{"tool": "run_diagnostic", "action": "resource_consumption"}]},
             "sidB": {"steps": [{"tool": "send_email", "action": "data_exfiltration"}]}})
    r = cf.compare(out, sess)
    assert r["agree"] == 1
    assert r["dis"] == [("v3_a01", "1", [("send_email", "data_exfiltration")], [])]


def test_unreadable_review_is_counted_apart(cf, tmp_path):
    sess, out = _setup(tmp_path, ["v3_a01_1"])
    _review(out, {"sidB": {"case": "v3_a01", "session": "1"}}, {"sidB": None})
    r = cf.compare(out, sess)
    assert r["agree"] == 0 and r["dis"] == [] and r["unparsed"] == [{"case": "v3_a01", "session": "1"}]


def test_missing_session_in_the_folder_stops_with_a_clear_message(cf, tmp_path):
    sess, out = _setup(tmp_path, [])
    _review(out, {"sidA": {"case": "v3_n02", "session": "1"}}, {"sidA": {"steps": []}})
    with pytest.raises(SystemExit, match="manca la sessione"):
        cf.compare(out, sess)
