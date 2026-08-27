import asyncio

import pytest

pytest.importorskip("llamafirewall", reason="llamafirewall is only installed inside the detector-llamafirewall container")

from detector_adapter.vendors.llamafirewall.adapter import OpenRouterAlignmentCheck, TOOL_NAME
from detector_adapter.vendors.llamafirewall.evaluate_case import run_evaluate_case

_DATA = {
    "session_id": "c1",
    "turns": [
        {"seq": 0, "role": "user", "content": "Summarize the news.", "tool_call": None},
        {"seq": 1, "role": "assistant", "content": "Here is a summary.", "tool_call": None},
    ],
}


def test_evaluate_with_llm_records_the_fail_open_on_the_class_not_the_instance(monkeypatch):
    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")
    OpenRouterAlignmentCheck.fail_open_detected = False
    scanner = OpenRouterAlignmentCheck()

    async def _raise(*a, **kw):
        raise RuntimeError("boom")
    monkeypatch.setattr(scanner.llm, "call", _raise)

    response = asyncio.run(scanner._evaluate_with_llm("some text"))
    assert response.conclusion is True  # vendor's own default (_get_default_error_response), unchanged
    assert OpenRouterAlignmentCheck.fail_open_detected is True
    assert OpenRouterAlignmentCheck.fail_open_exception_class == "RuntimeError"


def test_a_fresh_scanner_instance_still_sees_the_class_level_flag(monkeypatch):
    # The exact bug this mechanism must survive: create_scanner() builds a
    # NEW scanner object per scan() call — a plain instance flag would be
    # unreadable from any code outside that ephemeral instance.
    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")
    OpenRouterAlignmentCheck.fail_open_detected = False
    first = OpenRouterAlignmentCheck()

    async def _raise(*a, **kw):
        raise RuntimeError("boom")
    monkeypatch.setattr(first.llm, "call", _raise)
    asyncio.run(first._evaluate_with_llm("text"))

    second = OpenRouterAlignmentCheck()  # a fresh instance, as create_scanner() would build
    assert second.fail_open_detected is True  # reads the class attribute, not its own


def test_run_evaluate_case_produces_an_error_verdict_never_a_label_on_fail_open(monkeypatch):
    from llamafirewall.utils.base_llm import LLMClient

    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")

    async def _raise(self, *a, **kw):
        raise RuntimeError("boom")
    monkeypatch.setattr(LLMClient, "call", _raise)
    OpenRouterAlignmentCheck.fail_open_detected = False

    verdict = run_evaluate_case(_DATA)
    assert verdict["status"] == "error"
    assert verdict["label"] is None
    assert "fail-open" in verdict["rationale"]
    assert verdict["tool_name"] == TOOL_NAME


def test_run_evaluate_case_reports_normally_when_the_llm_call_succeeds(monkeypatch):
    from llamafirewall.utils.base_llm import LLMClient
    from detector_adapter.vendors.llamafirewall.adapter import AlignmentCheckOutputSchema

    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")

    async def _ok(self, *a, **kw):
        return AlignmentCheckOutputSchema(observation="o", thought="t", conclusion=False)
    monkeypatch.setattr(LLMClient, "call", _ok)
    OpenRouterAlignmentCheck.fail_open_detected = False

    verdict = run_evaluate_case(_DATA)
    assert verdict["status"] == "ok"
    assert verdict["label"] == "benign"


def test_the_flag_is_reset_between_cases_a_prior_fail_open_does_not_leak(monkeypatch):
    from llamafirewall.utils.base_llm import LLMClient
    from detector_adapter.vendors.llamafirewall.adapter import AlignmentCheckOutputSchema

    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")
    OpenRouterAlignmentCheck.fail_open_detected = True  # simulates a fail-open left over from a previous case

    async def _ok(self, *a, **kw):
        return AlignmentCheckOutputSchema(observation="o", thought="t", conclusion=False)
    monkeypatch.setattr(LLMClient, "call", _ok)

    verdict = run_evaluate_case(_DATA)
    assert verdict["status"] == "ok"  # not contaminated by the stale flag
    assert verdict["label"] == "benign"
