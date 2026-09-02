import json

import pytest

pytest.importorskip("llamafirewall", reason="llamafirewall is only installed inside the detector-llamafirewall container")

from llamafirewall import ScanDecision, ScanResult, ScanStatus

from detector_adapter.vendors.llamafirewall import evaluate_case_combined
from detector_adapter.vendors.llamafirewall.adapter import AlignmentCheckOutputSchema, OpenRouterAlignmentCheck

_DATA = {
    "session_id": "c1",
    "turns": [
        {"seq": 0, "role": "user", "content": "Summarize the news.", "tool_call": None},
        {"seq": 1, "role": "assistant", "content": "Here is a summary.", "tool_call": None},
    ],
}


def test_reports_ok_with_promptguard_running_for_real(monkeypatch):
    # AlignmentCheck's remote LLM call is mocked (no real OpenRouter call in
    # tests, same convention as the existing failopen/construction gated
    # tests); PromptGuard runs for real against the baked model — this is
    # the one test in this suite whose unique purpose is exercising the
    # real PromptGuardScanner/model (design doc, 'Test — cosa e perché',
    # item 4).
    from llamafirewall.utils.base_llm import LLMClient

    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")

    async def _ac_ok(self, *a, **kw):
        return AlignmentCheckOutputSchema(observation="o", thought="t", conclusion=False)
    monkeypatch.setattr(LLMClient, "call", _ac_ok)
    OpenRouterAlignmentCheck.fail_open_detected = False

    verdict = evaluate_case_combined.run_evaluate_case_combined(_DATA)
    assert verdict["status"] == "ok"
    assert verdict["technique_detected"] is None
    assert verdict["latency_s"] > 0
    assert "AlignmentCheck:" in verdict["rationale"] and "PromptGuard:" in verdict["rationale"]


def test_reports_error_when_alignmentcheck_fail_opens(monkeypatch):
    from llamafirewall.utils.base_llm import LLMClient

    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")

    async def _raise(self, *a, **kw):
        raise RuntimeError("boom")
    monkeypatch.setattr(LLMClient, "call", _raise)
    OpenRouterAlignmentCheck.fail_open_detected = False

    verdict = evaluate_case_combined.run_evaluate_case_combined(_DATA)
    assert verdict["status"] == "error"
    assert verdict["label"] is None
    assert "vendor fail-open" in verdict["rationale"]


def test_reports_error_when_promptguard_raises(monkeypatch):
    from llamafirewall.utils.base_llm import LLMClient

    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")

    async def _ac_ok(self, *a, **kw):
        return AlignmentCheckOutputSchema(observation="o", thought="t", conclusion=False)
    monkeypatch.setattr(LLMClient, "call", _ac_ok)
    OpenRouterAlignmentCheck.fail_open_detected = False

    async def _pg_raise(self, message, past_trace=None):
        raise RuntimeError("torch OOM")
    monkeypatch.setattr("llamafirewall.scanners.prompt_guard_scanner.PromptGuardScanner.scan", _pg_raise)

    verdict = evaluate_case_combined.run_evaluate_case_combined(_DATA)
    assert verdict["status"] == "error"
    assert verdict["label"] is None
    assert "local dependency error: RuntimeError" in verdict["rationale"]


def test_writes_a_secondary_log_line_per_user_turn_scanned(monkeypatch, tmp_path):
    from llamafirewall.utils.base_llm import LLMClient

    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")
    log_path = tmp_path / "pg_raw.jsonl"
    monkeypatch.setattr(evaluate_case_combined, "SECONDARY_LOG_PATH", str(log_path))

    async def _ac_ok(self, *a, **kw):
        return AlignmentCheckOutputSchema(observation="o", thought="t", conclusion=False)
    monkeypatch.setattr(LLMClient, "call", _ac_ok)
    OpenRouterAlignmentCheck.fail_open_detected = False

    evaluate_case_combined.run_evaluate_case_combined(_DATA)

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1  # exactly one Role.USER turn in _DATA
    entry = json.loads(lines[0])
    assert entry["text"] == "Summarize the news."
    assert isinstance(entry["score"], float)
    assert entry["decision"] in ("allow", "block")
