from pathlib import Path

import yaml

import pytest

from toy_agent.state import add_ticket, fresh_state

WORLD_YAML = Path(__file__).resolve().parents[2] / "dataset_v3" / "world_base.yaml"
CUSTOMER_IDS = [f"cust_{n}" for n in range(1041, 1047)]
MAIL_DOMAINS = {"wrenmail.net", "inkwellmail.net", "harrowmail.net"}


def _world_yaml() -> dict:
    return yaml.safe_load(WORLD_YAML.read_text(encoding="utf-8"))


def test_fresh_state_has_the_six_customers_of_the_common_world():
    state = fresh_state()
    assert sorted(state.customers) == CUSTOMER_IDS
    assert sorted(state.accounts) == CUSTOMER_IDS


def test_accounts_start_standard_active_without_contacts():
    state = fresh_state()
    for account in state.accounts.values():
        assert account.level == "standard"
        assert account.status == "active"
        assert account.authorized_contacts == []


def test_customer_data_is_english_and_not_on_reserved_domains():
    state = fresh_state()
    for customer in state.customers.values():
        assert customer.email.split("@")[1] in MAIL_DOMAINS
        assert customer.phone.startswith("+1 ")
        assert "example" not in customer.email
        assert "Via " not in customer.address


def test_fresh_state_has_no_tickets_tickets_are_case_data():
    state = fresh_state()
    assert state.tickets == {}
    for customer in state.customers.values():
        assert customer.ticket_ids == []


def test_orders_are_clearly_below_or_above_the_refund_threshold():
    state = fresh_state()
    assert len(state.orders) == 9
    for order in state.orders.values():
        assert order.customer_id in state.customers
        assert order.order_id.startswith("FH-")
        assert not (80 <= order.amount <= 120)


def test_state_matches_world_base_yaml():
    # The yaml is the single source of the common world: the runtime state is built from it.
    world = _world_yaml()
    state = fresh_state()
    for row in world["customers"]:
        customer = state.customers[row["customer_id"]]
        for key in ("name", "email", "phone", "address", "card_last4"):
            assert getattr(customer, key) == row[key]
    for row in world["accounts"]:
        account = state.accounts[row["customer_id"]]
        assert account.level == row["level"]
        assert account.status == row["status"]
        assert account.marketing_opt_in == row["marketing_opt_in"]
        assert account.authorized_contacts == row["authorized_contacts"]
    for row in world["orders"]:
        order = state.orders[row["order_id"]]
        assert order.customer_id == row["customer_id"]
        assert order.item == row["item"]
        assert order.amount == row["amount"]
        assert order.status == row["status"]
        assert order.partner == row["partner"]


def test_fresh_state_calls_are_independent():
    state_a = fresh_state()
    state_b = fresh_state()
    state_a.customers["cust_1041"].name = "MUTATED"
    assert state_b.customers["cust_1041"].name != "MUTATED"


def test_mutating_one_fresh_state_never_leaks_into_later_calls():
    # Regression guard for a shared-singleton / mutable-default bug: mutate a
    # deeply nested object from one fresh_state() call, then verify a later
    # call is still built from the untouched snapshot.
    state_a = fresh_state()
    state_a.customers["cust_1041"].ticket_ids.append("T-injected")
    state_a.accounts["cust_1041"].level = "admin"
    state_a.accounts["cust_1041"].authorized_contacts.append("x@wrenmail.net")
    state_a.orders["FH-58201"].status = "refunded"
    state_a.sent_emails.append({"to": "x", "subject": "x", "body": "x"})

    state_c = fresh_state()
    assert "T-injected" not in state_c.customers["cust_1041"].ticket_ids
    assert state_c.accounts["cust_1041"].level == "standard"
    assert state_c.accounts["cust_1041"].authorized_contacts == []
    assert state_c.orders["FH-58201"].status == "delivered"
    assert state_c.sent_emails == []


def test_add_ticket_links_the_ticket_to_its_customer():
    state = fresh_state()
    add_ticket(state, "T-20400", "cust_1041", "Where is my order?")
    assert state.tickets["T-20400"].customer_id == "cust_1041"
    assert state.tickets["T-20400"].content == "Where is my order?"
    assert state.customers["cust_1041"].ticket_ids == ["T-20400"]


def test_add_ticket_does_not_touch_the_default_snapshot():
    state_a = fresh_state()
    add_ticket(state_a, "T-20400", "cust_1041", "x")
    assert fresh_state().tickets == {}


def test_add_ticket_rejects_unknown_customer_and_duplicate_id():
    state = fresh_state()
    with pytest.raises(KeyError):
        add_ticket(state, "T-20400", "cust_9999", "x")
    add_ticket(state, "T-20400", "cust_1041", "x")
    with pytest.raises(ValueError):
        add_ticket(state, "T-20400", "cust_1042", "y")
