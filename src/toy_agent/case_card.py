from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .state import WORLD_BASE_PATH, Order, WorldState, add_order, add_ticket, fresh_state

# The case card is defined in docs/design/2026-10-14-tabella-permessi-bozza.md
# (section "Scheda del caso" and "Campi aggiunti"); a field not written there does not exist.

_INTENTS = ("malicious", "benign")
_WHERE = ("request", "content", "tool", "agent", "none")
_FORMS = ("disguised_injection", "override", "pretext", "explicit", "none")
_THIRD_PARTY_VERSIONS = ("honest", "compromised_data", "compromised_permissions", "compromised_persistence")
_ATTACK_LOCATION_KINDS = ("ticket", "order", "tool", "request", "none")

_REQUIRED = (
    "case_id", "intent", "where", "form", "actions", "text_only", "cell",
    "seed_turn", "requester_profile", "request_scope", "world_data", "attack_location",
)

_PROFILE_FIELDS = {
    "customer": ("customer_id", "registered_email"),
    "employee": ("name", "department", "refund_threshold"),
    "partner": ("partner_name", "partner_domains"),
}


class CardError(ValueError):
    """A case card that cannot be turned into a session. The message names fields, never case text."""


@dataclass
class PreparedSession:
    case_id: str
    scenario: str
    state: WorldState
    third_party_version: str
    card: dict


def _world() -> dict:
    return yaml.safe_load(WORLD_BASE_PATH.read_text(encoding="utf-8"))


def world_base() -> dict:
    """The common world file, as data (company domains, partner, employee)."""
    return _world()


def _check_closed(card: dict, field: str, allowed: tuple[str, ...]) -> None:
    if card[field] not in allowed:
        raise CardError(f"{field}: {card[field]!r} is not one of {list(allowed)}")


def _validate_profile(profile: dict) -> None:
    role = profile.get("role")
    if role not in _PROFILE_FIELDS:
        raise CardError(f"requester_profile.role: {role!r} is not one of {list(_PROFILE_FIELDS)}")
    missing = [f for f in _PROFILE_FIELDS[role] if f not in profile]
    if missing:
        raise CardError(f"requester_profile ({role}): missing {missing}")

    world = _world()
    if role == "customer":
        customer = next((c for c in world["customers"] if c["customer_id"] == profile["customer_id"]), None)
        if customer is None:
            raise CardError(f"requester_profile.customer_id: {profile['customer_id']!r} is not in the common world")
        if profile["registered_email"] != customer["email"]:
            raise CardError(f"requester_profile.registered_email: differs from the record of {profile['customer_id']}")
    elif role == "employee":
        for f in _PROFILE_FIELDS["employee"]:
            if profile[f] != world["employee"][f]:
                raise CardError(f"requester_profile.{f}: differs from the common world")
    else:
        if profile["partner_name"] != world["partner"]["name"]:
            raise CardError("requester_profile.partner_name: differs from the common world")
        if not set(profile["partner_domains"]) <= set(world["partner"]["domains"]):
            raise CardError("requester_profile.partner_domains: not a subset of the common world's")


def validate_card(card: dict) -> None:
    missing = [f for f in _REQUIRED if f not in card]
    if missing:
        raise CardError(f"missing fields: {missing}")
    if not card["text_only"] and "own_steps" not in card:
        raise CardError("own_steps: required unless text_only")

    if "slot" not in card["cell"]:
        raise CardError("cell.slot: required (the cell of scheme C the case fills)")
    _check_closed(card, "intent", _INTENTS)
    _check_closed(card, "where", _WHERE)
    _check_closed(card, "form", _FORMS)
    _validate_profile(card["requester_profile"])

    world_data = card["world_data"]
    version = world_data.get("third_party_version")
    if version not in _THIRD_PARTY_VERSIONS:
        raise CardError(f"world_data.third_party_version: {version!r} is not one of {list(_THIRD_PARTY_VERSIONS)}")

    if (card["where"] == "tool") != (version != "honest"):
        raise CardError("world_data.third_party_version: compromised only in the cases where the attack is in the tool")

    location = card["attack_location"]
    kind = location.get("kind")
    if kind not in _ATTACK_LOCATION_KINDS:
        raise CardError(f"attack_location.kind: {kind!r} is not one of {list(_ATTACK_LOCATION_KINDS)}")
    if kind == "ticket":
        ticket_ids = [t["ticket_id"] for t in world_data.get("tickets") or []]
        if location.get("ticket_id") not in ticket_ids:
            raise CardError(f"attack_location.ticket_id: {location.get('ticket_id')!r} is not a ticket of the case")
    if kind == "tool" and location.get("tool_name") != "crm_sync_contact":
        raise CardError("attack_location.tool_name: must be crm_sync_contact")
    if kind == "order":
        order_ids = [o["order_id"] for o in world_data.get("orders") or []]
        if location.get("order_id") not in order_ids:
            raise CardError(f"attack_location.order_id: {location.get('order_id')!r} is not an order of the case")


def load_card(path: Path | str) -> dict:
    path = Path(path)
    card = yaml.safe_load(path.read_text(encoding="utf-8"))
    try:
        validate_card(card)
    except CardError as exc:
        raise CardError(f"{path.name}: {exc}") from None
    return card


def read_path(state: WorldState, path: str) -> Any:
    """Value at an addressable path of the prepared world, e.g. `account.cust_1042.status`."""
    parts = path.split(".")
    try:
        if parts[0] == "requester_profile" and len(parts) == 2:
            return state.requester_profile[parts[1]]
        tables = {"account": state.accounts, "customer": state.customers, "order": state.orders, "ticket": state.tickets}
        if parts[0] in tables and len(parts) == 3:
            return getattr(tables[parts[0]][parts[1]], parts[2])
    except (KeyError, AttributeError, TypeError):
        pass
    raise CardError(f"path {path!r} does not exist in the world of the case")


def _check_pretext_facts(card: dict, state: WorldState) -> None:
    pretext = card.get("pretext") or {}
    for field in ("refuted_by", "false_fact_refuted_by"):
        for expression in pretext.get(field) or []:
            path, sep, raw = str(expression).partition(" == ")
            try:
                expected = json.loads(raw) if sep else None
            except json.JSONDecodeError:
                expected = None
            if not sep or expected is None and raw.strip() != "null":
                raise CardError(f"pretext.{field}: {expression!r} is not of the form '<path> == <json value>'")
            if read_path(state, path) != expected:
                raise CardError(f"pretext.{field}: {path} is not {raw} in the world of the case")


def prepare_session(card: dict) -> PreparedSession:
    """One session's starting state: the common world, the case's own data, and the requester profile."""
    validate_card(card)
    state = fresh_state()
    world_data = card["world_data"]
    try:
        for t in world_data.get("tickets") or []:
            add_ticket(state, t["ticket_id"], t["customer_id"], t["content"], t.get("status", "open"))
        for o in world_data.get("orders") or []:
            add_order(state, Order(
                order_id=o["order_id"], customer_id=o["customer_id"], item=o["item"],
                amount=o["amount"], status=o["status"], partner=o["partner"],
            ))
    except (KeyError, ValueError) as exc:
        raise CardError(f"{card['case_id']}: world_data: {exc.args[0]}") from None
    state.requester_profile = dict(card["requester_profile"])
    _check_pretext_facts(card, state)
    return PreparedSession(
        case_id=card["case_id"], scenario=card["seed_turn"], state=state,
        third_party_version=world_data["third_party_version"], card=card,
    )
