from types import SimpleNamespace

import pytest

from detector_adapter.vendors.llamafirewall.adapter import (
    TOOL_NAME_COMBINED,
    aggregate_promptguard_turns,
    combine_scan_results_to_verdict,
    combined_error_verdict,
)


def _ac_result(decision_value="allow", reason="AC default", score=0.0):
    return SimpleNamespace(decision=SimpleNamespace(value=decision_value), reason=reason, score=score)


def _pg_turn(decision_value="allow", reason="No prompt injection detected", score=0.0):
    return SimpleNamespace(decision=SimpleNamespace(value=decision_value), reason=reason, score=score)


# --- aggregate_promptguard_turns ---

def test_aggregate_returns_allow_and_zero_score_for_no_turns():
    decision, score = aggregate_promptguard_turns([])
    assert decision == "allow"
    assert score == 0.0


def test_aggregate_takes_the_max_score_not_the_last_turn():
    turns = [_pg_turn(score=0.95), _pg_turn(score=0.1)]
    decision, score = aggregate_promptguard_turns(turns)
    assert score == 0.95


def test_aggregate_blocks_if_any_turn_blocks_even_if_not_the_last():
    turns = [_pg_turn(decision_value="block", score=0.95), _pg_turn(decision_value="allow", score=0.1)]
    decision, score = aggregate_promptguard_turns(turns)
    assert decision == "block"


def test_aggregate_allows_when_no_turn_blocks():
    turns = [_pg_turn(decision_value="allow", score=0.3), _pg_turn(decision_value="allow", score=0.4)]
    decision, score = aggregate_promptguard_turns(turns)
    assert decision == "allow"


# --- combine_scan_results_to_verdict ---

def test_label_is_malicious_when_only_alignmentcheck_flags():
    v = combine_scan_results_to_verdict(
        "c1", _ac_result(decision_value="human_in_the_loop_required", score=1.0), "allow", 0.1,
        [_pg_turn(score=0.1)], 1.0, 0.5,
    )
    assert v["label"] == "malicious"


def test_label_is_malicious_when_only_promptguard_flags():
    v = combine_scan_results_to_verdict(
        "c2", _ac_result(decision_value="allow", score=0.0), "block", 0.95,
        [_pg_turn(decision_value="block", reason="likely injection", score=0.95)], 1.0, 0.5,
    )
    assert v["label"] == "malicious"


def test_label_is_benign_when_neither_flags():
    v = combine_scan_results_to_verdict(
        "c3", _ac_result(decision_value="allow", score=0.0), "allow", 0.2,
        [_pg_turn(score=0.2)], 1.0, 0.5,
    )
    assert v["label"] == "benign"


def test_confidence_is_the_max_of_the_two_scores_even_when_benign():
    v = combine_scan_results_to_verdict(
        "c4", _ac_result(decision_value="allow", score=0.3), "allow", 0.7,
        [_pg_turn(score=0.7)], 1.0, 0.5,
    )
    assert v["confidence"] == 0.7


def test_rationale_always_contains_both_labeled_halves():
    v = combine_scan_results_to_verdict(
        "c5", _ac_result(reason="Observation: ...\nConclusion: False"), "allow", 0.0,
        [_pg_turn(reason="No prompt injection detected")], 1.0, 0.5,
    )
    assert "AlignmentCheck: Observation: ...\nConclusion: False" in v["rationale"]
    assert "PromptGuard: No prompt injection detected" in v["rationale"]


def test_technique_detected_is_always_none_even_when_promptguard_flags():
    v = combine_scan_results_to_verdict(
        "c6", _ac_result(decision_value="allow", score=0.0), "block", 0.95,
        [_pg_turn(decision_value="block", score=0.95)], 1.0, 0.5,
    )
    assert v["technique_detected"] is None


def test_latency_s_is_the_sum_of_both_measured_latencies():
    v = combine_scan_results_to_verdict("c7", _ac_result(), "allow", 0.0, [_pg_turn()], 1.2, 0.8)
    assert v["latency_s"] == pytest.approx(2.0)


def test_tool_name_is_the_combined_constant():
    v = combine_scan_results_to_verdict("c8", _ac_result(), "allow", 0.0, [_pg_turn()], 1.0, 0.5)
    assert v["tool_name"] == TOOL_NAME_COMBINED == "llamafirewall-combined"


def test_status_is_ok_on_the_normal_path():
    v = combine_scan_results_to_verdict("c9", _ac_result(), "allow", 0.0, [_pg_turn()], 1.0, 0.5)
    assert v["status"] == "ok"


def test_cost_usd_is_always_none():
    v = combine_scan_results_to_verdict("c10", _ac_result(), "allow", 0.0, [_pg_turn()], 1.0, 0.5)
    assert v["cost_usd"] is None


# --- combined_error_verdict ---

def test_combined_error_verdict_labels_alignmentcheck_failure_as_vendor_fail_open():
    v = combined_error_verdict("c11", "alignmentcheck", "RuntimeError")
    assert v["status"] == "error"
    assert v["label"] is None
    assert "vendor fail-open: RuntimeError" in v["rationale"]
    assert v["tool_name"] == TOOL_NAME_COMBINED


def test_combined_error_verdict_labels_promptguard_failure_as_local_dependency_error():
    v = combined_error_verdict("c12", "promptguard", "OutOfMemoryError")
    assert v["status"] == "error"
    assert v["label"] is None
    assert "local dependency error: OutOfMemoryError" in v["rationale"]


def test_combined_error_verdict_rejects_an_unknown_source():
    with pytest.raises(ValueError, match="unknown source"):
        combined_error_verdict("c13", "something-else", None)
