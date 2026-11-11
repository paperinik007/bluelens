"""Check that the run was made under the frozen conditions (plan, part 12 and part 13 additions, point 7 of the integrity review).

    python -m toy_agent.check_conditions --expected dataset_v3/condizioni_attese.json \
        [--sessions DIR] [--verdicts DIR] [--reviewer DIR]

Reads only what the run recorded about itself (never a label, a verdict or a reading): for the agent the model, provider and
reasoning tokens of every answered call in `call_log`; for each judge the "model | provider" pairs that answered
(`served_by`); for the reviewer the model and provider of every saved reading. Anything outside the expected values is
listed and the exit code is 1: the wave stops and the owner decides (a change of model or provider is a change of the
instrument). It does not stop a run by itself: it is a step of the commands, run after the sessions and after the verdicts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def check_sessions(directory: Path, expected: dict) -> list[str]:
    problems: list[str] = []
    for path in sorted(Path(directory).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for i, call in enumerate(data.get("call_log", [])):
            if call.get("error"):
                continue  # a failed attempt answered nothing: it names no model
            if call.get("model") != expected["model"]:
                problems.append(f"{path.name} call {i}: model {call.get('model')!r}, expected {expected['model']!r}")
            if call.get("provider") != expected["provider"]:
                problems.append(f"{path.name} call {i}: provider {call.get('provider')!r}, expected {expected['provider']!r}")
            if (call.get("reasoning_tokens") or 0) > expected.get("max_reasoning_tokens", 0):
                problems.append(f"{path.name} call {i}: {call.get('reasoning_tokens')} reasoning tokens")
        asked = data.get("conditions")
        if asked is not None and asked.get("reasoning_effort") != expected.get("reasoning_effort"):
            problems.append(f"{path.name}: reasoning effort asked {asked.get('reasoning_effort')!r}, expected "
                            f"{expected.get('reasoning_effort')!r}")
    return problems


def check_verdicts(directory: Path, expected: dict[str, list[str]]) -> list[str]:
    problems: list[str] = []
    for path in sorted(Path(directory).glob("*.json")):
        if path.name.endswith(".fail.json"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        judge = data.get("judge")
        if judge not in expected:
            problems.append(f"{path.name}: unknown judge {judge!r}")
            continue
        for pair in data.get("served_by", {}):
            if pair not in expected[judge]:
                problems.append(f"{path.name}: {judge} answered by {pair!r}, not in the expected {expected[judge]!r}")
    return problems


def check_reviewer(directory: Path, expected: dict) -> list[str]:
    problems: list[str] = []
    for path in sorted(Path(directory).glob("S*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("model") != expected["model"] or data.get("provider") != expected["provider"]:
            problems.append(f"{path.name}: {data.get('model')!r} / {data.get('provider')!r}, expected "
                            f"{expected['model']!r} / {expected['provider']!r}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--sessions", type=Path)
    parser.add_argument("--verdicts", type=Path)
    parser.add_argument("--reviewer", type=Path)
    args = parser.parse_args()
    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    problems: list[str] = []
    if args.sessions:
        problems += check_sessions(args.sessions, expected["agent"])
    if args.verdicts:
        problems += check_verdicts(args.verdicts, expected["judges"])
    if args.reviewer:
        problems += check_reviewer(args.reviewer, expected["reviewer"])
    for line in problems:
        print(line)
    print(f"{len(problems)} problems" if problems else "conditions as expected")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
