import pytest
import yaml

from toy_agent.dataset import load_dataset


def _entry(case_id: str, label: str = "benign", technique_target: str | None = None, rationale: str = "r") -> dict:
    return {
        "case_id": case_id,
        "label": label,
        "technique_target": technique_target,
        "rationale": rationale,
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
    _write(tmp_path, "case_002.yaml", _entry("case_002", label="malicious", technique_target="T0001"))

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
