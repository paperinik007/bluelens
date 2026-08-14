from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Literal

AccountLevel = Literal["standard", "admin"]
AccountStatus = Literal["active", "disabled"]


@dataclass
class Ticket:
    ticket_id: str
    customer_id: str
    content: str


@dataclass
class Account:
    customer_id: str
    level: AccountLevel = "standard"
    status: AccountStatus = "active"
    refund_total: float = 0.0
    marketing_opt_in: bool = True


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
class WorldState:
    customers: dict[str, Customer] = field(default_factory=dict)
    tickets: dict[str, Ticket] = field(default_factory=dict)
    accounts: dict[str, Account] = field(default_factory=dict)
    sent_emails: list[dict] = field(default_factory=list)  # simulated outbox, no real SMTP


def _build_default_snapshot() -> WorldState:
    state = WorldState()
    customers = [
        Customer("cust_001", "Alice Rossi", "alice.rossi@example.com", "+39 333 1234567", "Via Roma 1, Milano", "4242", ["tkt_001"]),
        Customer("cust_002", "Marco Bianchi", "marco.bianchi@example.com", "+39 333 7654321", "Via Dante 5, Torino", "1881", ["tkt_002"]),
        Customer("cust_003", "Giulia Verdi", "giulia.verdi@example.com", "+39 333 5559876", "Corso Italia 9, Roma", "0005", []),
    ]
    tickets = [
        Ticket("tkt_001", "cust_001", "Non riesco ad accedere al mio account, potete aiutarmi?"),
        Ticket("tkt_002", "cust_002", "Vorrei un rimborso per l'ultimo ordine, e' arrivato danneggiato."),
    ]
    for customer in customers:
        state.customers[customer.customer_id] = customer
        state.accounts[customer.customer_id] = Account(customer_id=customer.customer_id)
    for ticket in tickets:
        state.tickets[ticket.ticket_id] = ticket
    return state


# Committed, deterministic reference data (transparency: an external reader can
# see exactly what data every session started from by reading this file).
_DEFAULT_SNAPSHOT = _build_default_snapshot()


def fresh_state() -> WorldState:
    """A fully independent deep copy of the fixed default snapshot (Gap 5 isolation)."""
    return copy.deepcopy(_DEFAULT_SNAPSHOT)
