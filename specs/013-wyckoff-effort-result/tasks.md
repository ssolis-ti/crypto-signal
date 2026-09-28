# Tasks: Wyckoff Effort-vs-Result Primitives

## Phase 1: Tests first

- [X] T001 `tests/analyzers/test_wyckoff.py`: `relative_volume`/`relative_range` normal computation,
      `effort_result_ratio` both directions (climax-shaped and thin-move-shaped), NaN warm-up
      propagation, zero-ATR/zero-volume guards, `is_climax`/`is_thin_move` threshold logic including
      the NaN-input-returns-False case (FR-001 through FR-004).

## Phase 2: Implementation

- [X] T002 `app/analyzers/indicators/wyckoff.py`: `WyckoffPrimitives` static-method class
      (`relative_volume`, `relative_range`, `effort_result_ratio`, `is_climax`, `is_thin_move`),
      mirroring `DerivedIndicators`' existing pattern (FR-001 through FR-005).
- [X] T003 Confirm T001 passes.

## Phase 3: Verification

- [X] T004 Run full suite inside `crypto-signal:dev` Docker image; confirm 121 existing + new tests
      pass (SC-001).
- [X] T005 [P] Refresh Graphify project graph.

## Phase 4: Convergence

Assessed 2026-09-28. 6/6 functional requirements verified by code + tests. 13 new tests added; full
suite now 134/134 passing (121 prior + 13 new), zero regressions. SC-002/SC-003 verified: no new
dependency added, every degenerate-input path (zero volume, zero ATR/flat price, warm-up) covered by
a test with no exception/inf. 3/3 relevant constitution principles checked (I, III, VI), no
violations — `WyckoffPrimitives` is not wired into `config.yml` or any alert path (FR-005).

**Outcome**: `converged` — no additional tasks appended. Unblocks `specs/014-wyckoff-range-spring-upthrust`.
