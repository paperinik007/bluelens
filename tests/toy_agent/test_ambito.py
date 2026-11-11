import json
from pathlib import Path

from toy_agent import ambito


def test_the_counts_are_the_ones_the_security_review_reproduced_from_the_cards():
    b = ambito.build()
    assert b["malicious_cases"] == 37
    assert b["counts"]["promptguard"] == {"wide": 26, "narrow": 8, "actions_only": 0}
    assert b["counts"]["alignmentcheck"]["wide"] == 19 and b["counts"]["alignmentcheck"]["narrow"] == 16
    assert b["counts"]["aidr"] == {"wide": 35, "narrow": 3, "actions_only": 28}


def test_the_narrow_reading_is_always_inside_the_wide_one():
    for case_id, row in ambito.build()["cases"].items():
        for judge, s in row["scope"].items():
            assert not s["narrow"]["in"] or s["wide"]["in"], (case_id, judge)


def test_two_cases_are_outside_aidr_and_three_rest_on_the_extended_catalogue_entry():
    cases = ambito.build()["cases"]
    assert sorted(k for k, v in cases.items() if not v["scope"]["aidr"]["wide"]["in"]) == ["v3_n09", "v3_n10"]
    assert sorted(k for k, v in cases.items() if v["scope"]["aidr"]["wide"].get("extended_only")) == ["v3_n12", "v3_n24", "v3_n26"]


def test_the_written_file_is_the_one_the_program_gives():
    path = Path(__file__).resolve().parents[2] / "dataset_v3" / "ambito.json"
    if path.exists():
        assert json.loads(path.read_text(encoding="utf-8")) == json.loads(json.dumps(ambito.build(), ensure_ascii=False))
