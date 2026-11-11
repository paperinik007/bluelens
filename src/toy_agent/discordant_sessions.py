"""Lists the sessions whose first two verdicts of a judge disagree, so a third can be asked for (plan part 9, part 13).

    python -m toy_agent.discordant_sessions --verdicts DIR --judge aidr > ids-terzo-verdetto.txt

Only the labels are read. A verdict without a label (an error) does not count as a disagreement: it is asked again by
running the same `judge_sessions` command, never by this list. Sessions that already have a third verdict are left out.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def discordant(verdicts_dir: Path, judge: str) -> list[str]:
    labels: dict[str, dict[int, str]] = {}
    for path in sorted(Path(verdicts_dir).glob(f"*_{judge}_*.json")):
        if path.name.endswith(".fail.json"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        verdict = data.get("verdict") or {}
        if verdict.get("status") != "ok" or not verdict.get("label"):
            continue
        labels.setdefault(data["session_id"], {})[int(data["repeat"])] = verdict["label"]
    result = []
    for sid, by_repeat in sorted(labels.items()):
        if 3 in by_repeat or 1 not in by_repeat or 2 not in by_repeat:
            continue
        if by_repeat[1] != by_repeat[2]:
            result.append(sid)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m toy_agent.discordant_sessions")
    parser.add_argument("--verdicts", type=Path, required=True)
    parser.add_argument("--judge", required=True)
    args = parser.parse_args()
    for sid in discordant(args.verdicts, args.judge):
        print(sid)


if __name__ == "__main__":
    main()
