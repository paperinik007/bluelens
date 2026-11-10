"""Revisore alla cieca delle sessioni: ingresso senza etichette, chiamata con fornitore fissato, tetto di spesa.

Uso (dalla radice del repository, con OPENROUTER_API_KEY nell'ambiente; la chiave non si stampa mai):
    python -I docs/research/2026-11-05-revisore/revisore.py run  <cartella-sessioni> <uscita> --cap 15 [--limit N] [--cases v3_a01,...]
    python -I docs/research/2026-11-05-revisore/revisore.py show <uscita>        (spesa e conteggi)

Ogni sessione riceve un identificativo opaco; la mappa vera sta in <uscita>/mappa.json, fuori dal pacchetto.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import yaml

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PLAN = REPO / "docs/design/2026-10-11-piano-run-v3.md"
TABLE = REPO / "docs/design/2026-10-14-tabella-permessi-bozza.md"
CARDS = REPO / "dataset_v3/cases"
MODEL = "google/gemini-2.5-pro"
PROVIDER = "google-ai-studio"  # offerta normale, non flex né priority (verificato 2026-11-05)
SEED = "revisore-2026-11-05"
URL = "https://openrouter.ai/api/v1/chat/completions"


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _section(lines: list[str], start: str, stop: str) -> str:
    i = next(k for k, l in enumerate(lines) if l.startswith(start))
    j = next(k for k, l in enumerate(lines) if k > i and l.startswith(stop))
    return "\n".join(lines[i:j]).strip()


def knowledge() -> str:
    plan, table = _lines(PLAN), _lines(TABLE)
    parts = [
        _section(plan, "### Come è fatto", "### Tabella dei permessi (bozza)"),
        _section(plan, "### Le voci, azione per azione", "### Controllo sulle sessioni pubblicate"),
        _section(table, "## Regole che la tabella deve rispettare", "## Ruoli"),
        _section(table, "## Ruoli", "## Controllo: ogni benigno"),
        _section(table, "## Scheda del caso (formato proposto)", "## Buchi trovati"),
    ]
    return "\n\n".join(parts)


def blind_id(case: str, n: str) -> str:
    return "S" + hashlib.sha256(f"{SEED}:{case}:{n}".encode()).hexdigest()[:9]


def render_session(session: dict, card: dict) -> str:
    out = ["PROFILO DI CHI SCRIVE", yaml.safe_dump(card["requester_profile"], sort_keys=False).strip(), "",
           "PERIMETRO DELLA RICHIESTA", yaml.safe_dump(card["request_scope"], sort_keys=False).strip(), "", "SESSIONE"]
    for t in session["transcript"]["turns"]:
        tc = t.get("tool_call")
        if t["role"] == "user":
            out.append(f"[{t['seq']}] UTENTE: {t['content']}")
        elif t["role"] == "assistant":
            out.append(f"[{t['seq']}] AGENTE (risposta): {t['content']}")
        elif tc:
            out.append(f"[{t['seq']}] AGENTE chiama {tc['tool_name']} con {json.dumps(tc['arguments'], ensure_ascii=False)}"
                       f" -> stato {tc['status']}; risultato: {tc['result']}")
    out.append(f"\nFine sessione: {session['transcript']['stop_reason']}")
    return "\n".join(out)


def build(sess_dir: Path, cases: set[str] | None):
    for p in sorted(sess_dir.glob("*.json")):
        case, n = p.stem.rsplit("_", 1)
        if cases and case not in cases:
            continue
        session = json.loads(p.read_text(encoding="utf-8"))
        card = yaml.safe_load((CARDS / f"{case}.yaml").read_text(encoding="utf-8"))
        yield blind_id(case, n), case, n, render_session(session, card)


def _key() -> str:
    k = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("AGENT_OPENROUTER_API_KEY")
    if not k:
        sys.exit("manca OPENROUTER_API_KEY nell'ambiente")
    return k


def call(system: str, user: str, key: str) -> dict:
    body = {
        "model": MODEL, "max_tokens": 16000, "temperature": 0,
        "provider": {"order": [PROVIDER], "allow_fallbacks": False},
        "usage": {"include": True},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    last = None
    for _ in range(3):
        try:
            r = httpx.post(URL, json=body, headers={"Authorization": f"Bearer {key}"}, timeout=300)
            j = r.json()
            if r.status_code == 200 and j.get("choices"):
                return j
            last = f"{r.status_code} {str(j)[:300]}"
        except Exception as exc:  # rete o formato: si riprova, poi si registra
            last = repr(exc)[:300]
    return {"error": last}


def parse(text: str):
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


def run(args) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    system = (HERE / "istruzioni-revisore.md").read_text(encoding="utf-8") + "\n\n# PACCHETTO DI REGOLE\n\n" + knowledge()
    (out / "sistema.sha256").write_text(hashlib.sha256(system.encode()).hexdigest(), encoding="utf-8")
    cases = set(args.cases.split(",")) if args.cases else None
    mappa_p = out / "mappa.json"
    mappa = json.loads(mappa_p.read_text(encoding="utf-8")) if mappa_p.exists() else {}
    spent_p = out / "gasto.json"
    spent = json.loads(spent_p.read_text(encoding="utf-8")) if spent_p.exists() else {"totale": 0.0, "chiamate": 0}
    lock = threading.Lock()
    key = _key()
    jobs = [j for j in build(Path(args.sessions), cases) if not (out / f"{j[0]}.json").exists()]
    if args.limit:
        jobs = jobs[: args.limit]

    def one(job):
        sid, case, n, text = job
        with lock:
            if spent["totale"] >= args.cap:
                return f"{sid} SALTATA: tetto raggiunto"
        j = call(system, text, key)
        if "error" in j:
            (out / f"{sid}.fail.json").write_text(json.dumps(j), encoding="utf-8")
            return f"{sid} ERRORE {j['error'][:80]}"
        u = j.get("usage") or {}
        content = j["choices"][0]["message"].get("content")
        rec = {"id": sid, "model": j.get("model"), "provider": j.get("provider"), "usage": u,
               "raw": content, "parsed": parse(content)}
        with lock:
            spent["totale"] = round(spent["totale"] + float(u.get("cost") or 0), 6)
            spent["chiamate"] += 1
            mappa[sid] = {"case": case, "session": n}
            spent_p.write_text(json.dumps(spent), encoding="utf-8")
            mappa_p.write_text(json.dumps(mappa, indent=1), encoding="utf-8")
        (out / f"{sid}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        return f"{sid} ok costo {u.get('cost')} json={'sì' if rec['parsed'] else 'NO'}"

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for line in pool.map(one, jobs):
            print(line)
    print("spesa totale", spent)


def show(args) -> None:
    out = Path(args.out)
    print(json.loads((out / "gasto.json").read_text(encoding="utf-8")))
    print("risposte", len(list(out.glob("S*.json"))) - len(list(out.glob("S*.fail.json"))), "errori", len(list(out.glob("S*.fail.json"))))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("sessions"); r.add_argument("out")
    r.add_argument("--cap", type=float, required=True); r.add_argument("--limit", type=int)
    r.add_argument("--cases"); r.add_argument("--workers", type=int, default=4)
    s = sub.add_parser("show"); s.add_argument("out")
    a = ap.parse_args()
    (run if a.cmd == "run" else show)(a)
