# Execution Report: Plan 2 (Metrics + Report)

**Branch:** `plan-2-metrics-report`
**Date:** 2026-08-14
**Plan executed:** `docs/superpowers/plans/2026-08-14-metrics-and-report.md`
**Base commit:** `bf4b262` (master, end of Plan 1)
**Final commit:** `5bcf033` (plan-2-metrics-report)
**Test suite:** 88/88 pass (0 regressions on Plan 1)

---

## 1. Commits (6 total, all on `plan-2-metrics-report`)

| # | Hash | Type | Message |
|---|------|------|---------|
| 1 | `c0b315b` | docs | add Plan 2 (metrics + report) with council checkpoint and grill-with-docs findings |
| 2 | `6a60563` | feat | add metrics result types (ConfidenceInterval/MetricScores/TechniqueBreakdown/MetricsResult) |
| 3 | `c2525bd` | feat | add compute_metrics with Wilson CI, primary/strict split, error exclusion, duplicate detection |
| 4 | `7c10db2` | feat | add script-generated Markdown report (5-part structure, transcript excerpts, deterministic) |
| 5 | `b27b57a` | test | add end-to-end integration test for metrics + report pipeline |
| 6 | `5bcf033` | fix | remove unused params from _f1_ci_from_pr_ci (whole-branch review) |

**Verify with:**
```bash
git log --oneline plan-2-metrics-report...master
```

---

## 2. Files Created/Modified

### New source files (2)

| File | Lines | Purpose |
|------|-------|---------|
| `src/toy_agent/metrics.py` | ~150 | `ConfidenceInterval`, `MetricScores`, `TechniqueBreakdown`, `MetricsResult` types + `wilson_ci()` + `compute_metrics()` |
| `src/toy_agent/report.py` | ~132 | `render_report()` - 5-part Markdown report generator |

### New test files (3)

| File | Tests | Purpose |
|------|-------|---------|
| `tests/toy_agent/test_metrics.py` | 19 | Unit tests for types, `wilson_ci`, `compute_metrics` (primary/strict/error/duplicate/technique) |
| `tests/toy_agent/test_report.py` | 10 | Unit tests for `render_report` (5 sections, CI, transcript excerpt, determinism, vendor comparison, setup notes) |
| `tests/toy_agent/test_metrics_e2e.py` | 3 | End-to-end: full pipeline (cases -> verdicts -> metrics -> report), never-fuse invariant, error-separate invariant |

### New doc files (2)

| File | Purpose |
|------|---------|
| `docs/superpowers/plans/2026-08-14-metrics-and-report.md` | The plan itself (written before execution, commit 1) |
| `docs/design/2026-08-14-metrics-gap-tracking.md` | Gap 8-12 findings from council checkpoint |

### No existing files modified (except `metrics.py` in commit 6)

---

## 3. TDD Compliance

Every task followed the 5-step TDD cycle prescribed by the plan:

| Task | Step 1 (write tests) | Step 2 (verify fail) | Step 3 (implement) | Step 4 (verify pass) | Step 5 (commit) |
|------|----------------------|----------------------|--------------------|---------------------|-----------------|
| Task 1 (types) | 6 tests written | PASS ModuleNotFoundError | `metrics.py` types only | PASS 6/6 | `6a60563` |
| Task 2 (compute) | 13 tests appended | PASS ImportError | `wilson_ci` + `compute_metrics` | PASS 19/19 | `c2525bd` |
| Task 3 (report) | 10 tests written | PASS ModuleNotFoundError | `report.py` | PASS 10/10 (after 1 test fix) | `7c10db2` |
| Task 4 (e2e) | 3 tests written | N/A (integration) | N/A | PASS 3/3 (after 1 test fix) | `b27b57a` |
| Task 5 (review) | N/A | N/A | 1 fix applied | PASS 88/88 | `5bcf033` |

### Test fixes during execution (2)

1. **`test_report_contains_error_count`**: test searched for `"Detector errors (status=error): 1"` but report produces `"**Detector errors (status=error):** 1"` (markdown bold). Fixed test to match exact string.
2. **`test_error_verdicts_always_reported_separately`**: test asserted `error_count != tn` but with 1 error and 1 TN they were numerically equal by coincidence. Fixed test to verify the sum invariant (`tp+fp+fn+tn+error_count == total_count`) instead.

---

## 4. Council Checkpoint Findings (Gap 8-12)

| Gap | Severity | Description | Resolution |
|-----|----------|-------------|------------|
| 8 | maggiore | Report had no transcript excerpt for misclassified cases | DONE: Added `_format_transcript_excerpt()` in `report.py` |
| 9 | moderata | Per-technique precision always 1.0 (fp=0 by construction) - misleading | DONE: New `TechniqueBreakdown` type with only tp/fn/recall/recall_ci |
| 10 | minore | Duplicate `case_id` in verdicts silently overwrote | DONE: `compute_metrics` detects and raises `ValueError` |
| 11 | minore | Report had no timestamp | DONE: Accepted as conscious deviation (better reproducibility) |
| 12 | minore | Tests used fragile substring matches | DONE: Tests use specific strings |

**Full details:** `docs/design/2026-08-14-metrics-gap-tracking.md`

---

## 5. Whole-Branch Review Findings

**1 issue found and fixed (commit `5bcf033`):**

- **File:** `src/toy_agent/metrics.py`
- **Issue:** `_f1_ci_from_pr_ci(p, r, p_ci, r_ci)` had parameters `p: float` and `r: float` that were never used in the function body (dead code).
- **Fix:** Removed `p` and `r` from the signature and from the call site in `_compute_scores`.
- **Risk:** None - removing unused parameters cannot change behavior.

---

## 6. Constraints Verified

| Constraint | How verified | Status |
|------------|-------------|--------|
| No vendor imports (`aidr...`) | `tests/test_no_vendor_imports.py` | PASS |
| No real I/O in tools | `tests/toy_agent/test_tools.py` (existing) | PASS |
| Primary and strict never fused | `test_metrics_never_fuse_primary_and_strict` | PASS |
| Error verdicts excluded from TP/FP/FN/TN | `test_compute_metrics_error_verdicts_excluded_from_counts` | PASS |
| Report is deterministic (no timestamp) | `test_report_is_deterministic` | PASS |
| Report includes confidence intervals | `test_report_contains_confidence_intervals` | PASS |
| Report includes transcript excerpts (Gap 8) | `test_report_contains_transcript_excerpt` | PASS |
| Duplicate case_id detected (Gap 10) | `test_compute_metrics_duplicate_verdict_raises` | PASS |
| TechniqueBreakdown has no precision/f1 (Gap 9) | `test_compute_metrics_per_technique_breakdown` | PASS |

---

## 7. How to Verify (for the second reviewer)

### Quick check (5 minutes)

```bash
# 1. Switch to the branch
git checkout plan-2-metrics-report

# 2. Run the full test suite
python -m pytest tests/ -v

# 3. Verify no vendor imports
python -m pytest tests/test_no_vendor_imports.py -v

# 4. Check the diff vs master
git diff master...plan-2-metrics-report --stat
```

### Deep review (30 minutes)

1. **Read the plan:** `docs/superpowers/plans/2026-08-14-metrics-and-report.md`
2. **Read the gap tracking:** `docs/design/2026-08-14-metrics-gap-tracking.md`
3. **Review `metrics.py`:** Check that `compute_metrics` correctly splits primary/strict, excludes errors, detects duplicates
4. **Review `report.py`:** Check that all 5 parts are present, transcript excerpts work, report is deterministic
5. **Review tests:** Check that test names match plan expectations, no tests are skipped or weakened
6. **Check commit messages:** Each commit is atomic and descriptive

### Specific things to look for

- [ ] `MetricsResult` has `primary` and `strict` as separate fields, no `aggregate`/`combined`/`overall`
- [ ] `TechniqueBreakdown` has only `tp`, `fn`, `recall`, `recall_ci` - no `precision` or `f1`
- [ ] `compute_metrics` raises `ValueError` on duplicate `case_id` in verdicts
- [ ] `compute_metrics` raises `ValueError` on mismatched lengths
- [ ] `render_report` output contains all 5 section headers
- [ ] `render_report` is deterministic (no `datetime.now()`, no `uuid`, no random)
- [ ] `_f1_ci_from_pr_ci` signature is `(p_ci, r_ci)` - no unused `p`/`r` params
- [ ] No `import aidr` anywhere in `src/toy_agent/`

---

## 8. Deviations from Plan

| Deviation | Reason | Impact |
|-----------|--------|--------|
| 2 test fixes during execution | Tests had incorrect assertions (markdown bold, numeric coincidence) | None - tests now correctly verify the intended behavior |
| `_f1_ci_from_pr_ci` signature changed during whole-branch review | Dead code found | None - removed unused params, behavior unchanged |
| Plan checkboxes not marked as complete (Task 5 Step 3) | Skipped to avoid extra commit | Minor - can be done in a follow-up |

---

## 9. Cost Analysis

| Metric | Value |
|--------|-------|
| Model used | Claude Sonnet 4 (via Cline) |
| Total tokens consumed | ~248K |
| Estimated cost | $5.6 |
| Tokens wasted (editor/PowerShell issues) | ~30K (~$1-1.5) |
| Effective cost without waste | ~$4-4.5 |
| Estimated cost with Sonnet 5 medium | ~$2.5-3.5 (30-50% savings) |
