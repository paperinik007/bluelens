import os

import pytest

pytest.importorskip("llamafirewall", reason="llamafirewall is only installed inside the detector-llamafirewall container")

from detector_adapter.vendors.llamafirewall.adapter import DEFAULT_MODEL, TOOL_NAME, OpenRouterAlignmentCheck


def test_zero_arg_construction_matches_create_scanner_contract(monkeypatch):
    # llamafirewall.llamafirewall.create_scanner() instantiates a registered
    # custom scanner with scanner_class() — zero arguments. This must not raise.
    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")
    scanner = OpenRouterAlignmentCheck()
    assert scanner.name == TOOL_NAME


def test_default_model_is_used_when_env_var_is_unset(monkeypatch):
    monkeypatch.delenv("LLAMAFIREWALL_MODEL", raising=False)
    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")
    scanner = OpenRouterAlignmentCheck()
    assert scanner.llm.model_name == DEFAULT_MODEL


def test_llamafirewall_model_env_var_overrides_the_default(monkeypatch):
    monkeypatch.setenv("LLAMAFIREWALL_MODEL", "vendor/other-model")
    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")
    scanner = OpenRouterAlignmentCheck()
    assert scanner.llm.model_name == "vendor/other-model"


def test_construction_points_at_the_local_proxy_not_openrouter_directly():
    os.environ["LLAMAFIREWALL_OPENROUTER_API_KEY"] = "sk-test-not-real"
    scanner = OpenRouterAlignmentCheck()
    assert "127.0.0.1" in str(scanner.llm.client.base_url)


def test_require_full_trace_is_set_like_the_real_alignmentcheck_scanner(monkeypatch):
    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")
    scanner = OpenRouterAlignmentCheck()
    assert scanner.require_full_trace is True


def test_construction_raises_a_clear_error_without_the_api_key(monkeypatch):
    monkeypatch.delenv("LLAMAFIREWALL_OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError, match="LLAMAFIREWALL_OPENROUTER_API_KEY"):
        OpenRouterAlignmentCheck()
