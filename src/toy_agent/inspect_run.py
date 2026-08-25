from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import provenance


def inspect_run(run_output_dir: Path) -> dict:
    """Read raw/*.transcript.json files and verdicts.jsonl from a run
    output directory and return a dict of observed counters — without
    importing dataclasses or detector_adapter (design doc section 8)."""
    raw_dir = run_output_dir / "raw"

    # --- Read transcripts ---------------------------------------------------
    transcript_count = 0
    stop_reasons: dict[str, int] = {}
    tool_calls = 0
    empty_arguments = 0
    non_dict_arguments = 0
    arguments_parse_failed = 0
    model_retries = 0
    transcript_case_ids: set[str] = set()

    if raw_dir.is_dir():
        for transcript_path in sorted(raw_dir.glob("*.transcript.json")):
            transcript_case_ids.add(transcript_path.stem.split(".transcript")[0])
            transcript_count += 1
            d = json.loads(transcript_path.read_text(encoding="utf-8"))

            sr = d.get("stop_reason")
            if sr is not None:
                stop_reasons[sr] = stop_reasons.get(sr, 0) + 1

            model_retries += d.get("model_retry_count", 0)

            for turn in d.get("turns", []):
                tc = turn.get("tool_call")
                if tc is None:
                    continue
                tool_calls += 1

                args = tc.get("arguments")
                if isinstance(args, dict):
                    if args == {}:
                        empty_arguments += 1
                else:
                    non_dict_arguments += 1

                if tc.get("arguments_parse_failed", False):
                    arguments_parse_failed += 1

    # --- Read verdicts ------------------------------------------------------
    verdicts_path = run_output_dir / "verdicts.jsonl"
    verdict_case_ids: set[str] = set()
    if verdicts_path.exists():
        for line in verdicts_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            vd = json.loads(line)
            cid = vd.get("case_id")
            if cid:
                verdict_case_ids.add(cid)

    missing_transcripts = sorted(verdict_case_ids - transcript_case_ids)
    stale_transcripts = sorted(transcript_case_ids - verdict_case_ids)

    prov = provenance.read_provenance(run_output_dir)

    return {
        "transcript_count": transcript_count,
        "tool_calls": tool_calls,
        "empty_arguments": empty_arguments,
        "non_dict_arguments": non_dict_arguments,
        "arguments_parse_failed": arguments_parse_failed,
        "model_retries": model_retries,
        "stop_reasons": stop_reasons,
        "missing_transcripts": missing_transcripts,
        "stale_transcripts": stale_transcripts,
        "provenance": prov,
    }


def format_inspection(result: dict) -> str:
    """Format the inspection result as multi-line readable text."""
    lines: list[str] = []
    lines.append(f"transcript_count: {result.get('transcript_count', 0)}")
    lines.append(f"tool_calls: {result.get('tool_calls', 0)}")
    lines.append(f"empty_arguments: {result.get('empty_arguments', 0)}")
    lines.append(f"non_dict_arguments: {result.get('non_dict_arguments', 0)}")
    lines.append(f"arguments_parse_failed: {result.get('arguments_parse_failed', 0)}")
    lines.append(f"model_retries: {result.get('model_retries', 0)}")

    stop_reasons = result.get("stop_reasons", {})
    if stop_reasons:
        sr_parts = [f"{k}: {v}" for k, v in sorted(stop_reasons.items())]
        lines.append(f"stop_reasons: {{{', '.join(sr_parts)}}}")
    else:
        lines.append("stop_reasons: {}")

    missing = result.get("missing_transcripts", [])
    if missing:
        lines.append(f"missing_transcripts: {missing}")
    else:
        lines.append("missing_transcripts: []")

    stale = result.get("stale_transcripts", [])
    if stale:
        lines.append(f"STALE TRANSCRIPTS (not in verdicts.jsonl): {stale}")
    else:
        lines.append("stale_transcripts: []")

    prov = result.get("provenance")
    if prov is not None:
        lines.append(f"provenance: {provenance.format_provenance(prov)}")
    else:
        lines.append("provenance: not recorded")

    return "\n".join(lines)


def main(argv=None) -> None:
    args = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="python -m toy_agent.inspect_run")
    parser.add_argument("run_output_dir", help="Path to a run output directory")
    parsed = parser.parse_args(args)

    result = inspect_run(Path(parsed.run_output_dir))
    print(format_inspection(result))