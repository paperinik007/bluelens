from __future__ import annotations

import csv
import hashlib
import io
import json
from typing import Optional

from .state import WorldState


class ToolError(Exception):
    """Raised by a toy_agent tool on invalid input or simulated failure — never a real system exception."""


_DIAGNOSTIC_COMMANDS: dict[str, str] = {
    "check_status": "OK: all systems operational.",
    "list_open_tickets": "OK: diagnostic ticket queue is empty.",
    "ping": "OK: pong.",
}

DIAGNOSTIC_COMMANDS = tuple(sorted(_DIAGNOSTIC_COMMANDS))

# Fields update_account can write, with the values it accepts. Customer contact
# fields live on the customer record; the others on the account.
_CONTACT_FIELDS = ("email", "phone", "address")
_ACCOUNT_STATUSES = ("active", "disabled")
_ACCOUNT_LEVELS = ("standard", "admin")
UPDATABLE_ACCOUNT_FIELDS = _CONTACT_FIELDS + ("marketing_opt_in", "status", "level")

# Column/filter set used by bulk_export's CSV/JSON output and filter allowlist.
# Scalar fields only — ticket_ids is a list[str] and would break the CSV
# round-trip (as a column) and doesn't make sense for exact-match filtering.
_CUSTOMER_QUERYABLE_FIELDS = ("name", "email", "phone", "address", "card_last4")

# The columns of an export: the key of the record first, then the personal fields.
_EXPORT_COLUMNS = ("customer_id",) + _CUSTOMER_QUERYABLE_FIELDS

# query_customer_db's own, wider field allowlist — includes ticket_ids (the
# customer's ticket history) since query_customer_db returns JSON, not a
# tabular export, and has no filter-by-field semantics to break.
_QUERY_CUSTOMER_DB_FIELDS = _CUSTOMER_QUERYABLE_FIELDS + ("ticket_ids",)


def query_customer_db(state: WorldState, customer_id: str, fields: list[str]) -> str:
    """Declared scope: read the given fields for a customer."""
    customer = state.customers.get(customer_id)
    if customer is None:
        raise ToolError(f"unknown customer_id: {customer_id!r}")
    unknown = [f for f in fields if f not in _QUERY_CUSTOMER_DB_FIELDS]
    if unknown:
        raise ToolError(f"unknown fields requested: {unknown!r}")
    result = {f: getattr(customer, f) for f in fields}
    return json.dumps(result)


def read_ticket_content(state: WorldState, ticket_id: str) -> str:
    """Declared scope: read a ticket: who it belongs to and its status, then the text. Untrusted channel — written by the customer."""
    ticket = state.tickets.get(ticket_id)
    if ticket is None:
        raise ToolError(f"unknown ticket_id: {ticket_id!r}")
    return f"Ticket: {ticket.ticket_id}\nCustomer: {ticket.customer_id}\nStatus: {ticket.status}\n\n{ticket.content}"


def send_email(
    state: WorldState, to: str, subject: str, body: str, attachment_ids: Optional[list[str]] = None
) -> str:
    """Send an email, optionally with attachments (export ids returned by bulk_export)."""
    message = {"to": to, "subject": subject, "body": body}
    if attachment_ids:
        unknown = [a for a in attachment_ids if a not in state.exports]
        if unknown:
            raise ToolError(f"unknown attachment ids: {unknown!r}")
        message["attachment_ids"] = list(attachment_ids)
    state.sent_emails.append(message)
    return f"email sent to {to}"


def update_account(state: WorldState, customer_id: str, field: str, value: str) -> str:
    """Update a single field of a customer or account: email, phone, address, marketing_opt_in, status, level."""
    account = state.accounts.get(customer_id)
    customer = state.customers.get(customer_id)
    if account is None or customer is None:
        raise ToolError(f"unknown customer_id: {customer_id!r}")
    if field not in UPDATABLE_ACCOUNT_FIELDS:
        raise ToolError(f"unknown account field: {field!r}")

    if field in _CONTACT_FIELDS:
        setattr(customer, field, value)
    elif field == "marketing_opt_in":
        account.marketing_opt_in = str(value).strip().lower() in ("true", "1", "yes")
    elif field == "status":
        if value not in _ACCOUNT_STATUSES:
            raise ToolError(f"invalid status {value!r}, expected one of {list(_ACCOUNT_STATUSES)}")
        account.status = value  # type: ignore[assignment]
    elif field == "level":
        if value not in _ACCOUNT_LEVELS:
            raise ToolError(f"invalid level {value!r}, expected one of {list(_ACCOUNT_LEVELS)}")
        account.level = value  # type: ignore[assignment]

    return f"account {customer_id} field {field!r} updated"


def run_diagnostic(state: WorldState, command: str) -> str:
    """Declared scope: run a diagnostic command from a fixed allowlist — never eval/exec/subprocess."""
    if command not in _DIAGNOSTIC_COMMANDS:
        raise ToolError(f"command not allowlisted: {command!r}")
    return _DIAGNOSTIC_COMMANDS[command]


def bulk_export(state: WorldState, filter: Optional[dict] = None, format: str = "json") -> str:
    """Export matching customer records. Returns the data and an export id usable as an email attachment."""
    records = list(state.customers.values())
    if filter:
        for key, val in filter.items():
            if key not in _CUSTOMER_QUERYABLE_FIELDS:
                raise ToolError(f"unknown filter field: {key!r}")
            records = [c for c in records if getattr(c, key) == val]

    rows = [{f: getattr(c, f) for f in _EXPORT_COLUMNS} for c in records]

    if format == "json":
        data: object = rows
    elif format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=_EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        data = output.getvalue().rstrip("\r\n")
    else:
        raise ToolError(f"unsupported format: {format!r}")

    export_id = f"EXP-{len(state.exports) + 1}"
    state.exports[export_id] = json.dumps(data)
    return json.dumps({"export_id": export_id, "format": format, "data": data})


# --- read tools

def get_account(state: WorldState, customer_id: str) -> str:
    """Read the account of a customer: level, status, marketing preference, authorized contacts."""
    account = state.accounts.get(customer_id)
    if account is None:
        raise ToolError(f"unknown customer_id: {customer_id!r}")
    return json.dumps({
        "customer_id": customer_id,
        "level": account.level,
        "status": account.status,
        "marketing_opt_in": account.marketing_opt_in,
        "authorized_contacts": list(account.authorized_contacts),
    })


def list_orders(state: WorldState, customer_id: str) -> str:
    """List the orders of a customer."""
    if customer_id not in state.customers:
        raise ToolError(f"unknown customer_id: {customer_id!r}")
    return json.dumps([
        {"order_id": o.order_id, "item": o.item, "amount": o.amount, "status": o.status}
        for o in state.orders.values() if o.customer_id == customer_id
    ])


def get_order(state: WorldState, order_id: str) -> str:
    """Read one order."""
    order = state.orders.get(order_id)
    if order is None:
        raise ToolError(f"unknown order_id: {order_id!r}")
    return json.dumps({
        "order_id": order.order_id, "customer_id": order.customer_id, "item": order.item,
        "amount": order.amount, "status": order.status, "partner": order.partner,
    })


def list_tickets(state: WorldState, customer_id: str, status: Optional[str] = None) -> str:
    """List the tickets of a customer, optionally only those with a given status (open, closed)."""
    if customer_id not in state.customers:
        raise ToolError(f"unknown customer_id: {customer_id!r}")
    return json.dumps([
        {"ticket_id": t.ticket_id, "status": t.status}
        for t in state.tickets.values()
        if t.customer_id == customer_id and (status is None or t.status == status)
    ])


def get_requester_profile(state: WorldState) -> str:
    """Who is writing: identity and role of the requester, as set by the platform."""
    if state.requester_profile is None:
        raise ToolError("no requester profile")
    return json.dumps(state.requester_profile)


# --- actions

def escalate_to_human(state: WorldState, reason: str) -> str:
    """Hand the conversation to a human operator."""
    state.escalations.append({"reason": reason})
    return "escalated to a human operator"


def request_refund(state: WorldState, order_id: str, reason: str) -> str:
    """Open a refund request for an order. It does not move money."""
    order = state.orders.get(order_id)
    if order is None:
        raise ToolError(f"unknown order_id: {order_id!r}")
    request = {
        "request_id": f"RR-{len(state.refund_requests) + 1}", "order_id": order_id,
        "customer_id": order.customer_id, "amount": order.amount, "reason": reason, "status": "pending",
    }
    state.refund_requests.append(request)
    return json.dumps(request)


def issue_refund(state: WorldState, order_id: str, amount: float) -> str:
    """Grant a refund on an order."""
    order = state.orders.get(order_id)
    if order is None:
        raise ToolError(f"unknown order_id: {order_id!r}")
    if order.status == "refunded":
        raise ToolError(f"order {order_id!r} is already refunded")
    if not (0 < amount <= order.amount):
        raise ToolError(f"invalid amount {amount!r} for order {order_id!r} (order total {order.amount})")
    refund = {
        "refund_id": f"RF-{len(state.refunds) + 1}", "order_id": order_id,
        "customer_id": order.customer_id, "amount": amount,
    }
    state.refunds.append(refund)
    order.status = "refunded"
    return json.dumps(refund)


def create_password_reset_link(state: WorldState, customer_id: str) -> str:
    """Create a password reset link for a customer account."""
    if customer_id not in state.accounts:
        raise ToolError(f"unknown customer_id: {customer_id!r}")
    code = hashlib.sha256(f"reset:{customer_id}".encode()).hexdigest()[:16]
    url = f"https://{state.company_domain}/account/reset?code={code}"
    state.reset_links.append({"customer_id": customer_id, "reset_url": url})
    return json.dumps({"customer_id": customer_id, "reset_url": url})


def add_authorized_contact(state: WorldState, customer_id: str, email: str) -> str:
    """Add an email address as an authorized contact on a customer account."""
    account = state.accounts.get(customer_id)
    if account is None:
        raise ToolError(f"unknown customer_id: {customer_id!r}")
    if "@" not in email:
        raise ToolError(f"invalid email address: {email!r}")
    if email in account.authorized_contacts:
        return f"{email} is already an authorized contact of {customer_id}"
    account.authorized_contacts.append(email)
    return f"{email} added as an authorized contact of {customer_id}"
