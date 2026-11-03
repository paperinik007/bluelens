from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

AccountLevel = Literal["standard", "admin"]
AccountStatus = Literal["active", "disabled"]

# The common world of every v3 session. Design: docs/design/2026-10-19-mondo-base.md.
# Cases add their own data (tickets, orders) on top; this file is not changed for a case.
WORLD_BASE_PATH = Path(__file__).resolve().parents[2] / "dataset_v3" / "world_base.yaml"


@dataclass
class Ticket:
    ticket_id: str
    customer_id: str
    content: str
    status: str = "open"


@dataclass
class Account:
    customer_id: str
    level: AccountLevel = "standard"
    status: AccountStatus = "active"
    marketing_opt_in: bool = True
    authorized_contacts: list[str] = field(default_factory=list)
    crm_id: str = ""


@dataclass
class Customer:
    customer_id: str
    name: str
    email: str
    phone: str
    address: str
    card_last4: str
    ticket_ids: list[str] = field(default_factory=list)


@dataclass
class Order:
    order_id: str
    customer_id: str
    item: str
    amount: float
    status: str
    partner: str


@dataclass
class WorldState:
    customers: dict[str, Customer] = field(default_factory=dict)
    tickets: dict[str, Ticket] = field(default_factory=dict)
    accounts: dict[str, Account] = field(default_factory=dict)
    orders: dict[str, Order] = field(default_factory=dict)
    sent_emails: list[dict] = field(default_factory=list)  # simulated outbox, no real SMTP
    company_domain: str = ""
    requester_profile: dict | None = None  # set by the platform before the agent starts
    exports: dict[str, str] = field(default_factory=dict)  # export_id -> exported data
    refund_requests: list[dict] = field(default_factory=list)
    refunds: list[dict] = field(default_factory=list)
    reset_links: list[dict] = field(default_factory=list)
    escalations: list[dict] = field(default_factory=list)
    integration_egress: list[dict] = field(default_factory=list)  # what the CRM integration sent out


def _build_default_snapshot(path: Path = WORLD_BASE_PATH) -> WorldState:
    world = yaml.safe_load(path.read_text(encoding="utf-8"))
    state = WorldState(company_domain=world["company"]["internal_domains"][0])
    for row in world["customers"]:
        state.customers[row["customer_id"]] = Customer(
            customer_id=row["customer_id"],
            name=row["name"],
            email=row["email"],
            phone=row["phone"],
            address=row["address"],
            card_last4=row["card_last4"],
        )
    for row in world["accounts"]:
        state.accounts[row["customer_id"]] = Account(
            customer_id=row["customer_id"],
            level=row["level"],
            status=row["status"],
            marketing_opt_in=row["marketing_opt_in"],
            authorized_contacts=list(row["authorized_contacts"]),
        )
    for row in world["orders"]:
        state.orders[row["order_id"]] = Order(
            order_id=row["order_id"],
            customer_id=row["customer_id"],
            item=row["item"],
            amount=row["amount"],
            status=row["status"],
            partner=row["partner"],
        )
    for ticket in world.get("tickets") or []:
        state.tickets[ticket["ticket_id"]] = Ticket(
            ticket_id=ticket["ticket_id"], customer_id=ticket["customer_id"], content=ticket["content"]
        )
        state.customers[ticket["customer_id"]].ticket_ids.append(ticket["ticket_id"])
    return state


# Committed, deterministic reference data (transparency: an external reader can
# see exactly what data every session started from by reading world_base.yaml).
_DEFAULT_SNAPSHOT = _build_default_snapshot()


def fresh_state() -> WorldState:
    """A fully independent deep copy of the fixed default snapshot (Gap 5 isolation)."""
    return copy.deepcopy(_DEFAULT_SNAPSHOT)


def add_order(state: WorldState, order: Order) -> None:
    """Add a case's own order to one session's state (a common-world order is never redefined)."""
    if order.customer_id not in state.customers:
        raise KeyError(f"unknown customer_id: {order.customer_id!r}")
    if order.order_id in state.orders:
        raise ValueError(f"duplicate order_id: {order.order_id!r}")
    state.orders[order.order_id] = order


def add_ticket(state: WorldState, ticket_id: str, customer_id: str, content: str, status: str = "open") -> None:
    """Add a case's ticket to one session's state (tickets are case data, not common world)."""
    if customer_id not in state.customers:
        raise KeyError(f"unknown customer_id: {customer_id!r}")
    if ticket_id in state.tickets:
        raise ValueError(f"duplicate ticket_id: {ticket_id!r}")
    state.tickets[ticket_id] = Ticket(ticket_id=ticket_id, customer_id=customer_id, content=content, status=status)
    state.customers[customer_id].ticket_ids.append(ticket_id)
