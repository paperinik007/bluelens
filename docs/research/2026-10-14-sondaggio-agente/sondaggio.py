"""Sondaggio dell'agente sui casi vecchi (piano-run-v3, parte 8).

Solo l'agente, nessun giudice: i 38 casi dei run pubblicati, ambiente vecchio,
lingua originale, 3 sessioni per caso. Agente openai/gpt-5.4-mini, fornitore
OpenAI, sforzo di ragionamento "none" (il più basso disponibile).

Uso (dalla radice del repo):
    python docs/research/2026-10-14-sondaggio-agente/sondaggio.py --smoke
    python docs/research/2026-10-14-sondaggio-agente/sondaggio.py
    python docs/research/2026-10-14-sondaggio-agente/sondaggio.py --verifica
Una sessione già salvata non si rifà. OpenRouter restituisce il nome del modello,
non la versione esatta: --verifica la legge, chiamata per chiamata, dal registro
delle generazioni di OpenRouter e la scrive in versioni.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from toy_agent.model_client import OpenRouterModelClient  # noqa: E402
from toy_agent.run_case import run_case  # noqa: E402

AGENTS = {
    "mini": ("openai/gpt-5.4-mini", "gpt-5.4-mini-20260317", "sessioni"),
    "nano": ("openai/gpt-5.4-nano", "gpt-5.4-nano-20260317", "sessioni-nano"),
}
MODEL, EXPECTED_VERSION, _OUT_DIR = AGENTS["mini"]
PROVIDER = "openai"
REASONING_EFFORT = "none"
REQUEST_TIMEOUT_S = 120.0
SESSIONS_PER_CASE = 3
OUT = Path(__file__).resolve().parent / _OUT_DIR


def _api_key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("AGENT_OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("AGENT_OPENROUTER_API_KEY not in .env")


def _cases() -> list[dict]:
    cases = []
    for path in sorted((ROOT / "dataset").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        cases.append({"case_id": data["case_id"], "label": data["label"], "transcript": data["transcript"]})
    return cases


def _one(case: dict, n: int, key: str) -> str:
    out = OUT / f"{case['case_id']}__{n}.json"
    if out.exists():
        return f"skip {out.name}"
    client = OpenRouterModelClient(
        model=MODEL, api_key=key, reasoning_effort=REASONING_EFFORT,
        provider=PROVIDER, request_timeout_s=REQUEST_TIMEOUT_S,
    )
    transcript = run_case({"case_id": case["case_id"], "transcript": case["transcript"]}, client)
    record = {
        "case_id": case["case_id"], "label": case["label"], "session": n,
        "model": MODEL, "provider": PROVIDER, "reasoning_effort": REASONING_EFFORT,
        "transcript": transcript, "call_log": client.call_log,
    }
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return f"ok {out.name} {transcript['stop_reason']}"


def _verifica(key: str) -> None:
    seen = {}
    for path in sorted(OUT.glob("*.json")):
        for call in json.loads(path.read_text(encoding="utf-8"))["call_log"]:
            gid = call["generation_id"]
            if gid is None:
                continue
            r = httpx.get("https://openrouter.ai/api/v1/generation", params={"id": gid},
                          headers={"Authorization": f"Bearer {key}"}, timeout=60).json()
            d = r.get("data") or {}
            seen[gid] = {"session": path.name, "model": d.get("model"), "provider_name": d.get("provider_name"),
                         "service_tier": d.get("service_tier"), "native_tokens_reasoning": d.get("native_tokens_reasoning")}
    (OUT.parent / ("versioni.json" if OUT.name == "sessioni" else f"versioni-{OUT.name}.json")).write_text(json.dumps(seen, indent=2), encoding="utf-8")
    models = {v["model"] for v in seen.values()}
    print(len(seen), "chiamate; versioni:", models, "atteso:", f"openai/{EXPECTED_VERSION}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="una sola sessione di un caso benigno")
    ap.add_argument("--verifica", action="store_true", help="versione esatta di ogni chiamata")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--agente", choices=sorted(AGENTS), default="mini")
    args = ap.parse_args()
    global MODEL, EXPECTED_VERSION, OUT
    MODEL, EXPECTED_VERSION, out_dir = AGENTS[args.agente]
    OUT = Path(__file__).resolve().parent / out_dir
    OUT.mkdir(exist_ok=True)
    key = _api_key()
    if args.verifica:
        _verifica(key)
        return
    cases = _cases()
    if args.smoke:
        case = next(c for c in cases if c["case_id"] == "simple_ticket_status_lookup")
        print(_one(case, 1, key))
        return
    jobs = [(c, n) for c in cases for n in range(1, SESSIONS_PER_CASE + 1)]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for line in pool.map(lambda j: _one(j[0], j[1], key), jobs):
            print(line, flush=True)


if __name__ == "__main__":
    main()
