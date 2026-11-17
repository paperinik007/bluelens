"""Test di `toy_agent.elenco_a`: l'elenco A delle impronte (piano, parte 12, «Cosa si congela»). Ogni prova usa un piccolo repository git vero."""
import hashlib
import json
import subprocess

import pytest

from toy_agent import elenco_a as e

GRUPPI = {"g1": ["a.txt", "d"], "g2": ["b.txt"]}
PIN = {"vendor": ("Dockerfile", r"git checkout ([0-9a-f]{40})")}
SHA40 = "7fad14d2478707e68a09b8ecd9942dec8fde1614"


def _git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false", *args],
                   cwd=repo, check=True, capture_output=True, stdin=subprocess.DEVNULL)


def _scrivi(repo, nome, contenuto: bytes):
    p = repo / nome
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(contenuto)


def _repo(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    _git(repo, "init", "-q")
    _scrivi(repo, "a.txt", b"uno\n")
    _scrivi(repo, "d/x.txt", b"x\n")
    _scrivi(repo, "d/y.txt", b"y\n")
    _scrivi(repo, "b.txt", b"b\n")
    _scrivi(repo, "Dockerfile", f"RUN git clone x \\\n && git checkout {SHA40}\n".encode())
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "c1")
    return repo


def _genera(repo, **kw):
    return e.genera(repo, "2026-11-17", gruppi=GRUPPI, pin=PIN, **kw)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def test_the_fingerprint_of_a_file_is_the_sha256_of_what_is_committed(tmp_path):
    repo = _repo(tmp_path)
    x = _genera(repo)
    assert x["gruppi"]["g1"]["file"]["a.txt"] == _sha(b"uno\n")


def test_a_directory_is_expanded_into_its_committed_files_and_untracked_files_are_left_out(tmp_path):
    repo = _repo(tmp_path)
    _scrivi(repo, "d/non_tracciato.txt", b"zzz\n")
    x = _genera(repo)
    assert sorted(x["gruppi"]["g1"]["file"]) == ["a.txt", "d/x.txt", "d/y.txt"]


def test_the_list_records_the_commit_the_date_and_what_each_group_declared(tmp_path):
    repo = _repo(tmp_path)
    x = _genera(repo)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True,
                          stdin=subprocess.DEVNULL).stdout.strip()
    assert x["commit_del_codice"] == head and x["data"] == "2026-11-17"
    assert x["gruppi"]["g1"]["percorsi"] == ["a.txt", "d"]


def test_the_fingerprint_of_a_group_changes_when_any_file_changes_and_not_otherwise(tmp_path):
    repo = _repo(tmp_path)
    prima = _genera(repo)
    assert _genera(repo)["gruppi"]["g1"]["impronta_insieme"] == prima["gruppi"]["g1"]["impronta_insieme"]
    _scrivi(repo, "d/y.txt", b"cambiato\n")
    _git(repo, "commit", "-q", "-am", "c2")
    dopo = _genera(repo)
    assert dopo["gruppi"]["g1"]["impronta_insieme"] != prima["gruppi"]["g1"]["impronta_insieme"]
    assert dopo["gruppi"]["g2"]["impronta_insieme"] == prima["gruppi"]["g2"]["impronta_insieme"]


def test_a_committed_file_modified_in_the_working_copy_stops_the_generation(tmp_path):
    repo = _repo(tmp_path)
    _scrivi(repo, "a.txt", b"modificato\n")
    with pytest.raises(ValueError):
        _genera(repo)


def test_a_declared_path_that_is_not_committed_stops_the_generation(tmp_path):
    repo = _repo(tmp_path)
    with pytest.raises(ValueError):
        e.genera(repo, "2026-11-17", gruppi={"g": ["non_esiste.txt"]}, pin=PIN)


def test_the_commits_and_versions_of_the_vendors_are_read_from_the_dockerfiles(tmp_path):
    repo = _repo(tmp_path)
    assert _genera(repo)["pin_dei_produttori"] == {"vendor": SHA40}


def test_a_vendor_pin_that_cannot_be_found_stops_the_generation(tmp_path):
    repo = _repo(tmp_path)
    with pytest.raises(ValueError):
        e.genera(repo, "2026-11-17", gruppi=GRUPPI, pin={"vendor": ("Dockerfile", r"nulla ([0-9]+)")})


def test_the_images_are_declared_not_yet_recorded_and_the_manual_items_are_listed(tmp_path):
    x = _genera(_repo(tmp_path))
    assert x["immagini"] is None
    assert any("disegno del modello" in voce for voce in x["da_registrare_a_mano"])


def test_the_list_is_the_same_bytes_every_time_so_it_can_be_fingerprinted(tmp_path):
    repo = _repo(tmp_path)
    assert e.in_json(_genera(repo)) == e.in_json(_genera(repo))
    assert json.loads(e.in_json(_genera(repo)))["data"] == "2026-11-17"


def test_a_list_checked_against_the_commit_it_was_made_from_has_no_differences(tmp_path):
    repo = _repo(tmp_path)
    assert e.verifica(repo, _genera(repo)) == []


def test_a_changed_file_is_reported_by_name(tmp_path):
    repo = _repo(tmp_path)
    x = _genera(repo)
    _scrivi(repo, "b.txt", b"nuovo\n")
    _git(repo, "commit", "-q", "-am", "c2")
    problemi = e.verifica(repo, x)
    assert len(problemi) == 1 and "b.txt" in problemi[0] and "cambiato" in problemi[0]


def test_a_file_added_to_a_declared_directory_is_reported(tmp_path):
    repo = _repo(tmp_path)
    x = _genera(repo)
    _scrivi(repo, "d/z.txt", b"z\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "c2")
    problemi = e.verifica(repo, x)
    assert len(problemi) == 1 and "d/z.txt" in problemi[0] and "aggiunto" in problemi[0]


def test_a_file_removed_from_a_declared_directory_is_reported(tmp_path):
    repo = _repo(tmp_path)
    x = _genera(repo)
    _git(repo, "rm", "-q", "d/y.txt")
    _git(repo, "commit", "-q", "-m", "c2")
    problemi = e.verifica(repo, x)
    assert len(problemi) == 1 and "d/y.txt" in problemi[0] and "tolto" in problemi[0]


def test_a_vendor_pin_that_changed_is_reported(tmp_path):
    repo = _repo(tmp_path)
    x = _genera(repo)
    _scrivi(repo, "Dockerfile", b"RUN git checkout " + b"1" * 40 + b"\n")
    _git(repo, "commit", "-q", "-am", "c2")
    problemi = e.verifica(repo, x)
    assert any("vendor" in p for p in problemi)


def test_the_list_keeps_where_each_vendor_pin_was_read_so_the_check_needs_nothing_else(tmp_path):
    x = _genera(_repo(tmp_path))
    assert x["origine_dei_pin"]["vendor"]["file"] == "Dockerfile"


def test_the_check_can_be_made_against_the_commit_the_list_was_made_from_even_after_later_commits(tmp_path):
    repo = _repo(tmp_path)
    x = _genera(repo)
    _scrivi(repo, "b.txt", b"nuovo\n")
    _git(repo, "commit", "-q", "-am", "c2")
    assert e.verifica(repo, x, commit=x["commit_del_codice"]) == []


def test_a_list_whose_group_fingerprint_does_not_match_its_own_files_is_reported(tmp_path):
    repo = _repo(tmp_path)
    x = _genera(repo)
    x["gruppi"]["g2"]["impronta_insieme"] = "0" * 64
    assert any("g2" in p and "insieme" in p for p in e.verifica(repo, x))


def test_the_command_line_writes_the_list_and_then_checks_it_without_differences(tmp_path, capsys):
    repo = _repo(tmp_path)
    out = tmp_path / "elenco.json"
    assert e.main(["genera", "--repo", str(repo), "--data", "2026-11-17", "--out", str(out)], gruppi=GRUPPI, pin=PIN) == 0
    assert out.exists()
    assert e.main(["verifica", str(out), "--repo", str(repo)]) == 0
    assert "nessuna differenza" in capsys.readouterr().out


def test_the_command_line_never_overwrites_an_existing_list(tmp_path):
    repo = _repo(tmp_path)
    out = tmp_path / "elenco.json"
    out.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError):
        e.main(["genera", "--repo", str(repo), "--data", "2026-11-17", "--out", str(out)], gruppi=GRUPPI, pin=PIN)
    assert out.read_text(encoding="utf-8") == "{}"


def test_the_command_line_check_exits_with_1_and_names_the_difference(tmp_path, capsys):
    repo = _repo(tmp_path)
    out = tmp_path / "elenco.json"
    e.main(["genera", "--repo", str(repo), "--data", "2026-11-17", "--out", str(out)], gruppi=GRUPPI, pin=PIN)
    _scrivi(repo, "b.txt", b"nuovo\n")
    _git(repo, "commit", "-q", "-am", "c2")
    assert e.main(["verifica", str(out), "--repo", str(repo)]) == 1
    assert "b.txt" in capsys.readouterr().out


def test_the_real_list_declares_the_programs_and_tables_the_plan_names():
    programmi = e.GRUPPI["programmi"]
    for nome in ("src/toy_agent/analisi_v3.py", "tests/toy_agent/test_analisi_v3.py", "src/toy_agent/ondate.py",
                 "src/toy_agent/ambito.py", "src/toy_agent/check_conditions.py", "src/toy_agent/sposta_guasti.py",
                 "src/toy_agent/registra_versioni.py", "docs/research/2026-11-05-revisore/confronta.py",
                 "src/toy_agent/malicious_steps.py", "src/toy_agent/elenco_a.py"):
        assert nome in programmi
    assert set(e.GRUPPI["tabelle_del_run"]) == {"dataset_v3/ondate.json", "dataset_v3/ambito.json", "dataset_v3/condizioni_attese.json"}
    assert "dataset_v3/cases" in e.GRUPPI["schede_e_mondo"] and "dataset_v3/controls" in e.GRUPPI["schede_e_mondo"]
