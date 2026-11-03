from __future__ import annotations

import argparse
import json
import os
import uuid
from pathlib import Path

from .agent_loop import build_tool_registry, run_agent
from .case_card import load_card, prepare_session
from .run_case import transcript_to_dict
from .state import WorldState


def _state_after(state: WorldState) -> dict:
    """What the session changed in the world. Read by the automatic reading, never shown to a judge."""
    return {
        "sent_emails": state.sent_emails,
        "refunds": state.refunds,
        "refund_requests": state.refund_requests,
        "reset_links": state.reset_links,
        "escalations": state.escalations,
        "exports": sorted(state.exports),
        "integration_egress": state.integration_egress,
        "accounts": {
            cid: {
                "level": a.level, "status": a.status, "marketing_opt_in": a.marketing_opt_in,
                "authorized_contacts": list(a.authorized_contacts), "crm_id": a.crm_id,
            }
            for cid, a in state.accounts.items()
        },
        "customers": {
            cid: {"email": c.email, "phone": c.phone, "address": c.address} for cid, c in state.customers.items()
        },
    }


def run_card(card: dict, model_client, max_turns: int = 8) -> dict:
    """One session of one case card. The transcript carries an opaque session id, never the case id."""
    session = prepare_session(card)
    transcript = run_agent(
        scenario=session.scenario,
        tools=build_tool_registry(third_party_version=session.third_party_version),
        state=session.state,
        model_client=model_client,
        session_id=uuid.uuid4().hex,
        max_turns=max_turns,
        read_requester_profile=True,
    )
    return {
        "case_id": session.case_id,
        "third_party_version": session.third_party_version,
        "transcript": transcript_to_dict(transcript),
        "state_after": _state_after(session.state),
    }


def main() -> None:
    from .model_client import OpenRouterModelClient

    parser = argparse.ArgumentParser(description="Run sessions of case cards with the agent only (no judges).")
    parser.add_argument("cards", nargs="+", type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning-effort", default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--sessions", type=int, default=1)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("AGENT_OPENROUTER_API_KEY")
    args.out.mkdir(parents=True, exist_ok=True)
    for path in args.cards:
        card = load_card(path)
        for n in range(1, args.sessions + 1):
            target = args.out / f"{card['case_id']}_{n}.json"
            if target.exists():
                continue  # a saved session is never redone
            client = OpenRouterModelClient(
                model=args.model, api_key=key, reasoning_effort=args.reasoning_effort,
                provider=args.provider, request_timeout_s=args.timeout,
            )
            try:
                record = run_card(card, client)
            except Exception as exc:  # class name only: the message may carry the key
                print(f"FAILED {target.name}: {exc.__class__.__name__}", flush=True)
                continue
            record["call_log"] = client.call_log
            target.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
            print(target, flush=True)


if __name__ == "__main__":
    main()
