"""Seconda lettura, alla cieca, delle sessioni dei casi "solo testo" (piano, parte 10, doppia lettura del 2026-10-28).

    python -I docs/research/2026-11-05-revisore/lettura_testo.py <cartella-sessioni> <uscita> --cap 1 --cases v3_n20,v3_n21,v3_n24,v3_n26
Stesso modello e fornitore del revisore; il criterio è il campo text_steps della scheda.
"""
import argparse, json, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import revisore as rv  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sessions"); ap.add_argument("out"); ap.add_argument("--cap", type=float, required=True)
    ap.add_argument("--cases", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    system = (HERE / "istruzioni-lettura-testo.md").read_text(encoding="utf-8")
    key = rv._key(); lock = threading.Lock(); mappa_p = out / "mappa.json"; spent_p = out / "gasto.json"
    mappa = json.loads(mappa_p.read_text(encoding="utf-8")) if mappa_p.exists() else {}
    spent = json.loads(spent_p.read_text(encoding="utf-8")) if spent_p.exists() else {"totale": 0.0}
    jobs = []
    for sid, case, n, text in rv.build(Path(a.sessions), set(a.cases.split(","))):
        card = yaml.safe_load((rv.CARDS / f"{case}.yaml").read_text(encoding="utf-8"))
        crit = "\n".join(f"- {c}" for c in card["text_steps"])
        done = out / f"{sid}.json"
        if done.exists() and json.loads(done.read_text(encoding="utf-8")).get("parsed"):
            continue  # già letta; una risposta vuota o non leggibile si rifà
        jobs.append((sid, case, n, f"CRITERIO\n{crit}\n\n{text}"))

    def one(job):
        sid, case, n, user = job
        with lock:
            if spent["totale"] >= a.cap:
                return f"{sid} SALTATA"
        j = rv.call(system, user, key)
        if "error" in j:
            return f"{sid} ERRORE {j['error'][:80]}"
        u = j.get("usage") or {}; content = j["choices"][0]["message"].get("content")
        rec = {"id": sid, "model": j.get("model"), "provider": j.get("provider"), "usage": u, "raw": content, "parsed": rv.parse(content)}
        with lock:
            spent["totale"] += float(u.get("cost") or 0); mappa[sid] = {"case": case, "session": n}
        (out / f"{sid}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        return f"{sid} ok"

    with ThreadPoolExecutor(max_workers=4) as pool:
        print("\n".join(pool.map(one, jobs)))
    mappa_p.write_text(json.dumps(mappa, indent=1), encoding="utf-8")
    spent_p.write_text(json.dumps({"totale": round(spent["totale"], 6)}), encoding="utf-8")
    print("spesa", round(spent["totale"], 4))


main()
