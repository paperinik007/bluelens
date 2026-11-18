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
    for nome in ("run_card", "agent_loop", "model_client", "tools", "state", "case_card", "prepare_judge_input", "judge_sessions",
                 "discordant_sessions"):
        assert f"src/toy_agent/{nome}.py" in programmi
    assert "docs/research/2026-11-05-revisore/revisore.py" in programmi
    assert {"tests/toy_agent/conformita_piano.py", "tests/toy_agent/test_conformita_piano.py"} <= set(programmi)
    assert set(e.GRUPPI["tabelle_del_run"]) == {"dataset_v3/ondate.json", "dataset_v3/ambito.json", "dataset_v3/condizioni_attese.json"}
    assert "dataset_v3/cases" in e.GRUPPI["schede_e_mondo"] and "dataset_v3/controls" in e.GRUPPI["schede_e_mondo"]


# ---- immagini Docker (docker finto: non servono i servizi) ----

IMMAGINI = {"img": {"nome": "img:latest", "dockerfile": "docker/x/Dockerfile", "contesto": ".", "pip": True},
            "senzapip": {"nome": "sp:latest", "dockerfile": "docker/y/Dockerfile", "contesto": "docker/y", "pip": False}}

DOCKERFILE_X = (b"FROM python:3.11-slim\n# un commento\nCOPY --from=vendor /opt/v /opt/v\nCOPY src/a.py /opt/a.py\n"
                b"COPY src/pkg /opt/pkg\nCOPY cfg.yaml /etc/cfg.yaml\nRUN pip install x\n")


def _repo_img(tmp_path):
    repo = _repo(tmp_path)
    _scrivi(repo, "docker/x/Dockerfile", DOCKERFILE_X)
    _scrivi(repo, "docker/y/Dockerfile", b"FROM ubuntu\nCOPY squid.conf /etc/squid/squid.conf\n")
    _scrivi(repo, "docker/y/squid.conf", b"conf\n")
    _scrivi(repo, "src/a.py", b"print(1)\n")
    _scrivi(repo, "src/pkg/m.py", b"m\n")
    _scrivi(repo, "src/pkg/n.py", b"n\n")
    _scrivi(repo, "cfg.yaml", b"k: v\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "immagini")
    return repo


class DockerFinto:
    """Risponde come docker per `image inspect` e per `run --entrypoint pip|sha256sum`. `dentro`: percorso nell'immagine -> byte."""

    def __init__(self, dentro, ids=None, freeze="a==1\nb==2\n"):
        self.dentro, self.freeze = dentro, freeze
        self.ids = ids or {"img:latest": "sha256:aaa", "sp:latest": "sha256:bbb"}
        self.chiamate = []

    def __call__(self, *args):
        self.chiamate.append(args)
        if args[:2] == ("image", "inspect"):
            if args[-1] not in self.ids:
                raise ValueError(f"no such image {args[-1]}")
            return self.ids[args[-1]] + "\n"
        i = args.index("--entrypoint")
        entrata, nome = args[i + 1], args[i + 2]
        if entrata == "pip":
            return self.freeze
        percorsi = args[i + 3:]
        return "".join(f"{_sha(self.dentro[p])}  {p}\n" for p in percorsi)


def _dentro_giusto():
    return {"/opt/a.py": b"print(1)\n", "/opt/pkg/m.py": b"m\n", "/opt/pkg/n.py": b"n\n", "/etc/cfg.yaml": b"k: v\n",
            "/etc/squid/squid.conf": b"conf\n"}


def test_the_files_a_dockerfile_copies_are_listed_with_their_place_in_the_image_and_in_the_repository(tmp_path):
    repo = _repo_img(tmp_path)
    commit = e._commit(repo)
    mappa = e.file_copiati(repo, commit, "docker/x/Dockerfile", ".")
    assert mappa == {"/opt/a.py": "src/a.py", "/opt/pkg/m.py": "src/pkg/m.py", "/opt/pkg/n.py": "src/pkg/n.py",
                     "/etc/cfg.yaml": "cfg.yaml"}


def test_a_copy_from_another_stage_is_not_a_file_of_the_repository(tmp_path):
    repo = _repo_img(tmp_path)
    mappa = e.file_copiati(repo, e._commit(repo), "docker/x/Dockerfile", ".")
    assert not any(d.startswith("/opt/v") for d in mappa)


def test_the_build_context_decides_where_the_source_files_are(tmp_path):
    repo = _repo_img(tmp_path)
    mappa = e.file_copiati(repo, e._commit(repo), "docker/y/Dockerfile", "docker/y")
    assert mappa == {"/etc/squid/squid.conf": "docker/y/squid.conf"}


def test_the_images_are_recorded_with_identifier_pip_freeze_and_the_files_inside(tmp_path):
    repo = _repo_img(tmp_path)
    r = e.registra_immagini(repo, e._commit(repo), DockerFinto(_dentro_giusto()), IMMAGINI)
    assert r["img"]["id"] == "sha256:aaa" and r["img"]["nome"] == "img:latest"
    assert r["img"]["pip_freeze"] == ["a==1", "b==2"]
    assert r["img"]["pip_freeze_sha256"] == _sha(b"a==1\nb==2\n")
    f = r["img"]["file_copiati"]["/opt/pkg/m.py"]
    assert f == {"sha256": _sha(b"m\n"), "da": "src/pkg/m.py", "rispetto_al_commit": "uguale"}


def test_an_image_without_python_has_no_pip_freeze(tmp_path):
    repo = _repo_img(tmp_path)
    r = e.registra_immagini(repo, e._commit(repo), DockerFinto(_dentro_giusto()), IMMAGINI)
    assert r["senzapip"]["pip_freeze"] is None and r["senzapip"]["pip_freeze_sha256"] is None
    assert "/etc/squid/squid.conf" in r["senzapip"]["file_copiati"]


def test_a_file_with_windows_line_endings_is_the_same_file_and_says_so(tmp_path):
    repo = _repo_img(tmp_path)
    dentro = {**_dentro_giusto(), "/etc/cfg.yaml": b"k: v\r\n"}
    r = e.registra_immagini(repo, e._commit(repo), DockerFinto(dentro), IMMAGINI)
    assert r["img"]["file_copiati"]["/etc/cfg.yaml"]["rispetto_al_commit"] == "uguale con a capo di Windows"


def test_a_file_inside_the_image_that_differs_from_the_commit_is_marked_different(tmp_path):
    repo = _repo_img(tmp_path)
    dentro = {**_dentro_giusto(), "/opt/a.py": b"print(2)\n"}
    r = e.registra_immagini(repo, e._commit(repo), DockerFinto(dentro), IMMAGINI)
    assert r["img"]["file_copiati"]["/opt/a.py"]["rispetto_al_commit"] == "DIVERSO"


def test_the_containers_run_with_no_network_and_never_pull_an_image(tmp_path):
    repo = _repo_img(tmp_path)
    d = DockerFinto(_dentro_giusto())
    e.registra_immagini(repo, e._commit(repo), d, IMMAGINI)
    avvii = [c for c in d.chiamate if c[0] == "run"]
    assert avvii and all("--network" in c and c[c.index("--network") + 1] == "none" and "--rm" in c
                         and c[c.index("--pull") + 1] == "never" for c in avvii)


def test_the_generation_with_images_stops_when_an_image_holds_a_file_different_from_the_commit(tmp_path):
    repo = _repo_img(tmp_path)
    dentro = {**_dentro_giusto(), "/opt/a.py": b"print(2)\n"}
    with pytest.raises(ValueError, match="/opt/a.py"):
        e.genera(repo, "2026-11-17", gruppi=GRUPPI, pin=PIN, docker=DockerFinto(dentro), immagini=IMMAGINI)


def test_the_generation_with_images_puts_them_in_the_list_and_drops_the_manual_item(tmp_path):
    repo = _repo_img(tmp_path)
    x = e.genera(repo, "2026-11-17", gruppi=GRUPPI, pin=PIN, docker=DockerFinto(_dentro_giusto()), immagini=IMMAGINI)
    assert x["immagini"]["img"]["id"] == "sha256:aaa"
    assert not any(v.startswith("immagini:") for v in x["da_registrare_a_mano"])


def _elenco_con_immagini(tmp_path):
    repo = _repo_img(tmp_path)
    return e.genera(repo, "2026-11-17", gruppi=GRUPPI, pin=PIN, docker=DockerFinto(_dentro_giusto()), immagini=IMMAGINI)


def test_images_that_are_the_recorded_ones_have_no_differences(tmp_path):
    x = _elenco_con_immagini(tmp_path)
    assert e.verifica_immagini(x, DockerFinto(_dentro_giusto())) == []


def test_an_image_with_another_identifier_is_reported_and_this_is_what_stops_the_run(tmp_path):
    x = _elenco_con_immagini(tmp_path)
    d = DockerFinto(_dentro_giusto(), ids={"img:latest": "sha256:CAMBIATO", "sp:latest": "sha256:bbb"})
    problemi = e.verifica_immagini(x, d)
    assert len(problemi) == 1 and "img" in problemi[0] and "sha256:CAMBIATO" in problemi[0]


def test_an_image_that_no_longer_exists_is_reported(tmp_path):
    x = _elenco_con_immagini(tmp_path)
    d = DockerFinto(_dentro_giusto(), ids={"sp:latest": "sha256:bbb"})
    assert any("img" in p and "non si trova" in p for p in e.verifica_immagini(x, d))


def test_the_quick_check_does_not_start_any_container(tmp_path):
    x = _elenco_con_immagini(tmp_path)
    d = DockerFinto(_dentro_giusto())
    e.verifica_immagini(x, d)
    assert all(c[:2] == ("image", "inspect") for c in d.chiamate)


def test_the_deep_check_reports_a_changed_pip_freeze_and_a_changed_file(tmp_path):
    x = _elenco_con_immagini(tmp_path)
    d = DockerFinto({**_dentro_giusto(), "/opt/a.py": b"print(2)\n"}, freeze="a==1\nb==3\n")
    problemi = e.verifica_immagini(x, d, a_fondo=True)
    assert any("pip freeze" in p and "img" in p for p in problemi)
    assert any("/opt/a.py" in p for p in problemi)


def test_the_command_line_records_the_images_and_checks_them(tmp_path, capsys):
    repo = _repo_img(tmp_path)
    out = tmp_path / "elenco.json"
    d = DockerFinto(_dentro_giusto())
    assert e.main(["genera", "--repo", str(repo), "--data", "2026-11-17", "--out", str(out), "--con-immagini"],
                  gruppi=GRUPPI, pin=PIN, docker=d, immagini=IMMAGINI) == 0
    assert e.main(["verifica-immagini", str(out)], docker=d) == 0
    assert "nessuna differenza" in capsys.readouterr().out
    cambiato = DockerFinto(_dentro_giusto(), ids={"img:latest": "sha256:X", "sp:latest": "sha256:bbb"})
    assert e.main(["verifica-immagini", str(out)], docker=cambiato) == 1


def test_a_list_without_images_cannot_be_used_to_check_them(tmp_path):
    repo = _repo(tmp_path)
    out = tmp_path / "elenco.json"
    e.main(["genera", "--repo", str(repo), "--data", "2026-11-17", "--out", str(out)], gruppi=GRUPPI, pin=PIN)
    with pytest.raises(SystemExit):
        e.main(["verifica-immagini", str(out)], docker=DockerFinto({}))


def test_the_files_behind_the_label_looks_like_a_test_are_in_the_list_because_the_analysis_reads_them():
    giusti = {"docs/research/2026-11-05-revisore/schede-plausibilita/plausibilita.json",
              "docs/research/2026-11-05-revisore/schede-plausibilita/mappa.json",
              "docs/research/2026-11-05-revisore/istruzioni-plausibilita.md"}
    assert set(e.GRUPPI["etichette_plausibilita"]) == giusti


def test_the_real_list_names_the_three_images_of_the_run():
    assert {i["nome"] for i in e.IMMAGINI.values()} == {
        "agentic-security-audits-detector:latest", "agentic-security-audits-detector-llamafirewall:latest",
        "agentic-security-audits-egress-proxy:latest"}
