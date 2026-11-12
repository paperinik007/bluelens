"""Archive the exact model version that answered every call of the agent, from OpenRouter's generation records.

    python -m toy_agent.registra_versioni <cartella-sessioni> <uscita.json>

A session records, for each answered call, the `generation_id`; the request carries only the alias (`openai/gpt-5.4-mini`),
and the dated version (`openai/gpt-5.4-mini-20260317`) appears only in the generation record that OpenRouter keeps for a
limited time. This program fetches the record of every call and saves the few fields that name the instrument (model,
provider, time, reasoning tokens, finish reason) in one JSON file kept in the run folder; `check_conditions --generations`
then compares them with the dated version in the frozen expected conditions. Run it right after the sessions of a wave
(plan, part 12, command 1d): the records are not kept for ever. A record that cannot be fetched is saved with its error and
counts as a problem for the check, never as a pass. The key is read from the environment and never printed or saved.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://openrouter.ai/api/v1/generation?id="
FIELDS = ("model", "provider_name", "created_at", "native_tokens_reasoning", "finish_reason", "upstream_id")
ATTEMPTS = 4
PAUSE_S = 3.0


def fetch_generation(gid: str, key: str) -> dict:
    request = urllib.request.Request(URL + gid, headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    return body.get("data", body)


def collect(sessions: Path, out: Path, fetch, sleep=time.sleep) -> tuple[int, int]:
    """Fetch the record of every answered call; returns (fetched, failed). A record already saved without error is kept."""
    records = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    fetched = failed = 0
    for path in sorted(Path(sessions).glob("*.json")):
        for call in json.loads(path.read_text(encoding="utf-8")).get("call_log", []):
            gid = call.get("generation_id")
            if call.get("error") or not gid:
                continue
            if gid in records and not records[gid].get("error"):
                continue
            error = None
            for attempt in range(ATTEMPTS):
                try:
                    data = fetch(gid)
                    records[gid] = {k: data.get(k) for k in FIELDS}
                    error = None
                    break
                except urllib.error.HTTPError as exc:  # the record may not be ready yet: wait and try again
                    error = f"HTTP {exc.code}"
                except Exception as exc:  # class name only: never the message
                    error = exc.__class__.__name__
                if attempt < ATTEMPTS - 1:
                    sleep(PAUSE_S)
            if error:
                records[gid] = {"error": error}
                failed += 1
            else:
                fetched += 1
    out.write_text(json.dumps(records, indent=1, ensure_ascii=False), encoding="utf-8")
    return fetched, failed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sessions", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("AGENT_OPENROUTER_API_KEY")
    if not key:
        sys.exit("manca OPENROUTER_API_KEY nell'ambiente")
    fetched, failed = collect(args.sessions, args.out, lambda gid: fetch_generation(gid, key))
    print(f"{fetched} records fetched, {failed} failed -> {args.out}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
