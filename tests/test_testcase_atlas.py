"""Structural checks for TestCase schema additions (Atlas 6-gap batch)."""

from toy_agent.schema import Always, TestCase


def test_testcase_strict_significant_defaults_to_true():
    case = TestCase(
        case_id="schema_smoke_strict_default",
        label="malicious",
        technique_target="T0001",
        rationale="schema smoke test — strict_significant default",
        attack_success_criteria=Always(),
    )
    assert case.strict_significant is True


def test_testcase_strict_significant_explicit_false_is_accepted():
    case = TestCase(
        case_id="schema_smoke_strict_explicit_false",
        label="malicious",
        technique_target="T-ATLAS-atlas-t0077-rendering",
        rationale="schema smoke test — strict_significant=False synthetic target",
        strict_significant=False,
        attack_success_criteria=Always(),
    )
    assert case.strict_significant is False
