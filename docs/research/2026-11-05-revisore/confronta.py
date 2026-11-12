"""Confronto tra il revisore e la lettura automatica, sessione per sessione (passi = coppie strumento:azione).

    python -I docs/research/2026-11-05-revisore/confronta.py <uscita-revisore> [--sessions <cartella-sessioni>] [--show]

La lettura automatica si calcola sul momento dalle sessioni (`toy_agent.malicious_steps.read_session`, con la scheda in
`dataset_v3/cases/`), non si legge da un file. Senza `--sessions` si usano le sessioni della prova generale (come prima: sulle
174 sessioni il calcolo coincide con `esiti-lettura-automatica.csv`). Nel run si passa la cartella `ONDATA/sessioni`.
Stampa pochi numeri e l'elenco dei disaccordi; con --show anche la sessione resa in chiaro per ciascuno.
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import revisore as rv  # noqa: E402
import yaml  # noqa: E402

REPO = rv.REPO
sys.path.insert(0, str(REPO / "src"))
from toy_agent.malicious_steps import read_session  # noqa: E402

SESS = REPO / "docs/research/2026-10-22-prova-generale-agente/sessioni"


def automatic_steps(case: str, session: str, sess_dir: Path) -> set[tuple[str, str]]:
    """The malicious steps (tool, action) that the automatic reading finds in one saved session."""
    f = sess_dir / f"{case}_{session}.json"
    if not f.exists():
        raise SystemExit(f"manca la sessione {f}: il confronto si fa sulla stessa cartella data al revisore")
    card = yaml.safe_load((rv.CARDS / f"{case}.yaml").read_text(encoding="utf-8"))
    transcript = json.loads(f.read_text(encoding="utf-8"))["transcript"]
    return {(s.tool, s.action) for s in read_session(card, transcript).steps}


def compare(out: Path, sess_dir: Path) -> dict:
    mappa = json.loads((out / "mappa.json").read_text(encoding="utf-8"))
    agree = 0; dis = []; hand = []; unparsed = []
    for sid, k in sorted(mappa.items(), key=lambda x: (x[1]["case"], x[1]["session"])):
        f = out / f"{sid}.json"
        if not f.exists():
            continue
        rec = json.loads(f.read_text(encoding="utf-8")); p = rec["parsed"]
        if not p:
            unparsed.append(k); continue
        rev = {(s["tool"], s["action"]) for s in p.get("steps", [])}
        aut = automatic_steps(k["case"], k["session"], sess_dir)
        if rev == aut:
            agree += 1
        else:
            dis.append((k["case"], k["session"], sorted(rev - aut), sorted(aut - rev)))
        if p.get("hand_reading"):
            card = yaml.safe_load((rv.CARDS / f"{k['case']}.yaml").read_text(encoding="utf-8"))
            hand.append((k["case"], k["session"], card["text_only"], [h["kind"] for h in p["hand_reading"]]))
    return {"agree": agree, "dis": dis, "hand": hand, "unparsed": unparsed}


def main(argv: list[str]) -> None:
    out = Path(argv[1]); show = "--show" in argv
    sess_dir = Path(argv[argv.index("--sessions") + 1]) if "--sessions" in argv else SESS
    r = compare(out, sess_dir)
    agree, dis, hand, unparsed = r["agree"], r["dis"], r["hand"], r["unparsed"]
    n = agree + len(dis)
    print(f"sessioni confrontate {n}: accordo {agree}, disaccordo {len(dis)}; risposte illeggibili {len(unparsed)}")
    for c, s, only_rev, only_auto in dis:
        print(f"  {c[3:]}/{s}  solo revisore: {only_rev}  solo automatica: {only_auto}")
        if show:
            card = yaml.safe_load((rv.CARDS / f"{c}.yaml").read_text(encoding="utf-8"))
            print(rv.render_session(json.loads((sess_dir / f"{c}_{s}.json").read_text(encoding="utf-8")), card)[:2500]); print("-" * 40)
    print(f"letture a mano segnalate dal revisore: {len(hand)} sessioni, di cui in schede 'solo testo': {sum(1 for h in hand if h[2])}")
    for c, s, to, kinds in hand:
        print(f"  {c[3:]}/{s} solo_testo={to} {kinds}")


if __name__ == "__main__":
    main(sys.argv)
