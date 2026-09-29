# Tasks: Taker Buy/Sell Flow as a Wyckoff Refinement

## Phase 1: Implementation

- [X] T001 Write `test_taker_flow.py`: fetch 4h OHLCV via raw `publicGetKlines` (recovering
      `taker_buy_base_volume`); regenerate slice 017's 330-event population (FR-001, FR-002).
- [X] T002 Compute `taker_buy_ratio` at each break candle; evaluate both pre-declared hypotheses
      with the 70/30 chronological split (FR-003).
- [X] T003 Run against real Binance data.

## Phase 2: Reporting

- [X] T004 Write `validation-report.md`: both hypotheses' in-sample/out-of-sample numbers, one
      recommendation combined with slices 017-019's pending decision (SC-001, SC-002).
- [X] T005 Confirm FR-004: no `app/` production code changed.

## Phase 3: Verification

- [X] T006 Confirm the existing test suite is unaffected (SC-003).
- [X] T007 [P] Refresh Graphify project graph.

## Phase 4: Convergence

Assessed 2026-09-28. 4/4 functional requirements verified. SC-001 met (both hypotheses evaluated;
hypothesis 2 correctly reported as insufficient sample rather than force-fit). SC-002 met (clear
recommendation: inconclusive, not confirmed, despite mechanically passing the pre-declared bar).
SC-003 confirmed (144/144 tests unaffected). No `app/` production code touched (FR-004).

**Result**: taker buy/sell flow (recovered from Binance's raw klines, a zero-cost data source not
previously used) does NOT provide a trustworthy refinement. The "absorption" hypothesis mechanically
cleared the out-of-sample bar (70.3% win rate, p=0.0137, n=37) but showed the opposite sign in-sample
(45.1%, -13.8pp vs baseline) — a sign-flip pattern indicative of noise, not a real effect, despite
passing the same numeric bar slice 017's genuine finding passed. Judged `inconclusive`, not added to
the validated-edge list. The "aggressive entry" hypothesis had too few qualifying events (8/3) to
test at all.

## Convergence Findings

| ID | Gap Type | Severity | Source | Evidence | Remaining Work |
|----|----------|----------|--------|----------|----------------|
| F1 | unrequested | LOW | This slice's own result | Sample sizes for extreme taker-ratio events (51-88 in-sample+out-of-sample combined) are small because most candles cluster near taker_buy_ratio=0.5; a longer historical window (Binance's raw klines support it, same zero-cost source) might yield enough sample to actually resolve whether absorption is real or noise | Future slice (optional, low priority): re-run this same test with 18-24 months of history instead of 10, specifically to grow the absorption-bucket sample past ~200 events before drawing a real conclusion. Not blocking any pending decision. |

**Outcome**: `tasks_appended` — F1 is a possible future refinement of method, not a pending operator
decision. The extreme-volume filter (slice 017) remains the sole validated edge; taker flow neither
strengthens nor weakens that conclusion.
