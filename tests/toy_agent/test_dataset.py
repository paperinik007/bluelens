import pytest
import yaml

from toy_agent.dataset import load_dataset


def _entry(
    case_id: str, label: str = "benign", technique_target: str | None = None,
    rationale: str = "r", attack_success_criteria: dict | None = None,
) -> dict:
    return {
        "case_id": case_id,
        "label": label,
        "technique_target": technique_target,
        "rationale": rationale,
        "attack_success_criteria": attack_success_criteria,
        "transcript": {
            "session_id": case_id,
            "turns": [{"seq": 0, "role": "user", "content": "hi", "tool_call": None}],
            "stop_reason": None,
        },
    }


def _write(dir_, filename: str, data: dict) -> None:
    (dir_ / filename).write_text(yaml.safe_dump(data), encoding="utf-8")


def test_load_dataset_reads_every_yaml_entry(tmp_path):
    _write(tmp_path, "case_001.yaml", _entry("case_001"))
    _write(tmp_path, "case_002.yaml", _entry(
        "case_002", label="malicious", technique_target="T0001",
        attack_success_criteria={"always": True},
    ))

    cases = load_dataset(tmp_path)

    assert {c.case_id for c in cases} == {"case_001", "case_002"}
    malicious = next(c for c in cases if c.case_id == "case_002")
    assert malicious.technique_target == "T0001"
    assert malicious.transcript.turns[0].content == "hi"


def test_load_dataset_rejects_a_case_id_with_a_path_separator(tmp_path):
    _write(tmp_path, "evil.yaml", _entry("../evil"))

    with pytest.raises(ValueError):
        load_dataset(tmp_path)


def test_load_dataset_rejects_a_case_id_with_a_space(tmp_path):
    _write(tmp_path, "evil.yaml", _entry("case 001"))

    with pytest.raises(ValueError):
        load_dataset(tmp_path)


def test_load_dataset_rejects_duplicate_case_ids(tmp_path):
    _write(tmp_path, "a.yaml", _entry("dup_case"))
    _write(tmp_path, "b.yaml", _entry("dup_case"))

    with pytest.raises(ValueError):
        load_dataset(tmp_path)


def test_load_dataset_does_not_write_to_the_dataset_dir(tmp_path):
    _write(tmp_path, "case_001.yaml", _entry("case_001"))
    before = (tmp_path / "case_001.yaml").read_text(encoding="utf-8")

    load_dataset(tmp_path)

    after = (tmp_path / "case_001.yaml").read_text(encoding="utf-8")
    assert before == after


def test_load_dataset_rejects_an_empty_yaml_file(tmp_path):
    (tmp_path / "empty.yaml").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="empty.yaml"):
        load_dataset(tmp_path)


def test_load_dataset_rejects_a_yaml_document_that_is_a_list(tmp_path):
    (tmp_path / "list.yaml").write_text(yaml.safe_dump([_entry("case_001")]), encoding="utf-8")

    with pytest.raises(ValueError, match="list.yaml"):
        load_dataset(tmp_path)


@pytest.mark.parametrize("missing_field", ["label", "rationale", "transcript"])
def test_load_dataset_rejects_an_entry_missing_a_required_field(tmp_path, missing_field):
    entry = _entry("case_001")
    del entry[missing_field]
    _write(tmp_path, "case_001.yaml", entry)

    with pytest.raises(ValueError, match=f"case_001.yaml.*{missing_field}"):
        load_dataset(tmp_path)


def test_load_dataset_rejects_a_transcript_with_zero_turns(tmp_path):
    entry = _entry("case_001")
    entry["transcript"]["turns"] = []
    _write(tmp_path, "case_001.yaml", entry)

    with pytest.raises(ValueError, match="case_001.yaml"):
        load_dataset(tmp_path)


def test_load_dataset_rejects_a_transcript_with_two_turns(tmp_path):
    entry = _entry("case_001")
    entry["transcript"]["turns"] = [
        {"seq": 0, "role": "user", "content": "hi", "tool_call": None},
        {"seq": 1, "role": "user", "content": "again", "tool_call": None},
    ]
    _write(tmp_path, "case_001.yaml", entry)

    with pytest.raises(ValueError, match="case_001.yaml"):
        load_dataset(tmp_path)


def test_load_dataset_rejects_a_seed_turn_with_a_non_user_role(tmp_path):
    entry = _entry("case_001")
    entry["transcript"]["turns"] = [{"seq": 0, "role": "assistant", "content": "hi", "tool_call": None}]
    _write(tmp_path, "case_001.yaml", entry)

    with pytest.raises(ValueError, match="case_001.yaml"):
        load_dataset(tmp_path)


def test_load_dataset_rejects_a_seed_turn_with_empty_content(tmp_path):
    entry = _entry("case_001")
    entry["transcript"]["turns"] = [{"seq": 0, "role": "user", "content": "", "tool_call": None}]
    _write(tmp_path, "case_001.yaml", entry)

    with pytest.raises(ValueError, match="case_001.yaml"):
        load_dataset(tmp_path)
