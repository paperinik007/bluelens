"""Prova generale dell'analisi su scala reale: sessioni vere della prova generale, verdetti FINTI (pseudo-casuali, deterministici).

    python docs/research/2026-11-18-prova-analisi-su-scala/prova_analisi.py CARTELLA_ONDATA

CARTELLA_ONDATA va creata fuori dal repository (se esiste viene cancellata e rifatta). Non chiama nessun modello, nessun servizio, non spende nulla.
"""
import json
import pathlib
import random
import shutil
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[3]
SRC = REPO / "docs/research/2026-10-22-prova-generale-agente/sessioni"
OND = pathlib.Path(sys.argv[1])
if OND.exists():
    shutil.rmtree(OND)
(OND / "sessioni").mkdir(parents=True)
(OND / "verdetti").mkdir()
rng = random.Random(7)
files = sorted(f for f in SRC.glob("v3_*_[0-9].json"))
mappa, chiuse = {}, {}
for i, f in enumerate(files):
    shutil.copy(f, OND / "sessioni" / f.name)
    caso = f.stem.rpartition("_")[0]
    sid = f"h{i:03d}"
    mappa[sid] = {"case_id": caso, "file": f.name}
    scheda = yaml.safe_load((REPO / f"dataset_v3/cases/{caso}.yaml").read_text(encoding="utf-8"))
    if scheda["intent"] == "malicious" and scheda.get("text_only"):
        chiuse[f.stem] = {"danno": False}          # lettura chiusa finta: nessun danno
    for g in ("promptguard", "alignmentcheck", "aidr"):
        labs = [rng.choice(["malicious", "benign"]) for _ in range(2)]
        if labs[0] != labs[1]:
            labs.append(rng.choice(["malicious", "benign"]))     # terzo verdetto sul disaccordo
        if rng.random() < 0.03:
            labs[0] = None                                       # un verdetto mancante (errore del giudice)
        for r, lab in enumerate(labs, 1):
            body = {"session_id": sid, "judge": g, "repeat": r, "verdict": {"status": "ok" if lab else "error", "label": lab}}
            (OND / "verdetti" / f"{sid}_{g}_{r}.json").write_text(json.dumps(body), encoding="utf-8")
(OND / "mappa.json").write_text(json.dumps(mappa), encoding="utf-8")
if chiuse:
    (OND / "letture-chiuse.json").write_text(json.dumps(chiuse), encoding="utf-8")
print(len(files), "sessioni;", len(chiuse), "letture chiuse")
