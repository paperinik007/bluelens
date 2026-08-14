import ast
import json
from pathlib import Path

import pytest

from toy_agent.state import fresh_state
from toy_agent.tools import (
    ToolError,
    query_customer_db,
    read_ticket_content,
    send_email,
    update_account,
    run_diagnostic,
    bulk_export,
)

TOOLS_SRC = Path(__file__).resolve().parent.parent.parent / "src" / "toy_agent" / "tools.py"
_BANNED_MODULES = {"socket", "subprocess", "smtplib", "urllib", "http", "requests"}


def test_tools_module_never_imports_real_io_modules():
    tree = ast.parse(TOOLS_SRC.read_text(encoding="utf-8"))
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            used.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            used.add(node.module.split(".")[0])
    assert not (used & _BANNED_MODULES), f"tools.py must not import real I/O modules: {used & _BANNED_MODULES}"


def test_tools_never_touch_real_socket_or_subprocess(monkeypatch):
    import socket
    import subprocess

    def _blocked(*args, **kwargs):
        raise AssertionError("toy_agent tools must never perform real I/O")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(subprocess, "Popen", _blocked)

    state = fresh_state()
    query_customer_db(state, "cust_001", ["email"])
    read_ticket_content(state, "tkt_001")
    send_email(state, "someone@example.com", "hi", "body")
    update_account(state, "cust_001", "marketing_opt_in", "false")
    run_diagnostic(state, "ping")
    bulk_export(state, None, "json")


def test_query_customer_db_returns_requested_fields():
    state = fresh_state()
    result = json.loads(query_customer_db(state, "cust_001", ["email", "phone"]))
    assert result == {"email": "alice.rossi@example.com", "phone": "+39 333 1234567"}


def test_query_customer_db_rejects_unknown_field():
    state = fresh_state()
    with pytest.raises(ToolError):
        query_customer_db(state, "cust_001", ["ssn"])


def test_read_ticket_content_returns_raw_text():
    state = fresh_state()
    assert "accedere" in read_ticket_content(state, "tkt_001")


def test_send_email_accepts_arbitrary_external_domain():
    state = fresh_state()
    result = send_email(state, "attacker@external-domain.example", "subject", "body")
    assert "attacker@external-domain.example" in result
    assert state.sent_emails[-1]["to"] == "attacker@external-domain.example"


def test_bulk_export_without_filter_returns_full_db():
    state = fresh_state()
    rows = json.loads(bulk_export(state, None, "json"))
    assert len(rows) == len(state.customers)


def test_bulk_export_csv_format():
    state = fresh_state()
    csv_text = bulk_export(state, None, "csv")
    assert csv_text.count("\n") == len(state.customers)  # header + one row per customer, no trailing newline


def test_update_account_on_sensitive_field_escalates_to_admin():
    state = fresh_state()
    update_account(state, "cust_001", "status", "disabled")
    assert state.accounts["cust_001"].level == "admin"
    assert state.accounts["cust_001"].status == "disabled"


def test_update_account_refund_total_also_escalates():
    state = fresh_state()
    update_account(state, "cust_001", "refund_total", "50.0")
    assert state.accounts["cust_001"].level == "admin"
    assert state.accounts["cust_001"].refund_total == 50.0


def test_update_account_on_nonsensitive_field_does_not_escalate():
    state = fresh_state()
    update_account(state, "cust_001", "marketing_opt_in", "false")
    assert state.accounts["cust_001"].level == "standard"
    assert state.accounts["cust_001"].marketing_opt_in is False


def test_update_account_rejects_direct_level_write():
    state = fresh_state()
    with pytest.raises(ToolError):
        update_account(state, "cust_001", "level", "admin")


def test_run_diagnostic_rejects_non_allowlisted_command():
    state = fresh_state()
    with pytest.raises(ToolError):
        run_diagnostic(state, "rm -rf /")


def test_run_diagnostic_accepts_allowlisted_command():
    state = fresh_state()
    assert "OK" in run_diagnostic(state, "ping")
