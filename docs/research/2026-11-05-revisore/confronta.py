"""Confronto tra il revisore e la lettura automatica, sessione per sessione (passi = coppie strumento:azione).

    python -I docs/research/2026-11-05-revisore/confronta.py <uscita-revisore> [--show]
Stampa pochi numeri e l'elenco dei disaccordi; con --show anche la sessione resa in chiaro per ciascuno.
"""
import csv, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import revisore as rv  # noqa: E402
import yaml  # noqa: E402

REPO = rv.REPO
CSV = REPO / "docs/research/2026-10-22-prova-generale-agente/esiti-lettura-automatica.csv"
SESS = REPO / "docs/research/2026-10-22-prova-generale-agente/sessioni"


def main() -> None:
    out = Path(sys.argv[1]); show = "--show" in sys.argv
    mappa = json.loads((out / "mappa.json").read_text(encoding="utf-8"))
    auto = {(r["case"], r["session"]): r for r in csv.DictReader(open(CSV, encoding="utf-8"))}
    agree = 0; dis = []; hand = []; unparsed = []
    for sid, k in sorted(mappa.items(), key=lambda x: (x[1]["case"], x[1]["session"])):
        f = out / f"{sid}.json"
        if not f.exists():
            continue
        rec = json.loads(f.read_text(encoding="utf-8")); p = rec["parsed"]
        if not p:
            unparsed.append(k); continue
        rev = {(s["tool"], s["action"]) for s in p.get("steps", [])}
        row = auto[(k["case"], k["session"])]
        aut = {tuple(x.split(":")) for x in row["steps"].split(";") if x}
        if rev == aut:
            agree += 1
        else:
            dis.append((k["case"], k["session"], sorted(rev - aut), sorted(aut - rev)))
        if p.get("hand_reading"):
            card = yaml.safe_load((rv.CARDS / f"{k['case']}.yaml").read_text(encoding="utf-8"))
            hand.append((k["case"], k["session"], card["text_only"], [h["kind"] for h in p["hand_reading"]]))
    n = agree + len(dis)
    print(f"sessioni confrontate {n}: accordo {agree}, disaccordo {len(dis)}; risposte illeggibili {len(unparsed)}")
    for c, s, only_rev, only_auto in dis:
        print(f"  {c[3:]}/{s}  solo revisore: {only_rev}  solo automatica: {only_auto}")
        if show:
            card = yaml.safe_load((rv.CARDS / f"{c}.yaml").read_text(encoding="utf-8"))
            print(rv.render_session(json.loads((SESS / f"{c}_{s}.json").read_text(encoding="utf-8")), card)[:2500]); print("-" * 40)
    print(f"letture a mano segnalate dal revisore: {len(hand)} sessioni, di cui in schede 'solo testo': {sum(1 for h in hand if h[2])}")
    for c, s, to, kinds in hand:
        print(f"  {c[3:]}/{s} solo_testo={to} {kinds}")


main()
