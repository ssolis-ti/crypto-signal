# Tasks: Trading Range, Spring, and Upthrust Detection

**Status**: Done.

## Phase 1: Tests first

- [X] T001 `tests/analyzers/test_wyckoff.py`: range detection on a synthetic horizontal-consolidation
      fixture; engineered spring fixture (break below support, return within window) flags exactly
      the confirmation candle; engineered upthrust mirror; a real-breakdown (no return) fixture flags
      nothing; insufficient-history edge case (FR-001 through FR-006).

## Phase 2: Implementation

- [X] T002 `app/analyzers/indicators/wyckoff.py`: `detect_trading_range`, `detect_springs`,
      `detect_upthrusts`, each attaching `relative_volume` context per FR-005.
- [X] T003 Confirm T001 passes.

## Phase 3: Verification

- [X] T004 Run full suite inside `crypto-signal:dev` Docker image; confirm all existing + new tests
      pass (SC-001).
- [X] T005 [P] Refresh Graphify project graph.

## Phase 4: Convergence

Assessed 2026-09-28. 6/6 functional requirements verified by code + tests. 10 new tests added; full
suite now 144/144 passing (134 prior + 10 new), zero regressions. SC-001/002/003 verified: engineered
spring/upthrust fixtures detected correctly, negative (no-return) fixture produces zero false
positives, no exception on short/degenerate input. Confirmed via `detect_trading_range`'s
`shift(1)`-based support/resistance that a candle cannot define its own range (dedicated regression
test `test_current_candle_does_not_define_its_own_range`). Still not wired into `config.yml` or any
alert path (FR-006), same as slice 013. 3/3 relevant constitution principles checked (I, III, VI), no
violations.

**Outcome**: `converged` — no additional tasks appended. Unblocks
`specs/015-wyckoff-historical-validation`.
