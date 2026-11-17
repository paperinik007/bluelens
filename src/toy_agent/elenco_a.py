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
    "programmi": ["src/toy_agent/analisi_v3.py", "tests/toy_agent/test_analisi_v3.py", "src/toy_agent/elenco_a.py",
                  "tests/toy_agent/test_elenco_a.py", "src/toy_agent/ondate.py", "src/toy_agent/ambito.py",
                  "src/toy_agent/check_conditions.py", "src/toy_agent/sposta_guasti.py", "src/toy_agent/registra_versioni.py",
                  "src/toy_agent/malicious_steps.py", f"{REV}/confronta.py"],
    "ambiente": ["docker", "docker-compose.yml"],
}

# Where the versions of the vendors are pinned: name -> (file, expression with one group). Read from the Dockerfiles.
PIN: dict[str, tuple[str, str]] = {
    "aidr_commit": ("docker/detector/Dockerfile", r"git checkout ([0-9a-f]{40})"),
    "llamafirewall_versione": ("docker/detector-llamafirewall/Dockerfile", r"llamafirewall==([0-9][0-9.]*[0-9])"),
}

DA_REGISTRARE_A_MANO = [
    "disegno del modello (pagina pubblicata, versione 34 o successiva): versione e impronta del testo pubblicato",
    "valori usati di .env.aidr e .env.llamafirewall (modelli e fornitori, mai le chiavi): li confronta check_conditions",
    "immagini: identificativo, pip freeze, file copiati dentro e archivio docker save (passo successivo, con Docker acceso)",
]


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


def genera(repo: Path, data: str, gruppi: dict[str, list[str]] = GRUPPI, pin: dict[str, tuple[str, str]] = PIN) -> dict:
    """The list as plain data, from the commit HEAD. It stops if a tracked file differs from the commit (it would not be in the list)."""
    repo = Path(repo)
    modificati = _git(repo, "status", "--porcelain", "--untracked-files=no").decode("utf-8").strip()
    if modificati:
        raise ValueError(f"file tracciati diversi dal commit, l'elenco non li conterrebbe:\n{modificati}")
    commit = _commit(repo)
    out_gruppi = {}
    for nome, percorsi in gruppi.items():
        file = _file_del_gruppo(repo, commit, percorsi)
        out_gruppi[nome] = {"percorsi": list(percorsi), "file": file, "impronta_insieme": _insieme(file)}
    return {
        "versione": 1,
        "data": data,
        "commit_del_codice": commit,
        "gruppi": out_gruppi,
        "pin_dei_produttori": {n: _leggi_pin(repo, commit, f, rx) for n, (f, rx) in pin.items()},
        "origine_dei_pin": {n: {"file": f, "espressione": rx} for n, (f, rx) in pin.items()},
        "immagini": None,
        "da_registrare_a_mano": list(DA_REGISTRARE_A_MANO),
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


def main(argv: list[str] | None = None, gruppi: dict | None = None, pin: dict | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m toy_agent.elenco_a", description="Elenco A delle impronte: genera e verifica.")
    sub = p.add_subparsers(dest="comando", required=True)
    g = sub.add_parser("genera", help="scrive l'elenco dal commit HEAD (non sovrascrive)")
    g.add_argument("--repo", type=Path, default=Path("."))
    g.add_argument("--data", required=True, help="data dell'elenco, AAAA-MM-GG (scritta nel file: il file e uguale a ogni rigenerazione)")
    g.add_argument("--out", type=Path, required=True)
    v = sub.add_parser("verifica", help="confronta l'elenco con un commit (default HEAD); esce con 1 se qualcosa differisce")
    v.add_argument("elenco", type=Path)
    v.add_argument("--repo", type=Path, default=Path("."))
    v.add_argument("--commit", default="HEAD")
    a = p.parse_args(argv)
    if a.comando == "genera":
        if a.out.exists():
            raise FileExistsError(f"l'elenco esiste gia, non si sovrascrive: {a.out}")
        elenco = genera(a.repo, a.data, gruppi or GRUPPI, pin or PIN)
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
