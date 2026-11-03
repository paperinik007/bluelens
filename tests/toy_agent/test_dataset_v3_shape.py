"""Shape of the v3 case set as a whole (plan part 5): counts, references, and that the written steps are calls the agent can make."""
from collections import Counter
from pathlib import Path

import pytest
import yaml

from toy_agent.agent_loop import build_tool_registry
from toy_agent.halvard import THIRD_PARTY_VERSIONS
from toy_agent.state import fresh_state

CASES_DIR = Path(__file__).resolve().parents[2] / "dataset_v3" / "cases"
CARDS = {p.stem: yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(CASES_DIR.glob("v3_*.yaml"))}


def _family(case_id: str) -> str:
    return case_id[3]  # v3_c01 -> c, v3_n01 -> n, v3_t01 -> t, v3_a01 -> a, v3_b01 -> b


def test_the_set_has_the_planned_size_and_families():
    counts = Counter(_family(c) for c in CARDS)
    # collections 4, ours (text) 27, tool 3, agent 3, benign 21; twins are deferred (plan part 4)
    assert counts == {"c": 4, "n": 27, "t": 3, "a": 3, "b": 21}
    assert len(CARDS) == 58


def test_case_ids_match_file_names_and_are_unique():
    assert all(card["case_id"] == name for name, card in CARDS.items())


def test_malicious_and_benign_split():
    assert Counter(c["intent"] for c in CARDS.values()) == {"malicious": 37, "benign": 21}
    assert all(c["actions"] == [] for c in CARDS.values() if c["intent"] == "benign")
    assert all(len(c["actions"]) == 1 for c in CARDS.values() if c["intent"] == "malicious")


def test_every_action_appears_in_the_request_and_in_the_content():
    """Plan part 5, point 3(b): each of the 12 actions at least once in the request and once in the content."""
    places = {}
    for card in CARDS.values():
        if card["intent"] == "malicious" and card["where"] in ("request", "content"):
            places.setdefault(card["actions"][0], set()).add(card["where"])
    assert len(places) == 12
    assert {a for a, w in places.items() if w != {"request", "content"}} == set()


def test_the_three_tool_cases_use_the_three_compromised_versions_once_each():
    versions = sorted(c["world_data"]["third_party_version"] for c in CARDS.values() if c["where"] == "tool")
    assert versions == sorted(v for v in THIRD_PARTY_VERSIONS if v != "honest")
    assert {c["actions"][0] for c in CARDS.values() if c["where"] == "tool"} == {
        "data_exposure", "permission_change", "persistence"}


def test_the_three_agent_cases_have_the_planned_actions():
    assert {c["actions"][0] for c in CARDS.values() if c["where"] == "agent"} == {
        "destruction", "resource_consumption", "data_tampering"}


def test_every_resembles_label_points_to_a_case_of_the_set():
    for card in CARDS.values():
        target = card["labels"].get("resembles")
        assert target is None or target in CARDS, (card["case_id"], target)


def test_every_planned_step_is_a_tool_the_agent_has_and_names_a_customer_of_the_world():
    tools = set(build_tool_registry(third_party_version="honest"))
    customers = set(fresh_state().customers)
    for card in CARDS.values():
        for own in card.get("own_steps") or []:
            assert own["tool"] in tools, (card["case_id"], own["tool"])
            target_customer = own["target"].get("customer_id")
            assert target_customer is None or target_customer in customers, card["case_id"]


def test_ticket_ids_do_not_repeat_across_cases_that_could_share_a_session_family():
    seen = Counter(t["ticket_id"] for c in CARDS.values() for t in c["world_data"]["tickets"])
    assert not [tid for tid, n in seen.items() if n > 1], "a ticket id is used by two cases"


@pytest.mark.parametrize("card", CARDS.values(), ids=lambda c: c["case_id"])
def test_a_ticket_is_short_enough_for_the_512_token_limit(card):
    for t in card["world_data"]["tickets"]:
        assert len(t["content"].split()) <= 250, "about 330 tokens: well inside PromptGuard's 512"
