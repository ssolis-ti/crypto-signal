# Tasks: Historical Validation of Wyckoff Spring/Upthrust Signals

**Status**: Ready to start — `specs/014-wyckoff-range-spring-upthrust` landed 2026-09-28.

## Phase 1: Implementation

- [ ] T001 Write `validate_wyckoff_springs.py`: reuse slices 007/011's fetch/context-reconstruction/
      permutation-test code; detect events via slice 014's `detect_springs`/`detect_upthrusts`;
      compute forward returns at 24h/72h/7d/14d (FR-001 through FR-003).
- [ ] T002 Run against real Binance data; if Spring/Upthrust sample size is inadequate (see spec Edge
      Cases), extend the historical window and/or basket before reporting, rather than reporting an
      underpowered result as conclusive.

## Phase 2: Reporting

- [ ] T003 Write `validation-report.md`: methodology, full results at all four horizons, explicit
      fact-check of the operator's "+20-30% over 1-2 weeks" recollection (FR-004), explicit
      comparison to slices 007 and 011 (FR-005), one recommendation.
- [ ] T004 Apply the same FR-006 discipline as slices 007/011: no unilateral scoring/gate change:
      record any implied change as a Convergence finding for operator sign-off.

## Phase 3: Verification

- [ ] T005 Confirm the existing test suite is unaffected (SC-003).
- [ ] T006 [P] Refresh Graphify project graph.

## Phase 4: Convergence

Not yet assessed — pending implementation.
