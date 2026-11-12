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
        self.call_log = []

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


class _Failing:
    """A client whose every call fails like a provider outage: the loop ends the session with a model error."""

    def __init__(self):
        self.retry_count = 0
        self.call_log = []

    def complete(self, messages, tools):
        raise RuntimeError("provider down")


def _cards(n):
    base = load_card(CASES_DIR / "v3_n01.yaml")
    return [dict(base, case_id=f"x{i}") for i in range(n)]


def test_after_three_sessions_in_a_row_ending_in_a_model_error_it_stops(tmp_path):
    from toy_agent.run_card import run_cards
    stopped = run_cards(_cards(5), _Failing, 1, tmp_path)
    assert stopped is True
    assert len(list(tmp_path.glob("*.json"))) == 3  # the three failed sessions are saved, no more are started


def test_a_good_session_resets_the_count_of_errors_in_a_row(tmp_path):
    from toy_agent.run_card import run_cards
    clients = iter([_Failing(), _Failing(), _Script(_say("Done.")), _Failing(), _Failing()])
    stopped = run_cards(_cards(5), lambda: next(clients), 1, tmp_path)
    assert stopped is False and len(list(tmp_path.glob("*.json"))) == 5


def test_the_session_file_records_the_conditions_it_was_asked_for(tmp_path):
    from toy_agent.run_card import run_cards
    cond = {"model": "m", "provider": "p", "reasoning_effort": "none", "request_timeout_s": 30.0, "max_turns": 8}
    run_cards(_cards(1), lambda: _Script(_say("Done.")), 1, tmp_path, cond)
    saved = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    assert saved["conditions"] == cond


def test_a_session_that_raises_is_saved_as_a_fault_the_mover_picks_up(tmp_path, monkeypatch):
    import toy_agent.run_card as rc
    from toy_agent.sposta_guasti import move_faults

    class _Client:
        retry_count = 0
        call_log = [{"generation_id": "g1"}]

    def _boom(card, client, **kw):
        raise ValueError("boom: a message that must not be saved")

    monkeypatch.setattr(rc, "run_card", _boom)
    stopped = rc.run_cards(_cards(1), _Client, 1, tmp_path)
    saved = json.loads((tmp_path / "x0_1.json").read_text(encoding="utf-8"))
    assert saved["transcript"]["stop_reason"] == "exception" and saved["error_class"] == "ValueError"
    assert saved["call_log"] == [{"generation_id": "g1"}] and "boom" not in json.dumps(saved)
    assert stopped is False
    assert move_faults(tmp_path, tmp_path / "guasto") == [("x0_1.json", "exception")] and not list(tmp_path.glob("*.json"))
    monkeypatch.undo()
