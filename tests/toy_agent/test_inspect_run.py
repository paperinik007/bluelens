from __future__ import annotations

import json
from pathlib import Path

import pytest

PUBLISHED_RUN = Path("docs/reports/agentic-threat-detection-2026-08-19")


def _write_run(tmp_path, transcripts, verdict_case_ids=None):
    raw = tmp_path / "raw"
    raw.mkdir(parents=True)
    for case_id, transcript in transcripts.items():
        (raw / f"{case_id}.transcript.json").write_text(
            json.dumps(transcript), encoding="utf-8"
        )
    ids = verdict_case_ids if verdict_case_ids is not None else list(transcripts)
    (tmp_path / "verdicts.jsonl").write_text(
        "\n".join(
            json.dumps({"case_id": c, "status": "ok"}) for c in ids
        )
        + "\n",
        encoding="utf-8",
    )
    return tmp_path


def _transcript(stop_reason="completed", arguments=None):
    turns = [{"seq": 0, "role": "user", "content": "x", "tool_call": None}]
    if arguments is not None:
        turns.append(
            {
                "seq": 1,
                "role": "tool",
                "content": "x",
                "tool_call": {
                    "tool_name": "bulk_export",
                    "arguments": arguments,
                    "result": "r",
                    "status": "ok",
                },
            }
        )
    return {"session_id": "s", "turns": turns, "stop_reason": stop_reason}


# ---------------------------------------------------------------------------
# The tests
# ---------------------------------------------------------------------------


def test_it_counts_stop_reasons(tmp_path):
    from toy_agent.inspect_run import inspect_run

    transcripts = {
        "c1": _transcript(stop_reason="completed"),
        "c2": _transcript(stop_reason="max_turns"),
    }
    run_dir = _write_run(tmp_path, transcripts)

    result = inspect_run(run_dir)

    assert result["transcript_count"] == 2
    assert result["stop_reasons"] == {"completed": 1, "max_turns": 1}


def test_it_counts_empty_argument_dicts(tmp_path):
    from toy_agent.inspect_run import inspect_run

    transcripts = {
        "c1": _transcript(arguments={}),
        "c2": _transcript(arguments={"ticket_id": "tkt_001"}),
    }
    run_dir = _write_run(tmp_path, transcripts)

    result = inspect_run(run_dir)

    assert result["empty_arguments"] == 1


def test_it_counts_non_dict_arguments(tmp_path):
    from toy_agent.inspect_run import inspect_run

    # _transcript(arguments=None) does not create a tool_call turn (the helper
    # checks "if arguments is not None"), so build the None-arguments case by hand.
    t_none_args = {
        "session_id": "s",
        "turns": [
            {"seq": 0, "role": "user", "content": "x", "tool_call": None},
            {
                "seq": 1,
                "role": "tool",
                "content": "x",
                "tool_call": {
                    "tool_name": "bulk_export",
                    "arguments": None,
                    "result": "r",
                    "status": "ok",
                },
            },
        ],
        "stop_reason": "completed",
    }
    transcripts = {
        "c1": _transcript(arguments=[1, 2]),
        "c2": t_none_args,
    }
    run_dir = _write_run(tmp_path, transcripts)

    result = inspect_run(run_dir)

    assert result["non_dict_arguments"] == 2


def test_it_counts_cases_whose_transcript_is_missing(tmp_path):
    from toy_agent.inspect_run import inspect_run

    transcripts = {"c1": _transcript()}
    run_dir = _write_run(tmp_path, transcripts, verdict_case_ids=["c1", "c2"])

    result = inspect_run(run_dir)

    assert result["missing_transcripts"] == ["c2"]


def test_it_flags_a_transcript_left_behind_by_a_previous_run(tmp_path):
    from toy_agent.inspect_run import inspect_run, format_inspection

    transcripts = {"c_old": _transcript()}
    run_dir = _write_run(tmp_path, transcripts, verdict_case_ids=["c1"])

    result = inspect_run(run_dir)

    assert result["stale_transcripts"] == ["c_old"]
    assert "STALE" in format_inspection(result)


def test_it_reads_the_explicit_counters_on_a_post_fix_run(tmp_path):
    from toy_agent.inspect_run import inspect_run

    t = _transcript(arguments={"x": 1})
    t["model_retry_count"] = 2
    # add a tool call with arguments_parse_failed=True
    t["turns"].append(
        {
            "seq": 2,
            "role": "tool",
            "content": "bad",
            "tool_call": {
                "tool_name": "run_diagnostic",
                "arguments": {},
                "result": "parse error",
                "status": "error",
                "arguments_parse_failed": True,
            },
        }
    )
    transcripts = {"c1": t}
    run_dir = _write_run(tmp_path, transcripts)

    result = inspect_run(run_dir)

    assert result["model_retries"] == 2
    assert result["arguments_parse_failed"] == 1


def test_the_published_run_is_inspectable_by_anyone_with_the_repo():
    from toy_agent.inspect_run import inspect_run

    result = inspect_run(PUBLISHED_RUN)

    assert result["transcript_count"] == 31
    assert result["stop_reasons"] == {"completed": 31}
    assert result["empty_arguments"] == 0
    assert result["non_dict_arguments"] == 0
    assert result["missing_transcripts"] == []
    assert result["stale_transcripts"] == []


def test_corrupt_transcript_file_is_reported_not_crashed(tmp_path):
    from toy_agent.inspect_run import inspect_run, format_inspection

    raw = tmp_path / "raw"
    raw.mkdir()
    # A valid transcript
    (raw / "c1.transcript.json").write_text(
        json.dumps({"session_id": "s1", "turns": [], "stop_reason": "completed"}),
        encoding="utf-8",
    )
    # A corrupt transcript (not valid JSON)
    (raw / "c2.transcript.json").write_text("this is not json", encoding="utf-8")
    (tmp_path / "verdicts.jsonl").write_text(
        json.dumps({"case_id": "c1", "status": "ok"}) + "\n" +
        json.dumps({"case_id": "c2", "status": "ok"}) + "\n",
        encoding="utf-8",
    )

    result = inspect_run(tmp_path)

    # The valid transcript is counted
    assert result["transcript_count"] == 2  # both files were attempted
    assert result["corrupt_transcripts"] == [("c2.transcript.json", "JSONDecodeError")]
    # The corrupt file's case_id is not added to transcript_case_ids
    # so it appears as missing (verdict exists but no transcript was read)
    assert "c2" in result["missing_transcripts"]

    output = format_inspection(result)
    assert "corrupt transcripts (skipped):" in output
    assert "c2.transcript.json" in output
    assert "JSONDecodeError" in output


def test_no_corrupt_transcripts_reported_for_clean_run(tmp_path):
    from toy_agent.inspect_run import inspect_run, format_inspection

    transcripts = {"c1": _transcript()}
    run_dir = _write_run(tmp_path, transcripts)

    result = inspect_run(run_dir)
    assert result["corrupt_transcripts"] == []
    output = format_inspection(result)
    assert "corrupt transcripts (skipped): none" in output