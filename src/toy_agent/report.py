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
    lines = []
    for turn in transcript.turns[:max_turns]:
        content = turn.content
        if len(content) > max_content_len:
            content = content[:max_content_len] + "..."
        lines.append(f"  - **{turn.role}** (turn {turn.seq}): {content}")
    if len(transcript.turns) > max_turns:
        lines.append(f"  - *... ({len(transcript.turns) - max_turns} more turns)*")
    return "\n".join(lines)


def _find_misclassified_cases(cases, verdicts, limit=3):
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


def render_report(cases, verdicts, metrics, tool_name="agentic-threat-detection", setup_notes=""):
    lines = []
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
    lines.append("## 2. Findings Table")
    lines.append("")
    lines.append("| Metric | Precision [95% CI] | Recall [95% CI] | F1 [95% CI] | TP | FP | FN | TN |")
    lines.append("|---|---|---|---|---|---|---|---|")
    lines.append(_fmt_scores_table_row("Primary", metrics.primary))
    lines.append(_fmt_scores_table_row("Strict", metrics.strict))
    lines.append("")
    if metrics.per_technique:
        lines.append("### Per-technique breakdown (primary metric, recall only)")
        lines.append("")
        lines.append("| Technique | Recall [95% CI] | TP | FN |")
        lines.append("|---|---|---|---|")
        for tech in sorted(metrics.per_technique.keys()):
            lines.append(_fmt_technique_row(tech, metrics.per_technique[tech]))
        lines.append("")
    lines.append("## 3. Methodology and Limitations")
    lines.append("")
    lines.append("- **Confidence intervals:** Wilson score interval (95% level), appropriate for small samples (Brown, Cai & DasGupta 2001).")
    lines.append("- **F1 CI:** Conservative approximation from P and R interval corners (declared limitation, not an exact interval).")
    lines.append(f"- **Sample size:** {metrics.total_count} cases total, {metrics.error_count} detector errors excluded from TP/FP/FN/TN.")
    lines.append(f"- **Small sample warning:** With {metrics.total_count} cases, confidence intervals are wide - results are indicative, not definitive. Consistent with SPIRIT.md principle 3 (statistical honesty).")
    lines.append("- **Per-technique breakdown:** Reports recall only (precision is always 1.0 by construction with fp=0 - Gap 9, misleading to report).")
    lines.append("- **Determinism:** This report is fully deterministic (no timestamp) - regenerating from the same data produces a bit-identical file.")
    if setup_notes:
        lines.append(f"- **Setup notes:** {setup_notes}")
    lines.append("")
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
            lines.append(_format_transcript_excerpt(case.transcript))
            lines.append("")
    else:
        lines.append("No misclassifications detected.")
        lines.append("")
    lines.append("## 5. Raw Data")
    lines.append("")
    lines.append("Full TestCase + Verdict pairs are published alongside this report in the same commit, in YAML format.")
    lines.append("")
    lines.append(f"- Total TestCase count: {len(cases)}")
    lines.append(f"- Total Verdict count: {len(verdicts)}")
    lines.append(f"- Detector errors: {metrics.error_count}/{metrics.total_count}")
    lines.append("")
    return "\n".join(lines)
