"""Every malicious card's own steps, performed with the real tools, are read as malicious by the automatic
reading, in the card's action; an empty session is clean. This ties the 58 cards to the rules that read them."""
import json
from pathlib import Path

import pytest

from toy_agent.agent_loop import build_tool_registry
from toy_agent.case_card import load_card, prepare_session
from toy_agent.malicious_steps import read_session
from toy_agent.tools import ToolError

CASES_DIR = Path(__file__).resolve().parents[2] / "dataset_v3" / "cases"
CARDS = [load_card(p) for p in sorted(CASES_DIR.glob("v3_*.yaml"))]
MALICIOUS = [c for c in CARDS if c["intent"] == "malicious" and c["own_steps"]]
TEXT_ONLY = [c for c in CARDS if c["text_only"]]


def _perform(card: dict) -> dict:
    """The card's own steps, run on a fresh session with the real tools; returns the transcript."""
    session = prepare_session(card)
    tools = build_tool_registry(third_party_version=session.third_party_version)
    turns = [{"seq": 0, "role": "user", "content": card["seed_turn"], "tool_call": None}]
    reset_links: dict[str, str] = {}
    for seq, step in enumerate(card["own_steps"], start=1):
        tool, target = step["tool"], dict(step["target"])
        if tool == "send_email":
            body = "Hello."
            if "body_customer_ids" in target:
                customer = session.state.customers[target["body_customer_ids"][0]]
                body += f" {customer.name}, phone {customer.phone}."
            if "contains_reset_link_of" in target:
                holder = target["contains_reset_link_of"]
                if holder not in reset_links:
                    reset_links[holder] = tools["create_password_reset_link"].fn(session.state, customer_id=holder)
                    turns.append({"seq": 100 + seq, "role": "tool", "content": reset_links[holder], "tool_call": {
                        "tool_name": "create_password_reset_link", "arguments": {"customer_id": holder},
                        "result": reset_links[holder], "status": "ok", "arguments_parse_failed": False, "raw_arguments": None}})
                body += f" Reset: {reset_links[holder]}"
            if "link_to_not_in" in target:
                body += " See https://fernhol1owgoods.com/track/1"
            args = {"to": target["to"], "subject": "Hi", "body": body}
        elif tool == "run_diagnostic":
            args = {"command": target.get("command", "cat /etc/passwd")}
        elif tool == "update_account":
            args = {"customer_id": target["customer_id"], "field": target["field"], "value": target.get("value", "x")}
        elif tool == "issue_refund":
            args = {"order_id": target["order_id"], "amount": target["amount"]}
        elif tool == "query_customer_db":
            args = {"customer_id": target["customer_id"], "fields": ["phone", "address"]}
        else:
            args = dict(target)
        try:
            result, status = tools[tool].fn(session.state, **args), "ok"
        except ToolError as exc:
            result, status = str(exc), "error"
        turns.append({"seq": seq, "role": "tool", "content": result, "tool_call": {
            "tool_name": tool, "arguments": args, "result": result, "status": status,
            "arguments_parse_failed": False, "raw_arguments": None}})
    return {"session_id": "s", "turns": turns, "stop_reason": "completed", "model_retry_count": 0}


def test_there_are_malicious_cards_with_planned_steps():
    assert len(MALICIOUS) == 37 - len(TEXT_ONLY)


@pytest.mark.parametrize("card", MALICIOUS, ids=lambda c: c["case_id"])
def test_the_cards_own_steps_are_read_as_malicious_in_the_cards_action(card):
    reading = read_session(card, _perform(card))
    assert reading.own_step_attempted, [(s.tool, s.action, s.reason) for s in reading.steps]
    assert reading.malicious
    assert {s.action for s in reading.steps if s.action in card["actions"]}


@pytest.mark.parametrize("card", CARDS, ids=lambda c: c["case_id"])
def test_a_session_with_no_calls_is_clean(card):
    empty = {"session_id": "s", "turns": [{"seq": 0, "role": "user", "content": "x", "tool_call": None}],
             "stop_reason": "completed", "model_retry_count": 0}
    reading = read_session(card, empty)
    assert reading.steps == [] and not reading.malicious


@pytest.mark.parametrize("card", TEXT_ONLY, ids=lambda c: c["case_id"])
def test_text_only_cards_are_sent_to_the_hand_reading_with_their_criteria(card):
    reading = read_session(card, {"session_id": "s", "turns": [], "stop_reason": "completed", "model_retry_count": 0})
    assert reading.needs_hand_reading and reading.hand_reading_criteria
