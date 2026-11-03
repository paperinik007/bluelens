"""Every written case of ours sits in the cell the drawn assignment gave its id.

Source: docs/design/2026-10-11-piano-run-v3.md, part 5, "Esito valido, dopo la correzione"
(2026-10-19, seed 3272053868). Cells are not chosen by hand: a case that fills another cell
than the one drawn for its id is a different case, not a rewording (plan, part 5, point 3).
"""
from pathlib import Path

import pytest
import yaml

CASES_DIR = Path(__file__).resolve().parents[2] / "dataset_v3" / "cases"
DRAW_SEED = 3272053868

_REQUEST = {
    "disguised_injection": ["harm_to_third_parties", "resource_consumption", "system_discovery", "harm_to_third_parties"],
    "override": ["money_movement", "money_movement", "destruction", "data_tampering"],
    "pretext": ["user_deception", "persistence", "permission_change", "command_execution"],
    "explicit": ["command_execution", "data_exposure", "credential_theft"],
}
_CONTENT = {
    "disguised_injection": ["data_tampering", "money_movement", "resource_consumption", "harm_to_third_parties"],
    "override": ["user_deception", "user_deception", "permission_change", "persistence"],
    "pretext": ["system_discovery", "credential_theft", "system_discovery", "destruction"],
}


def _drawn() -> dict[str, tuple[str, str, str]]:
    drawn = {}
    number = 1
    for where, table in (("request", _REQUEST), ("content", _CONTENT)):
        for form, actions in table.items():
            for action in actions:
                drawn[f"v3_n{number:02d}"] = (where, form, action)
                number += 1
    return drawn


DRAWN = _drawn()


def test_the_drawn_table_has_27_cases():
    assert len(DRAWN) == 27
    assert DRAWN["v3_n09"] == ("request", "pretext", "user_deception")
    assert DRAWN["v3_n16"] == ("content", "disguised_injection", "data_tampering")
    assert DRAWN["v3_n27"] == ("content", "pretext", "destruction")


@pytest.mark.parametrize("path", sorted(CASES_DIR.glob("v3_n*.yaml")), ids=lambda p: p.stem)
def test_a_written_case_fills_the_cell_drawn_for_its_id(path):
    card = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert card["case_id"] in DRAWN, f"{card['case_id']} is not an id of the drawn assignment"
    where, form, action = DRAWN[card["case_id"]]
    assert (card["where"], card["form"], card["actions"]) == (where, form, [action])
    assert card["cell"]["slot"] == f"{where} x {form}"
    assert card["cell"]["seed"] == DRAW_SEED and card["cell"]["drawn"] is True
