from toy_agent.state import fresh_state


def test_fresh_state_has_expected_seed_data():
    state = fresh_state()
    assert "cust_001" in state.customers
    assert state.accounts["cust_001"].level == "standard"
    assert state.accounts["cust_001"].status == "active"
    assert "tkt_001" in state.tickets


def test_fresh_state_calls_are_independent():
    state_a = fresh_state()
    state_b = fresh_state()
    state_a.customers["cust_001"].name = "MUTATED"
    assert state_b.customers["cust_001"].name != "MUTATED"


def test_mutating_one_fresh_state_never_leaks_into_later_calls():
    # Regression guard for a shared-singleton / mutable-default bug: mutate a
    # deeply nested object from one fresh_state() call, then verify a later
    # call is still built from the untouched snapshot.
    state_a = fresh_state()
    state_a.customers["cust_001"].ticket_ids.append("tkt_injected")
    state_a.accounts["cust_001"].level = "admin"
    state_a.accounts["cust_001"].refund_total = 999.0
    state_a.sent_emails.append({"to": "x", "subject": "x", "body": "x"})

    state_c = fresh_state()
    assert "tkt_injected" not in state_c.customers["cust_001"].ticket_ids
    assert state_c.accounts["cust_001"].level == "standard"
    assert state_c.accounts["cust_001"].refund_total == 0.0
    assert state_c.sent_emails == []
