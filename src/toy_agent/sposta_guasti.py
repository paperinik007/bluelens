"""Move the sessions that ended by a fault of the environment out of the sessions folder, before any reading (plan, part 13,
additions, point 3).

    python -m toy_agent.sposta_guasti ONDATA/sessioni ONDATA/sessioni-guasto

Valid sessions end `completed` or `max_turns`. `model_error` and `max_cost` are faults of the environment (a provider down, a key
over its limit), not behaviors of the agent: the file moves to the fault folder, and rerunning the `run_card` command redoes it
(a saved session is never redone, a moved one is missing). The program decides by the `stop_reason` field only and prints
the file names and the reason, never the content of a session, so nobody picks a session after having read it.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

VALID = {"completed", "max_turns"}


def move_faults(sessions: Path, faults: Path) -> list[tuple[str, str]]:
    moved: list[tuple[str, str]] = []
    for path in sorted(Path(sessions).glob("*.json")):
        reason = json.loads(path.read_text(encoding="utf-8")).get("transcript", {}).get("stop_reason")
        if reason in VALID:
            continue
        Path(faults).mkdir(parents=True, exist_ok=True)
        target = Path(faults) / path.name
        if target.exists():  # a second fault of the same session: keep both, the count of reruns is in the names
            target = Path(faults) / f"{path.stem}.{len(list(Path(faults).glob(path.stem + '*')))+1}{path.suffix}"
        shutil.move(str(path), str(target))
        moved.append((path.name, str(reason)))
    return moved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sessions", type=Path)
    parser.add_argument("faults", type=Path)
    args = parser.parse_args()
    moved = move_faults(args.sessions, args.faults)
    for name, reason in moved:
        print(f"{name}\t{reason}")
    print(f"{len(moved)} sessions moved")
    sys.exit(0)


if __name__ == "__main__":
    main()
