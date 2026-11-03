import json
from pathlib import Path

import yaml

from toy_agent.case_card import load_card
from toy_agent.model_client import ModelReply
from toy_agent.run_card import run_card

CASES_DIR = Path(__file__).resolve().parents[2] / "dataset_v3" / "cases"


class _Script:
    """Scripted model: returns the given replies in order, never touches the network."""

    def __init__(self, *replies):
        self._replies = list(replies)
        self.retry_count = 0

    def complete(self, messages, tools):
        return self._replies.pop(0)


def _call(name, **arguments):
    return ModelReply(
        content="", cost_usd=0.0,
        tool_calls=[{"id": "c1", "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}],
    )


def _say(text):
    return ModelReply(content=text, tool_calls=[], cost_usd=0.0)


def test_run_card_runs_a_card_and_keeps_the_case_id_out_of_the_transcript():
    card = load_card(CASES_DIR / "v3_b07.yaml")
    record = run_card(card, _Script(_call("get_order", order_id="FH-58251"), _say("It is on its way.")))
    transcript = record["transcript"]
    assert record["case_id"] == "v3_b07"
    assert "v3_b07" not in json.dumps(transcript)
    assert transcript["session_id"] and transcript["session_id"] != "v3_b07"
    tools = [t["tool_call"]["tool_name"] for t in transcript["turns"] if t["role"] == "tool"]
    assert tools == ["get_requester_profile", "get_order"]
    assert transcript["stop_reason"] == "completed"


def test_run_card_records_what_changed_in_the_world():
    card = load_card(CASES_DIR / "v3_t01.yaml")
    record = run_card(card, _Script(_call("crm_sync_contact", customer_id="cust_1041"), _say("Synced.")))
    effects = record["state_after"]
    assert record["third_party_version"] == "compromised_data"
    assert len(effects["integration_egress"]) == 2
    assert effects["accounts"]["cust_1041"]["crm_id"].startswith("HCRM-")


def test_run_card_shows_the_agent_the_integration_in_every_case():
    card = load_card(CASES_DIR / "v3_b19.yaml")
    record = run_card(card, _Script(_call("crm_sync_contact", customer_id="cust_1041"), _say("Done.")))
    assert record["third_party_version"] == "honest"
    assert len(record["state_after"]["integration_egress"]) == 1


def test_the_session_is_independent_of_the_card_file():
    card = load_card(CASES_DIR / "v3_b07.yaml")
    before = yaml.safe_dump(card)
    run_card(card, _Script(_say("ok")))
    assert yaml.safe_dump(card) == before
