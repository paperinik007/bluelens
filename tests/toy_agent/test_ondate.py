import json
import pytest

from toy_agent import ondate


def test_every_case_is_in_exactly_one_wave():
    strata = ondate.load_strata()
    waves = ondate.divide(strata, seed=7)
    all_ids = sorted(c for ids in strata.values() for c in ids)
    assert len(all_ids) == 58
    assert sorted(c for ids in waves.values() for c in ids) == all_ids


def test_each_wave_takes_cases_from_every_cell_that_has_three_or_more():
    strata = ondate.load_strata()
    waves = ondate.divide(strata, seed=7)
    for name, ids in strata.items():
        if len(ids) >= 3:
            assert all(sum(1 for c in ids if c in waves[w]) >= 1 for w in waves), name


def test_a_cell_is_spread_as_evenly_as_it_can_be_and_the_waves_are_balanced():
    strata = ondate.load_strata()
    waves = ondate.divide(strata, seed=7)
    for name, ids in strata.items():
        per_wave = [sum(1 for c in ids if c in waves[w]) for w in waves]
        assert max(per_wave) - min(per_wave) <= 1, name
    sizes = [len(v) for v in waves.values()]
    assert max(sizes) - min(sizes) <= 1, sizes


def test_the_three_benign_tool_twins_are_one_per_wave():
    waves = ondate.divide(ondate.load_strata(), seed=7)
    assert [sum(1 for c in waves[w] if c in ("v3_b19", "v3_b20", "v3_b21")) for w in waves] == [1, 1, 1]


def test_the_same_seed_gives_the_same_division_and_another_seed_a_different_one():
    strata = ondate.load_strata()
    assert ondate.divide(strata, 7) == ondate.divide(strata, 7)
    assert ondate.divide(strata, 7) != ondate.divide(strata, 8)


def test_the_division_is_pinned_by_a_known_value_so_a_change_of_algorithm_is_noticed():
    """If this fails the algorithm or the cards changed: the division in dataset_v3/ondate.json would not be reproducible."""
    waves = ondate.divide({"s": ["a", "b", "c"], "t": ["d", "e", "f", "g"]}, seed=123)
    assert waves == {1: ['a', 'f', 'g'], 2: ['b', 'e'], 3: ['c', 'd']}


def test_the_written_file_matches_the_division_the_program_gives_for_its_seed():
    from pathlib import Path
    path = Path(ondate.DEFAULT_FILE)
    if not path.exists():
        pytest.skip("the division is drawn once, before the freeze")
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["waves"] == ondate.build(saved["seed"])["waves"]
