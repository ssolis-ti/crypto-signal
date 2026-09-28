# Tasks: Historical Validation of the SignalEnhancer Score for macd_cross

## Phase 1: Implementation

- [X] T001 Write `validate_macd_cross.py`: reuse slice 007's fetch/context-reconstruction/scoring/
      aggregation code (basket, date range, permutation test), replace RSI threshold-crossing
      detection with MACD-histogram sign-change detection (FR-001 through FR-006).
- [X] T002 Run the script against real Binance data; capture full output (SC-001).

## Phase 2: Reporting

- [X] T003 Write `validation-report.md`: methodology (citing slice 007 by reference for anything
      unchanged), full results, explicit comparison to slice 007's RSI conclusion, one
      recommendation (FR-007, SC-002).
- [X] T004 Apply FR-008: no unilateral scoring/gate change regardless of result; if the result would
      imply one, record as a Convergence finding for operator sign-off.

## Phase 3: Verification

- [X] T005 Confirm the existing 121-test suite is unaffected (SC-003).
- [X] T006 Mark slice 007's F2 Convergence finding (`macd_cross` unvalidated) resolved (SC-004).
- [X] T007 [P] Refresh Graphify project graph.

## Phase 4: Convergence

Assessed 2026-09-28. 8/8 functional requirements verified. SC-001 exceeded (1,776 events, target
~30). SC-002 met (`validation-report.md` has concrete numbers, significance test, and an explicit
comparison to slice 007). SC-003 confirmed (121/121 existing tests unaffected). SC-004 verified:
slice 007's F2 finding marked resolved.

**Result**: reinforces slice 007's conclusion. At the 72h horizon (n=1754), score/outcome
correlation is statistically significant and **negative** (p=0.0055) — the largest, most confident
sample of this project's two validation slices shows the score actively anti-correlates with
outcome, not merely failing to predict it.

**FR-008 disposition**: no unilateral change made. This is recorded as reinforcement of the existing
Convergence finding (specs/007 F1) rather than a new operator decision point — the operator's
standing choice (keep the gate as-is pending redesign + re-validation) already covers this outcome.

## Convergence Findings

| ID | Gap Type | Severity | Source | Evidence | Remaining Work |
|----|----------|----------|--------|----------|----------------|
| F1 | unrequested | LOW | Scope boundary (this slice) | Only RSI and macd_cross were validated; no other indicator (Bollinger, Ichimoku, ADX, etc.) is enabled in current production config, so none are queued, but if `config-clean.yml` ever enables another signal-generating indicator it should be validated the same way before being trusted for gating | Future: validate any newly-enabled signal indicator before it influences `detail_min_quality`/`chart_min_quality` |

**Outcome**: `tasks_appended` — F1 is a standing practice note, not an active defect.
