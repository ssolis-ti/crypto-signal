# Tasks: 1D/4h Structural Confluence and Existing-TA Confirmation

## Phase 1: Implementation

- [X] T001 Write `test_confluence_and_ta.py`: regenerate slice 017's confirmed 4h event set;
      enrich with 1D confluence flag, RSI(14), ADX(14) at confirmation (FR-001 through FR-003).
- [X] T002 Implement chronological 70/30 split and evaluate all 3 candidates (FR-004).
- [X] T003 Run against real Binance data.

## Phase 2: Reporting

- [X] T004 Write `validation-report.md`: all 3 filters' in-sample/out-of-sample numbers with
      lift-over-baseline, one recommendation combining this with slices 017/018's pending decision
      (FR-006, SC-001, SC-002).
- [X] T005 Confirm FR-005: no `app/` production code changed.

## Phase 3: Verification

- [X] T006 Confirm the existing test suite is unaffected (SC-003).
- [X] T007 [P] Refresh Graphify project graph.

## Phase 4: Convergence

Assessed 2026-09-28. 6/6 functional requirements verified. SC-001 met (all 3 candidates evaluated
in-sample/out-of-sample). SC-002 met (unambiguous conclusion: none held up). SC-003 confirmed
(144/144 tests unaffected). No `app/` production code touched (FR-005).

**Result**: none of the three candidates (1D/4h structural confluence, RSI extremity, ADX strong
trend) added a confirmed incremental edge over slice 017's baseline — all three underperformed
out-of-sample relative to the unfiltered baseline (confluence −7.8pp, RSI −14.3pp, ADX −3.5pp).
Directly answers the operator's fractal-timeframe question: no useful correlation/detail found in
this bounded test. Combined with slices 007/011, this is now four separate tests (RSI alone,
macd_cross alone, 1D confluence, RSI/ADX as secondary filters) where classic TA / cross-timeframe
trend alignment failed to add value — the extreme-break-volume signature itself (slice 017) remains
the only validated edge in this project.

## Convergence Findings

| ID | Gap Type | Severity | Source | Evidence | Remaining Work |
|----|----------|----------|--------|----------|----------------|
| F1 | unrequested | LOW | This slice's own result | No further refinement found; continuing to test more candidates against the same 321-event dataset would itself risk multiple-comparisons overfitting | Recommend against further filter-search on this same dataset; if the operator wants to keep searching, a genuinely different data source (order-flow/order-book) or accepting slice 017's edge as final are the two live options — not more cuts of the same OHLCV-derived features. |

**Outcome**: `tasks_appended` — F1 is a scope-boundary recommendation, not a defect. The operator
decision already pending from slices 017/018 (whether/how to wire the validated extreme-volume
filter into a Telegram alert) remains the live open item.
