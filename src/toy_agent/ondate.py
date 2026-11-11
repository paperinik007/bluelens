"""Division of the 58 cases into the three waves of the run (plan, part 13, "Run in tre ondate").

    python -m toy_agent.ondate --seed N --write dataset_v3/ondate.json     # once, before the freeze
    python -m toy_agent.ondate --wave 2                                   # the card paths of wave 2, for run_card

Each wave takes cases from every cell (slot): a cell of 3 cases gives one to each wave, a cell of 4 gives 1, 1 and 2 (the extra
one goes to the wave with the fewest cases so far). The 21 benign cases are dealt the same way, the three tool twins (`benign x
tool`) as their own group so that each wave has one. Nothing is drawn with a random generator whose algorithm could change
between Python versions: cases are ordered by SHA-256 of "seed:case_id", so the same seed and the same cards give the same
division anywhere. The seed is chosen and written down before this program is run; the file it writes is in the list of
fingerprints.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from pathlib import Path

import yaml

WAVES = 3
CASES = Path(__file__).resolve().parents[2] / "dataset_v3" / "cases"
DEFAULT_FILE = Path(__file__).resolve().parents[2] / "dataset_v3" / "ondate.json"


def _h(seed: int, *parts: object) -> str:
    return hashlib.sha256(":".join([str(seed), *map(str, parts)]).encode()).hexdigest()


def stratum_of(card: dict) -> str:
    """The group a case is dealt from: its cell; the benign cases of the 'tool' cell stay together, the other benign cases form one group."""
    slot = (card.get("cell") or {}).get("slot") or "?"
    if card["intent"] == "malicious":
        return f"malicious | {slot}"
    return "benign | tool" if slot == "benign x tool" else "benign | other"


def divide(strata: dict[str, list[str]], seed: int, waves: int = WAVES) -> dict[int, list[str]]:
    """{stratum: [case ids]} -> {wave number: [case ids]}. Every stratum is spread over the waves as evenly as it can be."""
    out: dict[int, list[str]] = {w: [] for w in range(1, waves + 1)}
    for name in sorted(strata):
        for case_id in sorted(strata[name], key=lambda c: _h(seed, c)):
            # the wave with the fewest cases of this stratum, then the fewest in all, then a tie broken by the seed
            wave = min(out, key=lambda w: (sum(1 for c in out[w] if c in strata[name]), len(out[w]), _h(seed, name, w)))
            out[wave].append(case_id)
    return {w: sorted(v) for w, v in out.items()}


def load_strata(cases_dir: Path = CASES) -> dict[str, list[str]]:
    strata: dict[str, list[str]] = {}
    for path in sorted(Path(cases_dir).glob("v3_*.yaml")):
        card = yaml.safe_load(path.read_text(encoding="utf-8"))
        strata.setdefault(stratum_of(card), []).append(card["case_id"])
    return strata


def build(seed: int, cases_dir: Path = CASES) -> dict:
    strata = load_strata(cases_dir)
    waves = divide(strata, seed)
    return {
        "seed": seed, "python": platform.python_version(), "algorithm": "SHA-256 of 'seed:case_id', least-loaded wave first",
        "strata": {k: sorted(v) for k, v in sorted(strata.items())},
        "waves": {str(w): ids for w, ids in waves.items()},
    }


def card_paths(wave: int, file: Path = DEFAULT_FILE, cases_dir: Path = CASES) -> list[Path]:
    data = json.loads(Path(file).read_text(encoding="utf-8"))
    return [Path(cases_dir) / f"{case_id}.yaml" for case_id in data["waves"][str(wave)]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int)
    parser.add_argument("--write", type=Path)
    parser.add_argument("--wave", type=int)
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    args = parser.parse_args()
    if args.write:
        if args.seed is None:
            parser.error("--write needs --seed (chosen and written down before running this)")
        if args.write.exists():
            parser.error(f"{args.write} exists: the division is drawn once and never redone")
        args.write.write_text(json.dumps(build(args.seed), indent=1, ensure_ascii=False), encoding="utf-8")
        print(args.write)
    elif args.wave:
        print(" ".join(Path(os.path.relpath(p)).as_posix() for p in card_paths(args.wave, args.file)))
    else:
        parser.error("--write or --wave")
    sys.exit(0)


if __name__ == "__main__":
    main()
