# Tasks: Trading Range, Spring, and Upthrust Detection

**Status**: Not started — blocked on `specs/013-wyckoff-effort-result` landing.

## Phase 1: Tests first

- [ ] T001 `tests/analyzers/test_wyckoff.py`: range detection on a synthetic horizontal-consolidation
      fixture; engineered spring fixture (break below support, return within window) flags exactly
      the confirmation candle; engineered upthrust mirror; a real-breakdown (no return) fixture flags
      nothing; insufficient-history edge case (FR-001 through FR-006).

## Phase 2: Implementation

- [ ] T002 `app/analyzers/indicators/wyckoff.py`: `detect_trading_range`, `detect_springs`,
      `detect_upthrusts`, each attaching `relative_volume` context per FR-005.
- [ ] T003 Confirm T001 passes.

## Phase 3: Verification

- [ ] T004 Run full suite inside `crypto-signal:dev` Docker image; confirm all existing + new tests
      pass (SC-001).
- [ ] T005 [P] Refresh Graphify project graph.

## Phase 4: Convergence

Not yet assessed — pending implementation.
