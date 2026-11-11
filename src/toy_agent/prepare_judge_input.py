"""Turns saved v3 sessions (as `run_card` writes them) into what the judges read, with no case name anywhere.

A judge adapter reads `session_id` and `turns` at the top level of its input, and aidr also reads
`third_party_version` (the integration code it may inspect). A `run_card` file keeps the transcript under
`transcript` and carries the case id, the final state and more: none of that goes to a judge. The map from the
opaque session id back to the case is written outside the folder the judges read.

    python -m toy_agent.prepare_judge_input SESSIONS_DIR OUT_DIR MAP_FILE
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def judge_input(session: dict) -> dict:
    """The input of one judge: the transcript at the top level, plus the integration version. Nothing else."""
    transcript = session["transcript"]
    for key in ("session_id", "turns"):
        if key not in transcript:
            raise ValueError(f"transcript has no {key!r}")
    result = {**transcript, "third_party_version": session["third_party_version"]}
    case_id = session["case_id"]
    if case_id in json.dumps(result, ensure_ascii=False):
        raise ValueError(f"the case id {case_id!r} appears in what a judge would read")
    return result


def prepare(sessions_dir: Path, out_dir: Path, map_file: Path) -> dict[str, dict]:
    sessions_dir, out_dir, map_file = Path(sessions_dir), Path(out_dir), Path(map_file)
    if out_dir.resolve() in map_file.resolve().parents:
        raise ValueError("the map file must not be inside the folder the judges read")
    out_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, dict] = {}
    for path in sorted(sessions_dir.glob("*.json")):
        session = json.loads(path.read_text(encoding="utf-8"))
        data = judge_input(session)
        sid = data["session_id"]
        if sid in mapping:
            raise ValueError(f"two sessions share the id {sid!r}")
        (out_dir / f"{sid}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        mapping[sid] = {"case_id": session["case_id"], "file": path.name}
    map_file.parent.mkdir(parents=True, exist_ok=True)
    map_file.write_text(json.dumps(mapping, indent=1, ensure_ascii=False), encoding="utf-8")
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m toy_agent.prepare_judge_input")
    parser.add_argument("sessions_dir", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("map_file", type=Path)
    args = parser.parse_args()
    mapping = prepare(args.sessions_dir, args.out_dir, args.map_file)
    print(f"{len(mapping)} sessions prepared in {args.out_dir}; map in {args.map_file}")


if __name__ == "__main__":
    main()
