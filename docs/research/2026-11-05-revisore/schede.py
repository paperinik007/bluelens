"""Lettura alla cieca delle 58 schede: coerenza (una chiamata per scheda) e plausibilità (un'unica chiamata a lotto).

    python -I docs/research/2026-11-05-revisore/schede.py coerenza <uscita> --cap 3
    python -I docs/research/2026-11-05-revisore/schede.py plausibilita <uscita> --cap 1
"""
import argparse, json, random, sys, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import revisore as rv  # noqa: E402

HIDE = {"case_id", "intent", "labels", "cell", "source", "written_for_length", "text_only", "where", "form"}


def sheets():
    for p in sorted(rv.CARDS.glob("v3_*.yaml")):
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        yield d["case_id"], d


def coerenza(a) -> None:
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    system = (HERE / "istruzioni-schede.md").read_text(encoding="utf-8") + "\n\n# PACCHETTO DI REGOLE\n\n" + rv.knowledge()
    key = rv._key(); lock = threading.Lock(); spent = {"totale": 0.0}; mappa = {}
    def one(item):
        cid, d = item
        sid = rv.blind_id(cid, "scheda")
        f = out / f"{sid}.json"
        if f.exists() and json.loads(f.read_text(encoding="utf-8")).get("parsed"):
            return f"{sid} già letta"
        view = {k: v for k, v in d.items() if k not in HIDE}
        view["world_data"] = {k: v for k, v in d["world_data"].items() if k != "third_party_version"}
        with lock:
            if spent["totale"] >= a.cap:
                return f"{sid} SALTATA"
        j = rv.call(system, "SCHEDA\n" + yaml.safe_dump(view, sort_keys=False, allow_unicode=True), key)
        if "error" in j:
            return f"{sid} ERRORE {j['error'][:80]}"
        u = j.get("usage") or {}; content = j["choices"][0]["message"].get("content")
        with lock:
            spent["totale"] += float(u.get("cost") or 0); mappa[sid] = cid
        f.write_text(json.dumps({"id": sid, "model": j.get("model"), "provider": j.get("provider"), "usage": u, "raw": content, "parsed": rv.parse(content)}, ensure_ascii=False, indent=1), encoding="utf-8")
        return f"{sid} ok"
    with ThreadPoolExecutor(max_workers=3) as pool:
        print("\n".join(pool.map(one, list(sheets()))))
    mp = out / "mappa.json"; old = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    old.update(mappa); mp.write_text(json.dumps(old, indent=1), encoding="utf-8")
    print("spesa", round(spent["totale"], 4))


def plausibilita(a) -> None:
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    system = (HERE / "istruzioni-plausibilita.md").read_text(encoding="utf-8")
    items, mappa = [], {}
    for cid, d in sheets():
        sid = rv.blind_id(cid, "plaus"); mappa[sid] = cid
        w = d["world_data"]
        texts = {"role": d["requester_profile"]["role"], "request": d["seed_turn"],
                 "tickets": [t.get("content") for t in (w.get("tickets") or [])],
                 "orders": [o.get("note") or o for o in (w.get("orders") or [])]}
        items.append({"id": sid, **texts})
    random.Random(rv.SEED).shuffle(items)
    merged, spent, raws = [], 0.0, []
    for i in range(0, len(items), 15):  # lotti da 15: con 58 insieme la risposta supera il limite di uscita
        j = rv.call(system, json.dumps(items[i:i + 15], ensure_ascii=False, indent=1), rv._key())
        if "error" in j:
            sys.exit("ERRORE " + j["error"])
        u = j.get("usage") or {}; content = j["choices"][0]["message"].get("content")
        parsed = rv.parse(content); spent += float(u.get("cost") or 0); raws.append({"model": j.get("model"), "provider": j.get("provider"), "usage": u, "raw": content})
        if not parsed:
            sys.exit(f"lotto {i // 15} non leggibile")
        merged += parsed["items"]
    (out / "plausibilita.json").write_text(json.dumps({"batches": raws, "items": merged}, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "mappa.json").write_text(json.dumps(mappa, indent=1), encoding="utf-8")
    print("spesa", round(spent, 4), "elementi", len(merged))


ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["coerenza", "plausibilita"]); ap.add_argument("out"); ap.add_argument("--cap", type=float, required=True)
a = ap.parse_args(); (coerenza if a.cmd == "coerenza" else plausibilita)(a)
