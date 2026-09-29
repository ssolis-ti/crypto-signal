# Tasks: Search for a Trade-Worthy Wyckoff Edge

## Phase 1: Implementation

- [X] T001 Write `search_wyckoff_edge.py`: regenerate slice 015's event set; enrich with 1D EMA trend
      alignment, range compression at break, break-candle `is_climax`, BTC regime alignment
      (FR-001).
- [X] T002 Implement chronological 70/30 in-sample/out-of-sample split (FR-002).
- [X] T003 Evaluate all 4 candidate filters, in-sample and out-of-sample, reporting every one
      regardless of outcome (FR-003).
- [X] T004 Run against real Binance data.

## Phase 2: Reporting

- [X] T005 Write `validation-report.md`: all 4 filters' in-sample/out-of-sample numbers, one
      unambiguous recommendation naming a specific validated filter or concluding none survived
      (FR-005, SC-002).
- [X] T006 Confirm FR-004: no `app/` production code changed by this slice.

## Phase 3: Verification

- [X] T007 Confirm the existing test suite is unaffected (SC-003).
- [X] T008 [P] Refresh Graphify project graph.

## Phase 4: Convergence

Assessed 2026-09-28. 5/5 functional requirements verified. SC-001 met (all 4 filters evaluated
in-sample and out-of-sample). SC-002 met (one specific, named, validated filter identified). SC-003
confirmed (144/144 tests unaffected). No `app/` production code touched (FR-004).

**Result**: 1 of 4 candidate filters (extreme break-candle volume, relative_volume >= 2.5x) survived
the chronological out-of-sample check with a real, meaningful lift over baseline in both periods
(+6.6pp in-sample, +5.5pp out-of-sample) — out-of-sample win rate 62.4% (n=101, p=0.013), mean
return +2.36% at 14 days. The other 3 (HTF trend alignment, range compression, BTC regime alignment)
did not show a genuine incremental edge once compared against each period's own baseline (HTF
alignment was a near-miss — real but mostly redundant with the period's general improvement; BTC
regime alignment was a clear overfit, reversing sign out-of-sample).

## Convergence Findings

| ID | Gap Type | Severity | Source | Evidence | Remaining Work |
|----|----------|----------|--------|----------|----------------|
| F1 | unrequested | MEDIUM | This slice's own result | A validated, holdout-tested filter exists (extreme break volume) with a real ~60% win rate at 14d — the first genuinely actionable candidate across 4 validation slices | **Operator decision needed**: build a follow-up slice wiring this specific, narrowly-defined filter into a dedicated Wyckoff Telegram alert path (separate from `SignalEnhancer`), with honest framing (~60% win rate / ~2.4% typical move, not the originally-recalled 20-30%) — or hold for further study first. No code wired by this slice (FR-004). |

**Outcome**: `tasks_appended` — F1 is a decision for the operator, same discipline as every prior
validation slice in this project.
