"""Estrae a sorte le 30 sessioni della prova pilota dalle 138 sessioni salvate dei run pubblicati.

Piano del run v3, parte 9: 10 con risultato malevolo, 10 benigne, 10 rifiuti di un attacco, estratte a
sorte dentro ogni gruppo con un seme registrato; 10 delle 30 sono anche quelle della prova della lingua.
I gruppi si definiscono dalla nostra lettura delle sessioni (docs/research/2026-10-08-risultati-run-pubblicati/
tabella-per-caso.csv), mai dai verdetti dei giudici nuovi.

Uso: python prepara_sessioni.py   (dalla cartella del repo; scrive accanto a questo file)
"""
import csv
import hashlib
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TABLE = REPO / "docs/research/2026-10-08-risultati-run-pubblicati/tabella-per-caso.csv"
REPORTS = REPO / "docs/reports"
SEED = 20261026
PER_GROUP = 10
LANGUAGE_TEST = 10

RUN_DIR = {
    "19/8": "agentic-threat-detection-2026-08-19",
    "26/8": "aidr-2026-08-26",
    "28/8": "llamafirewall-2026-08-28",
    "1/9": "atlas-6gap-aidr-2026-09-01",
    "4/9": "llamafirewall-combined-2026-09-04",
}


def group_of(row):
    """Il gruppo della sessione, dalla nostra lettura; None se non è in nessuno dei tre."""
    if row["intento"] == "malevolo" and row["esito"] == "ESEGUE" and row["effetto"].startswith("avvenuto"):
        return "risultato malevolo"
    if row["intento"] == "benigno" and row["esito"] == "CORRETTO":
        return "benigna"
    if row["intento"] == "malevolo" and row["esito"] == "RIFIUTA":
        return "rifiuto"
    return None


def opaque_id(run, case):
    return "p" + hashlib.sha256(f"{SEED}|{run}|{case}".encode()).hexdigest()[:10]


def main():
    rows = list(csv.DictReader(open(TABLE, encoding="utf-8")))
    groups = {"risultato malevolo": [], "benigna": [], "rifiuto": []}
    for r in rows:
        g = group_of(r)
        if g:
            groups[g].append(r)
    rng = random.Random(SEED)
    chosen = []
    for name, candidates in groups.items():
        candidates = sorted(candidates, key=lambda r: (r["run"], r["caso"]))
        picked = rng.sample(candidates, min(PER_GROUP, len(candidates)))
        print(f"{name}: {len(candidates)} candidate, estratte {len(picked)}")
        chosen += [(name, r) for r in picked]
    chosen.sort(key=lambda gr: opaque_id(gr[1]["run"], gr[1]["caso"]))
    language = set(rng.sample([opaque_id(r["run"], r["caso"]) for _, r in chosen], LANGUAGE_TEST))

    out = HERE / "sessioni-originali"
    out.mkdir(exist_ok=True)
    with open(HERE / "estrazione.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "gruppo", "run", "caso", "prova_lingua"])
        for name, r in chosen:
            sid = opaque_id(r["run"], r["caso"])
            source = REPORTS / RUN_DIR[r["run"]] / "raw" / f"{r['caso']}.transcript.json"
            data = json.loads(source.read_text(encoding="utf-8"))
            data["session_id"] = sid  # opaco: mai il nome del caso
            (out / f"{sid}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            w.writerow([sid, name, r["run"], r["caso"], "si" if sid in language else "no"])
    print(f"{len(chosen)} sessioni in {out}; seme {SEED}; prova della lingua su {len(language)}")


if __name__ == "__main__":
    main()
