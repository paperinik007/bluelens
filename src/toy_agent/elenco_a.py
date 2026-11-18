"""The list A of the fingerprints (plan, part 12, «Cosa si congela»): generates it and checks it.

    python -m toy_agent.elenco_a genera --data 2026-11-17 --out ELENCO.json
    python -m toy_agent.elenco_a verifica ELENCO.json [--commit REV]

The fingerprint of a file is the SHA-256 of what is COMMITTED (`git cat-file blob`), never of the working copy: on a machine with
`autocrlf` the bytes on disk differ, and whoever clones the repository must recompute the same numbers. The list refuses to be made
with tracked files modified, and never overwrites a list that exists. It reads no `.env` file: the models in use are checked by
`check_conditions` against `dataset_v3/condizioni_attese.json`, which is in the list. The images (identifier, pip freeze, files copied
inside, `docker save`) need Docker running and are recorded in a later step: here they are declared «not yet recorded».
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

REV = "docs/research/2026-11-05-revisore"

# What the plan freezes and that lives in the repository: group -> files and directories (every tracked file inside is listed).
GRUPPI: dict[str, list[str]] = {
    "schede_e_mondo": ["dataset_v3/cases", "dataset_v3/world_base.yaml", "dataset_v3/servers", "dataset_v3/controls"],
    "tabelle_del_run": ["dataset_v3/ondate.json", "dataset_v3/ambito.json", "dataset_v3/condizioni_attese.json"],
    "documenti": ["docs/design/2026-10-11-piano-run-v3.md", "docs/design/2026-10-14-tabella-permessi-bozza.md",
                  "docs/design/2026-10-19-mondo-base.md", "docs/design/2026-10-11-sfere-giudici.md",
                  "docs/design/2026-11-05-limiti-dichiarati-run-v3.md"],
    "istruzioni": [f"{REV}/istruzioni-revisore.md", f"{REV}/istruzioni-schede.md"],
    # the label «sembra un test» that `analisi_v3` reads (plan, part 13, point 8): fixed before the verdicts, so it is in the list
    "etichette_plausibilita": [f"{REV}/istruzioni-plausibilita.md", f"{REV}/schede-plausibilita/plausibilita.json",
                               f"{REV}/schede-plausibilita/mappa.json"],
    "programmi": ["src/toy_agent/analisi_v3.py", "tests/toy_agent/test_analisi_v3.py", "src/toy_agent/elenco_a.py",
                  "tests/toy_agent/test_elenco_a.py", "src/toy_agent/ondate.py", "src/toy_agent/ambito.py",
                  "src/toy_agent/check_conditions.py", "src/toy_agent/sposta_guasti.py", "src/toy_agent/registra_versioni.py",
                  "src/toy_agent/malicious_steps.py", f"{REV}/confronta.py",
                  # the chain that produces the sessions, the verdicts and the readings the numbers come from (external check, 17 Nov)
                  "src/toy_agent/run_card.py", "src/toy_agent/agent_loop.py", "src/toy_agent/model_client.py",
                  "src/toy_agent/tools.py", "src/toy_agent/state.py", "src/toy_agent/case_card.py",
                  "src/toy_agent/prepare_judge_input.py", "src/toy_agent/judge_sessions.py",
                  "src/toy_agent/discordant_sessions.py", f"{REV}/revisore.py"],
    "ambiente": ["docker", "docker-compose.yml"],
}

# Where the versions of the vendors are pinned: name -> (file, expression with one group). Read from the Dockerfiles.
PIN: dict[str, tuple[str, str]] = {
    "aidr_commit": ("docker/detector/Dockerfile", r"git checkout ([0-9a-f]{40})"),
    "llamafirewall_versione": ("docker/detector-llamafirewall/Dockerfile", r"llamafirewall==([0-9][0-9.]*[0-9])"),
}

# The three images of the run (plan, part 12, point 4). `contesto`: the build context of compose; `pip`: whether the image has Python.
IMMAGINI: dict[str, dict] = {
    "aidr": {"nome": "agentic-security-audits-detector:latest", "dockerfile": "docker/detector/Dockerfile", "contesto": ".", "pip": True},
    "llamafirewall": {"nome": "agentic-security-audits-detector-llamafirewall:latest",
                      "dockerfile": "docker/detector-llamafirewall/Dockerfile", "contesto": ".", "pip": True},
    "proxy_in_uscita": {"nome": "agentic-security-audits-egress-proxy:latest", "dockerfile": "docker/egress-proxy/Dockerfile",
                        "contesto": "docker/egress-proxy", "pip": False},
}

DA_REGISTRARE_A_MANO = [
    "disegno del modello (pagina pubblicata, versione 34 o successiva): versione e impronta del testo pubblicato",
    "valori usati di .env.aidr e .env.llamafirewall (modelli e fornitori, mai le chiavi): li confronta check_conditions",
    "PurpleLlama 4be64c3 (piano, parte 10) e documentario: nessun Dockerfile lo scarica; il codice eseguito e llamafirewall==1.0.3, "
    "identificato dal pin letto dal Dockerfile e dall'identificativo dell'immagine",
    "immagini: identificativo, pip freeze e file copiati dentro si registrano con genera --con-immagini (Docker acceso)",
    "archivio docker save delle immagini: NON conservato (decisione del proprietario, 17 novembre: circa 14 GB, disco limitato); le "
    "immagini restano in Docker e il passo 3 del run si ferma se un identificativo cambia o l'immagine manca",
]


def _docker(*args: str) -> str:
    """Runs docker and returns what it printed; a failure stops with the first part of its message."""
    r = subprocess.run(["docker", *args], capture_output=True, stdin=subprocess.DEVNULL)
    if r.returncode:
        raise ValueError(f"docker {' '.join(args[:3])}: {r.stderr.decode('utf-8', 'replace').strip()[:300]}")
    return r.stdout.decode("utf-8")


def _git(repo: Path, *args: str) -> bytes:
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, stdin=subprocess.DEVNULL)
    if r.returncode:
        raise ValueError(f"git {' '.join(args)}: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout


def _commit(repo: Path, rev: str = "HEAD") -> str:
    return _git(repo, "rev-parse", "--verify", f"{rev}^{{commit}}").decode().strip()


def _tracciati(repo: Path, commit: str, percorso: str) -> list[str]:
    nomi = sorted(n for n in _git(repo, "ls-tree", "-r", "-z", "--name-only", commit, "--", percorso).decode("utf-8").split("\0") if n)
    if not nomi:
        raise ValueError(f"nel commit non c'e nulla in {percorso}")
    return nomi


def _impronta(repo: Path, commit: str, nome: str) -> str:
    return hashlib.sha256(_git(repo, "cat-file", "blob", f"{commit}:{nome}")).hexdigest()


def _insieme(file: dict[str, str]) -> str:
    return hashlib.sha256(("\n".join(f"{sha}  {nome}" for nome, sha in sorted(file.items())) + "\n").encode("utf-8")).hexdigest()


def _file_del_gruppo(repo: Path, commit: str, percorsi: list[str]) -> dict[str, str]:
    return dict(sorted((nome, _impronta(repo, commit, nome)) for p in percorsi for nome in _tracciati(repo, commit, p)))


def _leggi_pin(repo: Path, commit: str, file: str, espressione: str) -> str:
    m = re.search(espressione, _git(repo, "cat-file", "blob", f"{commit}:{file}").decode("utf-8"))
    if not m:
        raise ValueError(f"nel file {file} non si trova il valore cercato ({espressione})")
    return m.group(1)


def file_copiati(repo: Path, commit: str, dockerfile: str, contesto: str) -> dict[str, str]:
    """The files a Dockerfile copies from the repository: place in the image -> file in the repository. `COPY --from` (another stage)
    is not a file of the repository. A directory is expanded into its tracked files."""
    mappa: dict[str, str] = {}
    for riga in _git(Path(repo), "cat-file", "blob", f"{commit}:{dockerfile}").decode("utf-8").splitlines():
        parti = riga.split()
        if not parti or parti[0].upper() != "COPY" or any(p.startswith("--from") for p in parti):
            continue
        *sorgenti, dest = [p for p in parti[1:] if not p.startswith("--")]
        for s in sorgenti:
            percorso = s if contesto in (".", "") else f"{contesto.rstrip('/')}/{s}"
            nomi = _tracciati(Path(repo), commit, percorso)
            if nomi == [percorso]:
                mappa[dest + Path(percorso).name if dest.endswith("/") else dest] = percorso
            else:
                for n in nomi:
                    mappa[dest.rstrip("/") + "/" + n[len(percorso.rstrip("/")) + 1:]] = n
    return dict(sorted(mappa.items()))


def _in_immagine(docker, nome: str, entrata: str, *args: str) -> str:
    """Runs a command in a throwaway container: no network, never pulls an image, removed at the end."""
    return docker("run", "--rm", "--network", "none", "--pull", "never", "--entrypoint", entrata, nome, *args)


def _hash_dentro(docker, nome: str, percorsi: list[str]) -> dict[str, str]:
    out = {}
    for riga in _in_immagine(docker, nome, "sha256sum", *percorsi).splitlines():
        h, _, p = riga.partition("  ")
        out[p] = h
    return out


def registra_immagini(repo: Path, commit: str, docker, immagini: dict = IMMAGINI) -> dict:
    """Each image with its identifier, its pip freeze and the files copied into it, each compared with the file of the commit:
    «uguale», «uguale con a capo di Windows» (the build on Windows copies the working copy) or «DIVERSO»."""
    repo = Path(repo)
    registro = {}
    for chiave, cfg in immagini.items():
        nome = cfg["nome"]
        identificativo = docker("image", "inspect", "--format", "{{.Id}}", nome).strip()
        freeze = _in_immagine(docker, nome, "pip", "freeze") if cfg["pip"] else None
        mappa = file_copiati(repo, commit, cfg["dockerfile"], cfg["contesto"])
        dentro = _hash_dentro(docker, nome, list(mappa))
        file = {}
        for dest, sorgente in mappa.items():
            blob = _git(repo, "cat-file", "blob", f"{commit}:{sorgente}")
            h = dentro[dest]
            stato = ("uguale" if h == hashlib.sha256(blob).hexdigest() else
                     "uguale con a capo di Windows" if h == hashlib.sha256(blob.replace(b"\n", b"\r\n")).hexdigest() else "DIVERSO")
            file[dest] = {"sha256": h, "da": sorgente, "rispetto_al_commit": stato}
        registro[chiave] = {"nome": nome, "id": identificativo,
                            "pip_freeze": None if freeze is None else [r for r in freeze.splitlines() if r.strip()],
                            "pip_freeze_sha256": None if freeze is None else hashlib.sha256(freeze.encode("utf-8")).hexdigest(),
                            "file_copiati": file}
    return registro


def verifica_immagini(elenco: dict, docker, a_fondo: bool = False) -> list[str]:
    """The images of the list against the ones Docker has now. Quick (default): only the identifiers, no container started; this is
    the check of the run (step 3). Deep: also pip freeze and the files inside, in throwaway containers."""
    if elenco.get("immagini") is None:
        raise ValueError("l'elenco non ha le immagini registrate")
    problemi: list[str] = []
    for chiave, r in elenco["immagini"].items():
        try:
            ora = docker("image", "inspect", "--format", "{{.Id}}", r["nome"]).strip()
        except ValueError as exc:
            problemi.append(f"{chiave}: l'immagine {r['nome']} non si trova ({exc})")
            continue
        if ora != r["id"]:
            problemi.append(f"{chiave}: identificativo {ora}, nell'elenco {r['id']}")
            continue
        if not a_fondo:
            continue
        if r["pip_freeze_sha256"] is not None:
            freeze = _in_immagine(docker, r["nome"], "pip", "freeze")
            if hashlib.sha256(freeze.encode("utf-8")).hexdigest() != r["pip_freeze_sha256"]:
                problemi.append(f"{chiave}: pip freeze diverso da quello dell'elenco")
        dentro = _hash_dentro(docker, r["nome"], list(r["file_copiati"]))
        problemi += [f"{chiave}: {p} cambiato dentro l'immagine" for p, f in r["file_copiati"].items() if dentro.get(p) != f["sha256"]]
    return problemi


def genera(repo: Path, data: str, gruppi: dict[str, list[str]] = GRUPPI, pin: dict[str, tuple[str, str]] = PIN,
           docker=None, immagini: dict | None = None) -> dict:
    """The list as plain data, from the commit HEAD. It stops if a tracked file differs from the commit (it would not be in the list).
    With `docker` the images are recorded too; an image holding a file that differs from the commit stops the generation."""
    repo = Path(repo)
    modificati = _git(repo, "status", "--porcelain", "--untracked-files=no").decode("utf-8").strip()
    if modificati:
        raise ValueError(f"file tracciati diversi dal commit, l'elenco non li conterrebbe:\n{modificati}")
    commit = _commit(repo)
    out_gruppi = {}
    for nome, percorsi in gruppi.items():
        file = _file_del_gruppo(repo, commit, percorsi)
        out_gruppi[nome] = {"percorsi": list(percorsi), "file": file, "impronta_insieme": _insieme(file)}
    registro = None
    if docker is not None:
        registro = registra_immagini(repo, commit, docker, immagini or IMMAGINI)
        diversi = [f"{k}: {p}" for k, r in registro.items() for p, f in r["file_copiati"].items() if f["rispetto_al_commit"] == "DIVERSO"]
        if diversi:
            raise ValueError("file dentro le immagini diversi da quelli del commit (l'immagine non e stata costruita da questo commit?): "
                             + "; ".join(diversi))
    return {
        "versione": 1,
        "data": data,
        "commit_del_codice": commit,
        "gruppi": out_gruppi,
        "pin_dei_produttori": {n: _leggi_pin(repo, commit, f, rx) for n, (f, rx) in pin.items()},
        "origine_dei_pin": {n: {"file": f, "espressione": rx} for n, (f, rx) in pin.items()},
        "immagini": registro,
        "da_registrare_a_mano": [v for v in DA_REGISTRARE_A_MANO if not (registro is not None and v.startswith("immagini:"))],
    }


def verifica(repo: Path, elenco: dict, commit: str = "HEAD") -> list[str]:
    """The differences between the list and a commit (default HEAD), one line each. Empty: nothing differs."""
    repo = Path(repo)
    c = _commit(repo, commit)
    problemi: list[str] = []
    for nome, g in elenco["gruppi"].items():
        if _insieme(g["file"]) != g["impronta_insieme"]:
            problemi.append(f"{nome}: l'impronta d'insieme non corrisponde ai file dell'elenco")
        ora: dict[str, str] = {}
        for p in g["percorsi"]:
            try:
                ora.update(_file_del_gruppo(repo, c, [p]))
            except ValueError:
                problemi.append(f"{nome}: {p} non c'e piu nel commit")
        problemi += [f"{nome}: {f} tolto" for f in sorted(set(g["file"]) - set(ora))]
        problemi += [f"{nome}: {f} aggiunto" for f in sorted(set(ora) - set(g["file"]))]
        problemi += [f"{nome}: {f} cambiato" for f in sorted(set(ora) & set(g["file"])) if ora[f] != g["file"][f]]
    for n, atteso in elenco["pin_dei_produttori"].items():
        o = elenco["origine_dei_pin"][n]
        trovato = _leggi_pin(repo, c, o["file"], o["espressione"])
        if trovato != atteso:
            problemi.append(f"{n}: nel commit {trovato}, nell'elenco {atteso}")
    return problemi


def in_json(elenco: dict) -> str:
    return json.dumps(elenco, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None, gruppi: dict | None = None, pin: dict | None = None, docker=None,
         immagini: dict | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m toy_agent.elenco_a", description="Elenco A delle impronte: genera e verifica.")
    sub = p.add_subparsers(dest="comando", required=True)
    g = sub.add_parser("genera", help="scrive l'elenco dal commit HEAD (non sovrascrive)")
    g.add_argument("--repo", type=Path, default=Path("."))
    g.add_argument("--data", required=True, help="data dell'elenco, AAAA-MM-GG (scritta nel file: il file e uguale a ogni rigenerazione)")
    g.add_argument("--out", type=Path, required=True)
    g.add_argument("--con-immagini", action="store_true",
                   help="registra anche le tre immagini Docker (identificativo, pip freeze, file copiati); serve Docker acceso")
    vi = sub.add_parser("verifica-immagini", help="confronta le immagini Docker di ora con quelle dell'elenco; esce con 1 se differiscono "
                                                  "(e il passo 3 dei comandi del run)")
    vi.add_argument("elenco", type=Path)
    vi.add_argument("--a-fondo", action="store_true", help="anche pip freeze e i file dentro, in contenitori usa e getta")
    v = sub.add_parser("verifica", help="confronta l'elenco con un commit (default HEAD); esce con 1 se qualcosa differisce")
    v.add_argument("elenco", type=Path)
    v.add_argument("--repo", type=Path, default=Path("."))
    v.add_argument("--commit", default="HEAD")
    a = p.parse_args(argv)
    if a.comando == "verifica-immagini":
        elenco = json.loads(a.elenco.read_text(encoding="utf-8"))
        if elenco.get("immagini") is None:
            p.error("l'elenco non ha le immagini registrate: rigenerarlo con --con-immagini")
        problemi = verifica_immagini(elenco, docker or _docker, a.a_fondo)
        for riga in problemi:
            print(riga)
        if not problemi:
            print("nessuna differenza")
        return 1 if problemi else 0
    if a.comando == "genera":
        if a.out.exists():
            raise FileExistsError(f"l'elenco esiste gia, non si sovrascrive: {a.out}")
        elenco = genera(a.repo, a.data, gruppi or GRUPPI, pin or PIN, (docker or _docker) if a.con_immagini else None, immagini)
        with open(a.out, "x", encoding="utf-8", newline="\n") as f:
            f.write(in_json(elenco))
        n = sum(len(x["file"]) for x in elenco["gruppi"].values())
        print(f"{a.out}: {n} file in {len(elenco['gruppi'])} gruppi, commit {elenco['commit_del_codice']}")
        return 0
    elenco = json.loads(a.elenco.read_text(encoding="utf-8"))
    problemi = verifica(a.repo, elenco, a.commit)
    for riga in problemi:
        print(riga)
    if not problemi:
        print("nessuna differenza")
    if elenco["immagini"] is None:
        print("nota: le immagini non sono ancora registrate nell'elenco")
    return 1 if problemi else 0


if __name__ == "__main__":
    raise SystemExit(main())
