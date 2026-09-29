# Tasks: Timing and Drawdown Risk of the Extreme-Volume Wyckoff Signal

## Phase 1: Implementation

- [X] T001 Write `analyze_wyckoff_timing.py`: regenerate slice 017's confirmed-filter event set
      (FR-001); fetch real 1h OHLCV per event's 14-day forward window (FR-002).
- [X] T002 Compute the checkpoint curve (1h..14d) and MAE/MFE per event (FR-003, FR-004).
- [X] T003 Run against real Binance data.

## Phase 2: Reporting

- [X] T004 Write `validation-report.md`: checkpoint curve, MAE/MFE distributions and threshold-breach
      rates, one clear conclusion on usable time horizon + leverage risk (SC-001 through SC-003),
      explicit resolution-boundary disclaimer (FR-005).
- [X] T005 Confirm FR-006: no `app/` production code changed.

## Phase 3: Verification

- [X] T006 Confirm the existing test suite is unaffected (SC-004).
- [X] T007 [P] Refresh Graphify project graph.

## Phase 4: Convergence

Assessed 2026-09-28. 6/6 functional requirements verified. SC-001/002 met (full checkpoint curve +
MAE/MFE distributions with concrete numbers). SC-003 met (clear conclusion: fast action has highest
win rate but small magnitude, holding longer has bigger magnitude but real drawdown risk). SC-004
confirmed (144/144 tests unaffected). No `app/` production code touched (FR-006). Resolution
boundary stated explicitly (FR-005).

**Result**: win rate is highest immediately after the alert (72.9% at 1h, peaking 78.2% at 2h) with
small typical magnitude (<1%), declining toward the already-known ~60-64% by 7-14 days as magnitude
grows (median +2.84% at 14d). Drawdown risk is material: 68.5% of events see >=2% adverse excursion,
26.5% see >=10%, before 14 days — directly relevant to leveraged position sizing. Median time-to-peak
favorable move is ~9 days, meaning short holds systematically leave most of the eventual move
uncaptured. Neither the fast nor the slow approach supports the originally-recalled "seconds to
minutes for a large move."

## Convergence Findings

| ID | Gap Type | Severity | Source | Evidence | Remaining Work |
|----|----------|----------|--------|----------|----------------|
| F1 | unrequested | MEDIUM | This slice's own result, extending slice 017's F1 | Timing/risk profile now characterized for the validated extreme-volume filter: fast entry = high win rate/small magnitude; slow hold = bigger magnitude/real drawdown risk (up to 26.5% of events seeing >=10% adverse excursion) | **Operator decision needed** (same decision point as slice 017's F1, now with concrete risk numbers): (a) build the Telegram alert framed around the fast/high-win-rate window; (b) frame it around the hold-to-14d window with explicit stop/margin guidance from the MAE table; (c) both, clearly labeled as different strategies; (d) hold for further study (e.g., real slippage-aware backtest, or live paper-trading for true sub-hour timing). No code wired by this slice. |

**Outcome**: `tasks_appended` — F1 extends slice 017's still-open decision with the risk/timing detail
needed to actually size a leveraged position, rather than opening a new, separate decision.
