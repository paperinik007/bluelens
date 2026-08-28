from types import SimpleNamespace

from detector_adapter.vendors.llamafirewall.adapter import TOOL_NAME, scan_decision_to_verdict


def _scan_result(decision_value="allow", reason="default", score=0.0):
    return SimpleNamespace(
        decision=SimpleNamespace(value=decision_value),
        reason=reason,
        score=score,
    )


def test_human_in_the_loop_required_maps_to_malicious():
    v = scan_decision_to_verdict("c1", _scan_result(decision_value="human_in_the_loop_required", score=1.0))
    assert v["label"] == "malicious"


def test_allow_maps_to_benign():
    v = scan_decision_to_verdict("c2", _scan_result(decision_value="allow", score=0.0))
    assert v["label"] == "benign"


def test_block_maps_to_benign_not_malicious():
    # AlignmentCheckScanner never actually emits BLOCK (verified on the real
    # source, llamafirewall/scanners/experimental/alignmentcheck_scanner.py:
    # _convert_score_to_decision only returns HUMAN_IN_THE_LOOP_REQUIRED or
    # ALLOW) — this pins the design doc's exact mapping formula
    # ("malicious iff HUMAN_IN_THE_LOOP_REQUIRED, else benign") for the
    # unreachable-in-practice case too, so a future change to the vendor's
    # scan() logic that starts emitting BLOCK is caught here, not silently
    # misclassified as malicious.
    v = scan_decision_to_verdict("c3", _scan_result(decision_value="block", score=1.0))
    assert v["label"] == "benign"


def test_score_becomes_confidence():
    v = scan_decision_to_verdict("c4", _scan_result(score=0.73))
    assert v["confidence"] == 0.73


def test_reason_becomes_rationale():
    v = scan_decision_to_verdict("c5", _scan_result(reason="Observation: ...\nConclusion: True"))
    assert v["rationale"] == "Observation: ...\nConclusion: True"


def test_empty_reason_normalizes_to_none_rationale():
    v = scan_decision_to_verdict("c6", _scan_result(reason=""))
    assert v["rationale"] is None


def test_technique_detected_is_always_none():
    # AlignmentCheck has no technique attribution (CONTEXT.md, "Tool") — only
    # aidr's strict metric has one.
    v = scan_decision_to_verdict("c7", _scan_result(decision_value="human_in_the_loop_required"))
    assert v["technique_detected"] is None


def test_tool_name_is_the_declared_llamafirewall_constant():
    v = scan_decision_to_verdict("c8", _scan_result())
    assert v["tool_name"] == TOOL_NAME == "llamafirewall-alignmentcheck"


def test_status_is_ok_on_the_normal_path():
    v = scan_decision_to_verdict("c9", _scan_result())
    assert v["status"] == "ok"


def test_latency_s_defaults_to_none_when_the_caller_does_not_pass_it():
    v = scan_decision_to_verdict("c10", _scan_result())
    assert v["latency_s"] is None


def test_latency_s_is_recorded_when_the_caller_passes_it():
    # I4 (final review): evaluate_case.py measures wall-clock latency around
    # the actual scan call and passes it through here.
    v = scan_decision_to_verdict("c11", _scan_result(), latency_s=1.23)
    assert v["latency_s"] == 1.23
