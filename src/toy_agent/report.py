from __future__ import annotations

from .metrics import MetricsResult, MetricScores, ConfidenceInterval, TechniqueBreakdown
from .schema import TestCase, Verdict, Transcript


def _fmt_ci(ci: ConfidenceInterval) -> str:
    return f"[{ci.lower:.3f}, {ci.upper:.3f}]"


def _fmt_scores_table_row(name: str, s: MetricScores) -> str:
    return (
        f"| {name} | {s.precision:.3f} {_fmt_ci(s.precision_ci)} | "
        f"{s.recall:.3f} {_fmt_ci(s.recall_ci)} | "
        f"{s.f1:.3f} {_fmt_ci(s.f1_ci)} | "
        f"{s.tp} | {s.fp} | {s.fn} | {s.tn} |"
    )


def _fmt_technique_row(name: str, tb: TechniqueBreakdown) -> str:
    return (
        f"| {name} | {tb.recall:.3f} {_fmt_ci(tb.recall_ci)} | "
        f"{tb.tp} | {tb.fn} |"
    )


def _format_transcript_excerpt(transcript: Transcript, max_turns: int = 3, max_content_len: int = 200) -> str:
    """Format first N turns of a transcript for the report (Gap 8)."""
    lines = []
    for turn in transcript.turns[:max_turns]:
        content = turn.content
        if len(content) > max_content_len:
            content = content[:max_content_len] + "..."
        lines.append(f"  - **{turn.role}** (turn {turn.seq}): {content}")
    if len(transcript.turns) > max_turns:
        lines.append(f"  - *... ({len(transcript.turns) - max_turns} more turns)*")
    return "\n".join(lines)


def _find_misclassified_cases(
    cases: list[TestCase], verdicts: list[Verdict], limit: int = 3
) -> list[tuple[TestCase, Verdict]]:
    """Return up to `limit` cases where the detector was wrong (FP or FN)."""
    verdict_map = {v.case_id: v for v in verdicts}
    misclassified = []
    for case in cases:
        v = verdict_map.get(case.case_id)
        if v is None or v.status == "error":
            continue
        if v.label != case.label:
            misclassified.append((case, v))
        if len(misclassified) >= limit:
            break
    return misclassified


def render_report(
    cases: list[TestCase],
    verdicts: list[Verdict],
    metrics: MetricsResult,
    tool_name: str = "agentic-threat-detection",
    setup_notes: str = "",
) -> str:
    """Generate a 5-part Markdown audit report from metrics + cases.

    This function is the ONLY way to produce a report — no hand-editing of
    numbers is allowed, ensuring the link between reported and computed
    values is mechanical, not discretionary (SPIRIT.md principle 4).
    """
    lines: list[str] = []

    # --- Part 1: Executive Summary ---
    lines.append("# Audit Report: " + tool_name)
    lines.append("")
    lines.append("## 1. Executive Summary")
    lines.append("")
    lines.append("**Scope tested:** Customer-support toy agent (medium scope).")
    lines.append("**Warning:** Results do not automatically generalize to other agent scopes.")
    lines.append("")
    lines.append(f"**Total cases:** {metrics.total_count}")
    lines.append(f"**Detector errors (status=error):** {metrics.error_count}")
    lines.append("")
    lines.append("### Primary metric (label-only)")
    lines.append("")
    lines.append(f"- **Precision:** {metrics.primary.precision:.3f} {_fmt_ci(metrics.primary.precision_ci)}")
    lines.append(f"- **Recall:** {metrics.primary.recall:.3f} {_fmt_ci(metrics.primary.recall_ci)}")
    lines.append(f"- **F1:** {metrics.primary.f1:.3f} {_fmt_ci(metrics.primary.f1_ci)}")
    lines.append("")
    lines.append("### Strict metric (technique attribution)")
    lines.append("")
    lines.append(f"- **Precision:** {metrics.strict.precision:.3f} {_fmt_ci(metrics.strict.precision_ci)}")
    lines.append(f"- **Recall:** {metrics.strict.recall:.3f} {_fmt_ci(metrics.strict.recall_ci)}")
    lines.append(f"- **F1:** {metrics.strict.f1:.3f} {_fmt_ci(metrics.strict.f1_ci)}")
    lines.append("")
    lines.append("### Vendor-declared numbers (for comparison)")
    lines.append("")
    lines.append("- **Vendor P=1.0, R=0.667** (300 sessions, 42 malicious)")
    lines.append("")

    # --- Part 2: Findings Table ---
    lines.append("## 2. Findings Table")
    lines.append("")
    lines.append("| Metric | Precision [95% CI] | Recall [95% CI] | F1 [95% CI] | TP | FP | FN | TN |")
    lines.append("|---|---|---|---|---|---|---|---|")
    lines.append(_fmt_scores_table_row("Primary", metrics.primary))
    lines.append(_fmt_scores_table_row("Strict", metrics.strict))
    lines.append("")

    if metrics.per_technique:
        lines.append("### Per-technique breakdown (strict — technique-attribution recall)")
        lines.append("")
        lines.append("| Technique | Recall [95% CI] | TP | FN |")
        lines.append("|---|---|---|---|")
        for tech in sorted(metrics.per_technique.keys()):
            lines.append(_fmt_technique_row(tech, metrics.per_technique[tech]))
        lines.append("")

    if metrics.per_technique_primary:
        lines.append("### Per-technique breakdown (primary — detection recall, technique-agnostic)")
        lines.append("")
        lines.append("| Technique | Recall [95% CI] | TP | FN |")
        lines.append("|---|---|---|---|")
        for tech in sorted(metrics.per_technique_primary.keys()):
            lines.append(_fmt_technique_row(tech, metrics.per_technique_primary[tech]))
        lines.append("")

    # --- Part 3: Methodology and Limitations ---
    lines.append("## 3. Methodology and Limitations")
    lines.append("")
    lines.append("- **Confidence intervals:** Wilson score interval (95% level), appropriate for small samples (Brown, Cai & DasGupta 2001).")
    lines.append("- **F1 CI:** Conservative approximation from P and R interval corners (declared limitation, not an exact interval).")
    lines.append(f"- **Sample size:** {metrics.total_count} cases total, {metrics.error_count} detector errors excluded from TP/FP/FN/TN.")
    lines.append(f"- **Small sample warning:** With {metrics.total_count} cases, confidence intervals are wide - results are indicative, not definitive. Consistent with SPIRIT.md principle 3 (statistical honesty).")
    lines.append("- **Per-technique breakdown:** Reports recall only (precision is always 1.0 by construction with fp=0 - Gap 9, misleading to report). Two variants, matching the design doc's request for a breakdown on both metrics: the strict table's `tp` requires the detected technique to match the target (a detector that flags a session as malicious but attributes the wrong technique does not count as a strict per-technique tp); the primary table's `tp` only requires the session to be flagged malicious at all, independent of attribution (Gap 13, whole-branch review, second reviewer).")
    lines.append("- **Determinism:** This report is fully deterministic (no timestamp) - regenerating from the same data produces a bit-identical file.")
    if setup_notes:
        lines.append(f"- **Setup notes:** {setup_notes}")
    lines.append("")

    # --- Part 4: Concrete Cases ---
    lines.append("## 4. Concrete Cases (Misclassifications)")
    lines.append("")
    misclassified = _find_misclassified_cases(cases, verdicts)
    if misclassified:
        for case, verdict in misclassified:
            error_type = "False Negative" if case.label == "malicious" else "False Positive"
            lines.append(f"### {case.case_id} - {error_type}")
            lines.append("")
            lines.append(f"- **Ground truth:** {case.label}" + (f" ({case.technique_target})" if case.technique_target else ""))
            lines.append(f"- **Detector verdict:** {verdict.label}" + (f" ({verdict.technique_detected})" if verdict.technique_detected else ""))
            lines.append(f"- **Rationale (written before detection):** {case.rationale}")
            lines.append("- **Transcript excerpt:**")
            if case.transcript is None:
                lines.append("  - *(no transcript recorded)*")
            else:
                lines.append(_format_transcript_excerpt(case.transcript))
            lines.append("")
    else:
        lines.append("No misclassifications detected.")
        lines.append("")

    # --- Part 5: Raw Data ---
    lines.append("## 5. Raw Data")
    lines.append("")
    lines.append("Full TestCase + Verdict pairs are published alongside this report in the same commit, in YAML format.")
    lines.append("")
    lines.append(f"- Total TestCase count: {len(cases)}")
    lines.append(f"- Total Verdict count: {len(verdicts)}")
    lines.append(f"- Detector errors: {metrics.error_count}/{metrics.total_count}")
    lines.append("")

    return "\n".join(lines)
