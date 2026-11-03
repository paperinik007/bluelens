from __future__ import annotations

import os
from typing import Any

TOOL_NAME = "llamafirewall-alignmentcheck"


def scan_decision_to_verdict(case_id: str, scan_result: Any, latency_s: float | None = None) -> dict:
    """Normalize a llamafirewall ScanResult (duck-typed here — only attribute
    access, no isinstance check, so this stays testable without llamafirewall
    installed) into our Verdict JSON shape. Mirrors
    detector_adapter.vendors.aidr.adapter.detection_result_to_verdict.

    decision is compared by .value (a plain string on the real ScanDecision
    enum) rather than by importing ScanDecision — never needs llamafirewall
    importable to be called or tested.

    latency_s (I4, final review): wall-clock time of the actual scan call,
    measured by the caller (evaluate_case.py, around firewall.scan_replay())
    — this function only records it, since scan_result itself carries no
    timing information."""
    decision_value = getattr(scan_result.decision, "value", scan_result.decision)
    is_malicious = decision_value == "human_in_the_loop_required"
    return {
        "case_id": case_id,
        "tool_name": TOOL_NAME,
        "status": "ok",
        "label": "malicious" if is_malicious else "benign",
        "confidence": scan_result.score,
        "technique_detected": None,
        "rationale": scan_result.reason or None,
        "cost_usd": None,
        "latency_s": latency_s,
        "in_tokens": None,
        "out_tokens": None,
    }


def transcript_dict_to_trace(transcript: dict) -> list:
    """Build a llamafirewall Trace (list of Message) from a Transcript JSON
    dict (same wire format aidr's adapter consumes on stdin) — never
    deserializes a toy_agent.schema.Transcript instance (detector_adapter
    must never import toy_agent, Gap 9).

    Lazy import (function-local, not module-level): keeps this module
    importable without llamafirewall installed for anything that doesn't
    call this function — same pattern as _build_messages in
    detector_adapter/vendors/aidr/adapter.py."""
    from llamafirewall import AssistantMessage, ToolMessage, UserMessage

    messages: list = []
    for turn in transcript["turns"]:
        role = turn["role"]
        if role == "user":
            messages.append(UserMessage(content=turn["content"]))
        elif role == "assistant":
            messages.append(AssistantMessage(content=turn["content"]))
        elif role == "tool":
            call = turn["tool_call"]
            action_text = f"ACTION: {call['tool_name']}\nACTION INPUT: {call['arguments']}"
            messages.append(AssistantMessage(content=action_text))
            messages.append(ToolMessage(content=call.get("result") or ""))
        else:
            raise ValueError(f"unknown turn role: {role!r}")
    return messages


TOOL_NAME_COMBINED = "llamafirewall-combined"


def aggregate_promptguard_turns(pg_turn_results: list) -> tuple[str, float]:
    """Aggregate one ScanResult per scanned Role.USER turn into a single
    (decision_value, score) pair for the whole case — max/any, never
    scan_replay()'s own last-message-wins default (design doc, 'Architettura
    / Data flow', risk finding #2 post-council: scan_replay() would have
    silently reported whichever turn was scanned last, almost always an
    assistant/tool turn with no PromptGuard signal at all, since only
    Role.USER turns are ever scanned here). decision is compared by .value
    (a plain string) — same duck-typing convention as
    scan_decision_to_verdict, never requires llamafirewall importable."""
    decisions = [getattr(r.decision, "value", r.decision) for r in pg_turn_results]
    score = max((r.score for r in pg_turn_results), default=0.0)
    return ("block" if "block" in decisions else "allow"), score


def combine_scan_results_to_verdict(
    case_id: str,
    ac_result: Any,
    pg_decision_value: str,
    pg_score: float,
    pg_turn_results: list,
    ac_latency_s: float,
    pg_latency_s: float,
) -> dict:
    """Fuse one AlignmentCheck ScanResult and the aggregated PromptGuard
    decision/score (aggregate_promptguard_turns) into a single Verdict dict
    (design doc, 'Combinazione del Verdict'). OR on the label, max on the
    confidence — a fusion policy of this project's own, not inherited from
    any vendor arbitration (no cross-role arbitration exists in the vendor
    for two independently-registered scanners, verified in
    docs/research/2026-08-29-llamafirewall-promptguard-not-wired.md).
    technique_detected stays None unconditionally: PromptGuard is a binary
    classifier with no technique attribution by construction, regardless of
    which of the two scanners determined the label (skeptic finding,
    design doc)."""
    ac_decision_value = getattr(ac_result.decision, "value", ac_result.decision)
    is_malicious = ac_decision_value == "human_in_the_loop_required" or pg_decision_value == "block"
    pg_reason = max(pg_turn_results, key=lambda r: r.score).reason if pg_turn_results else "no user turn scanned"
    return {
        "case_id": case_id,
        "tool_name": TOOL_NAME_COMBINED,
        "status": "ok",
        "label": "malicious" if is_malicious else "benign",
        "confidence": max(ac_result.score, pg_score),
        "technique_detected": None,
        "rationale": f"AlignmentCheck: {ac_result.reason or 'n/a'} | PromptGuard: {pg_reason}",
        "cost_usd": None,
        "latency_s": ac_latency_s + pg_latency_s,
        "in_tokens": None,
        "out_tokens": None,
    }


def combined_error_verdict(case_id: str, source: str, exception_class: str | None) -> dict:
    """Verdict for either scan failing inside evaluate_case_combined.py — the
    whole case becomes status='error'/label=None regardless of which of the
    two scanners failed (never a Verdict based on the one that survived,
    design doc 'Gestione errori': that would silently inflate LlamaFirewall's
    measured coverage on a case where only half the product responded).
    `source` distinguishes a vendor fail-open (AlignmentCheck's remote LLM
    call) from a local dependency error (PromptGuard's torch/transformers
    stack) in the rationale text only — the Verdict shape is identical
    either way (skeptic finding, design doc 'Gestione errori')."""
    if source == "alignmentcheck":
        detail = f"vendor fail-open: {exception_class}" if exception_class else "vendor fail-open"
    elif source == "promptguard":
        detail = f"local dependency error: {exception_class}" if exception_class else "local dependency error"
    else:
        raise ValueError(f"unknown source: {source!r}")
    return {
        "case_id": case_id,
        "tool_name": TOOL_NAME_COMBINED,
        "status": "error",
        "label": None,
        "confidence": None,
        "technique_detected": None,
        "rationale": detail,
        "cost_usd": None,
        "latency_s": None,
        "in_tokens": None,
        "out_tokens": None,
    }


TOOL_NAME_PROMPTGUARD = "llamafirewall-promptguard"


def promptguard_inputs(transcript: dict) -> list[dict]:
    """The texts the vendor's default configuration has PromptGuard scan: the user's messages and the
    results of the tools (llamafirewall.py:90-96, pinned 1.0.3: Role.USER and Role.TOOL). The assistant's own
    messages and the arguments of its calls are not scanned, and an empty result carries nothing to scan."""
    inputs = []
    for turn in transcript["turns"]:
        if turn["role"] == "user":
            text, source, tool_name = turn["content"], "user", None
        elif turn["role"] == "tool":
            call = turn["tool_call"]
            text, source, tool_name = call.get("result") or "", "tool", call["tool_name"]
        else:
            continue
        if text:
            inputs.append({"turn": turn["seq"], "source": source, "tool_name": tool_name, "text": text})
    return inputs


def _where(item: dict) -> str:
    what = "the user message" if item["source"] == "user" else f"the result of {item['tool_name']}"
    return f"{what} (turn {item['turn']})"


def promptguard_verdict(case_id: str, scans: list, latency_s: float | None) -> dict:
    """One verdict for a whole session from the scan of each input (item, ScanResult): malicious if any input
    reaches the vendor's threshold, confidence the highest score. `inputs_scanned` keeps every score (no text)
    so the input that fired can be found afterwards."""
    decisions = [getattr(r.decision, "value", r.decision) for _, r in scans]
    is_malicious = "block" in decisions
    best_item, best = max(scans, key=lambda pair: pair[1].score) if scans else (None, None)
    if not scans:
        rationale = "PromptGuard: no input to scan"
    elif is_malicious:
        fired = sum(d == "block" for d in decisions)
        rationale = (f"PromptGuard: block (score {best.score:.2f}) on {_where(best_item)}; "
                     f"{fired} of {len(scans)} inputs over the threshold")
    else:
        rationale = (f"PromptGuard: allow (highest score {best.score:.2f}, on {_where(best_item)}); "
                     f"{len(scans)} inputs scanned")
    return {
        "case_id": case_id,
        "tool_name": TOOL_NAME_PROMPTGUARD,
        "status": "ok",
        "label": "malicious" if is_malicious else "benign",
        "confidence": best.score if scans else 0.0,
        "technique_detected": None,
        "rationale": rationale,
        "cost_usd": None,
        "latency_s": latency_s,
        "in_tokens": None,
        "out_tokens": None,
        "inputs_scanned": [
            {"turn": item["turn"], "source": item["source"], "tool_name": item["tool_name"],
             "decision": getattr(r.decision, "value", r.decision), "score": r.score}
            for item, r in scans
        ],
    }


def promptguard_error_verdict(case_id: str, exception_class: str | None) -> dict:
    """The local classifier failed (model files, torch): status='error', label=None, excluded from the counts."""
    detail = f"local dependency error: {exception_class}" if exception_class else "local dependency error"
    return {
        "case_id": case_id,
        "tool_name": TOOL_NAME_PROMPTGUARD,
        "status": "error",
        "label": None,
        "confidence": None,
        "technique_detected": None,
        "rationale": f"PromptGuard: {detail}",
        "cost_usd": None,
        "latency_s": None,
        "in_tokens": None,
        "out_tokens": None,
    }


def alignmentcheck_steps(transcript: dict) -> list[dict]:
    """The session as the vendor's trace: the user's messages, each tool call as an action of the assistant
    ("ACTION: ... ACTION INPUT: ...", the format its prompt describes) followed by the tool's result, and the
    assistant's own messages. `turn` is the session's turn number, `kind` what the step is. Plain data: the
    caller turns each step into the vendor's message class."""
    steps = []
    for turn in transcript["turns"]:
        role, seq = turn["role"], turn["seq"]
        if role == "user":
            steps.append({"turn": seq, "role": "user", "kind": "user", "tool_name": None, "content": turn["content"]})
        elif role == "assistant":
            steps.append({"turn": seq, "role": "assistant", "kind": "reply", "tool_name": None, "content": turn["content"]})
        elif role == "tool":
            call = turn["tool_call"]
            name = call["tool_name"]
            action = f"ACTION: {name}\nACTION INPUT: {call['arguments']}"
            steps.append({"turn": seq, "role": "assistant", "kind": "action", "tool_name": name, "content": action})
            steps.append({"turn": seq, "role": "tool", "kind": "result", "tool_name": name, "content": call.get("result") or ""})
        else:
            raise ValueError(f"unknown turn role: {role!r}")
    return steps


def _what(step: dict) -> str:
    what = f"the call to {step['tool_name']}" if step["kind"] == "action" else "the assistant's reply"
    return f"{what} (turn {step['turn']})"


def alignmentcheck_verdict(case_id: str, scans: list, latency_s: float | None) -> dict:
    """One verdict for a whole session from the judgement of each action of the assistant (step, ScanResult), in
    order, up to the first one judged misaligned (the vendor's replay stops there). Malicious if any action was
    judged misaligned; confidence the highest score. `actions_scanned` keeps the outcome of each action (no text)
    so the one that fired can be found afterwards."""
    decisions = [getattr(r.decision, "value", r.decision) for _, r in scans]
    is_malicious = "human_in_the_loop_required" in decisions
    fired = next(((s, r) for (s, r), d in zip(scans, decisions) if d == "human_in_the_loop_required"), None)
    if fired:
        step, result = fired
        rationale = f"AlignmentCheck: misaligned on {_what(step)}. {result.reason}"
    elif scans:
        rationale = f"AlignmentCheck: no action judged misaligned; {len(scans)} actions scanned"
    else:
        rationale = "AlignmentCheck: no action to scan"
    return {
        "case_id": case_id,
        "tool_name": TOOL_NAME,
        "status": "ok",
        "label": "malicious" if is_malicious else "benign",
        "confidence": max((r.score for _, r in scans), default=0.0),
        "technique_detected": None,
        "rationale": rationale,
        "cost_usd": None,
        "latency_s": latency_s,
        "in_tokens": None,
        "out_tokens": None,
        "actions_scanned": [
            {"turn": s["turn"], "kind": s["kind"], "tool_name": s["tool_name"],
             "decision": getattr(r.decision, "value", r.decision), "score": r.score}
            for s, r in scans
        ],
    }


try:
    from llamafirewall import register_llamafirewall_scanner
    from llamafirewall.scanners.custom_check_scanner import CustomCheckScanner
    from llamafirewall.scanners.experimental.alignmentcheck_scanner import (
        AlignmentCheckOutputSchema,
        AlignmentCheckScanner,
        SYSTEM_PROMPT,
    )
except ImportError:
    OpenRouterAlignmentCheck = None  # llamafirewall not installed on this host
else:
    # Verified live (Step 0, deferred in this run — see above) at
    # implementation time, not only at pre-design falsification — a
    # third-party model catalog ages (Gap 10, same lesson already applied to
    # aidr's SIFTER_MODEL/INSPECTOR_MODEL).
    # The vendor's own model (custom_check_scanner.py, 1.0.3: Llama-4-Maverick-17B-128E-Instruct-FP8); on
    # OpenRouter the only Maverick, served in fp8 only by Parasail (listing of 2026-10-26; plan part 7).
    DEFAULT_MODEL = "meta-llama/llama-4-maverick"
    API_BASE_URL = "http://127.0.0.1:8200/v1"  # local proxy (a later task), single port — no tier remap needed
    API_KEY_ENV_VAR = "LLAMAFIREWALL_OPENROUTER_API_KEY"

    @register_llamafirewall_scanner(TOOL_NAME)
    class OpenRouterAlignmentCheck(AlignmentCheckScanner):
        """AlignmentCheckScanner pointed at OpenRouter via our local proxy,
        instead of Together — bypasses AlignmentCheckScanner.__init__
        (hardcodes Together's api_base_url/api_key_env_var) by calling
        CustomCheckScanner.__init__ directly. Zero-argument constructor:
        llamafirewall.llamafirewall.create_scanner() instantiates a
        registered custom scanner with scanner_class() — no arguments."""

        fail_open_detected: bool = False
        fail_open_exception_class: str | None = None

        def __init__(self, model_name: str | None = None) -> None:
            model = model_name or os.environ.get("LLAMAFIREWALL_MODEL") or DEFAULT_MODEL
            CustomCheckScanner.__init__(
                self,
                scanner_name=TOOL_NAME,
                system_prompt=SYSTEM_PROMPT,
                output_schema=AlignmentCheckOutputSchema,
                model_name=model,
                api_base_url=API_BASE_URL,
                api_key_env_var=API_KEY_ENV_VAR,
            )
            self.require_full_trace = True

        async def _evaluate_with_llm(self, text: str) -> AlignmentCheckOutputSchema:
            """Overrides CustomCheckScanner._evaluate_with_llm (verified on
            llamafirewall/scanners/custom_check_scanner.py:68-80) to record a
            vendor fail-open before its own default silently substitutes
            conclusion=True — same interception point the vendor's own test
            suite patches. The class attribute (not self) is what
            create_scanner()'s caller can actually read afterward."""
            try:
                return await self.llm.call(
                    prompt=text, system_prompt=self.system_prompt,
                    output_schema=self.output_schema, temperature=self.temperature,
                )
            except Exception as exc:
                cls = type(self)
                cls.fail_open_detected = True
                cls.fail_open_exception_class = exc.__class__.__name__
                return self._get_default_error_response()


def fail_open_verdict(case_id: str, exception_class: str | None) -> dict:
    """Verdict for a vendor fail-open (the LLM call inside
    _evaluate_with_llm raised, and AlignmentCheckScanner's own default
    silently substituted conclusion=True) — status='error'/label=None so
    metrics.py excludes it from TP/FP/FN/TN via the existing error_count
    bucket."""
    detail = f"vendor fail-open: {exception_class}" if exception_class else "vendor fail-open"
    return {
        "case_id": case_id,
        "tool_name": TOOL_NAME,
        "status": "error",
        "label": None,
        "confidence": None,
        "technique_detected": None,
        "rationale": detail,
        "cost_usd": None,
        "latency_s": None,
        "in_tokens": None,
        "out_tokens": None,
    }
