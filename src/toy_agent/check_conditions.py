"""Check that the run was made under the frozen conditions (plan, part 12 and part 13 additions, point 7 of the integrity review).

    python -m toy_agent.check_conditions --expected dataset_v3/condizioni_attese.json \
        [--sessions DIR] [--generations FILE] [--verdicts DIR] [--reviewer DIR]

Reads only what the run recorded about itself (never a label, a verdict or a reading): for the agent the model, provider and
reasoning tokens of every answered call in `call_log`; for each judge the "model | provider" pairs that answered
(`served_by`; a verdict of a judge that has expected pairs but records none is a problem: its log was not read); for the
reviewer the model and provider of every saved reading and the fingerprint of the instructions it was given (`sistema.sha256`,
against `instructions_sha256` of the expected file); with `--generations` (the file written by `registra_versioni`) the exact
dated version and provider that OpenRouter's generation record names for every answered call of the agent. Anything outside the expected values is
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
        if expected[judge] and not data.get("served_by"):
            problems.append(f"{path.name}: {judge} has expected pairs but the verdict records none (log not read)")
        for pair in data.get("served_by", {}):
            if pair not in expected[judge]:
                problems.append(f"{path.name}: {judge} answered by {pair!r}, not in the expected {expected[judge]!r}")
    return problems


def check_generations(sessions: Path, generations: Path, expected: dict) -> list[str]:
    """Every answered call of the agent must have a generation record naming the expected dated version and provider."""
    records = json.loads(Path(generations).read_text(encoding="utf-8"))
    problems: list[str] = []
    files = sorted(Path(sessions).glob("*.json"))
    if not files:
        return [f"no session file in {sessions}: the check would pass without having checked anything"]
    for path in files:
        calls = json.loads(path.read_text(encoding="utf-8")).get("call_log")
        if not calls:             # key missing or empty: nothing to check is a problem, not a pass
            problems.append(f"{path.name}: no call_log (missing or empty), the dated version cannot be checked")
            continue
        for i, call in enumerate(calls):
            gid = call.get("generation_id")
            if call.get("error"):
                continue          # a failed attempt names no model: not a problem
            if not gid:           # answered but never identified: the check would pass without having checked anything
                problems.append(f"{path.name} call {i}: answered call without a generation_id, the dated version cannot be checked")
                continue
            rec = records.get(gid)
            if not rec or rec.get("error"):
                problems.append(f"{path.name} call {i}: no generation record for {gid} ({(rec or {}).get('error', 'not fetched')})")
            elif rec.get("model") != expected["version"] or rec.get("provider_name") != expected["provider"]:
                problems.append(f"{path.name} call {i}: generation record names {rec.get('model')!r} / {rec.get('provider_name')!r}, "
                                f"expected {expected['version']!r} / {expected['provider']!r}")
    return problems


def check_reviewer(directory: Path, expected: dict) -> list[str]:
    problems: list[str] = []
    want = expected.get("instructions_sha256")
    if want:
        f = Path(directory) / "sistema.sha256"
        got = f.read_text(encoding="utf-8").strip() if f.exists() else None
        if got != want:
            problems.append(f"sistema.sha256: instructions fingerprint {got!r}, expected {want!r}")
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
    parser.add_argument("--generations", type=Path)
    parser.add_argument("--verdicts", type=Path)
    parser.add_argument("--reviewer", type=Path)
    args = parser.parse_args()
    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    problems: list[str] = []
    if args.sessions:
        problems += check_sessions(args.sessions, expected["agent"])
    if args.generations:
        if not args.sessions:
            parser.error("--generations needs --sessions")
        problems += check_generations(args.sessions, args.generations, expected["agent"])
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
