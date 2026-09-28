# Tasks: Clean Up Deferred Convergence Findings

**Input**: Design documents from `specs/006-deferred-cleanup-findings/`

## Phase 1: User Story 1 - get_top_pairs debug logging cleanup (P2, closes 001-F3)

### Tests first

- [X] T001 [US1] `tests/data/test_manager.py`: `TestGetTopPairs` — quote filtering, min-volume
      filtering, descending sort, `top_n` truncation, cache-hit short-circuit, against a fake driver
      (FR-003).

### Implementation

- [X] T002 [US1] In `app/data/manager.py::get_top_pairs`, demote the two `"DEBUG:"`-prefixed
      `logger.info` calls to `logger.debug` without the prefix; delete the two dead commented-out
      `logger.debug` lines (FR-001, FR-002).
- [X] T003 [US1] Confirm T001 passes; `grep -n "DEBUG:" app/data/manager.py` returns nothing (SC-002).

## Phase 2: User Story 2 - Chart timestamp UTC fix (P2, closes 002-F2)

### Tests first

- [X] T004 [US2] Create `tests/rendering/__init__.py`; `tests/rendering/test_utils.py`:
      `convert_to_dataframe` known-epoch UTC mapping, tz-awareness assertion, empty-input no-raise,
      columns/row-count preservation (FR-004, mirrors slice 002's `tests/analyzers/test_utils.py`).

### Implementation

- [X] T005 [US2] In `app/rendering/utils.py::convert_to_dataframe`, replace the naive
      `datetime.datetime.fromtimestamp` apply with
      `pandas.to_datetime(dataframe['timestamp'], unit='ms', utc=True)`; remove the now-unused
      `import datetime` if nothing else in the file needs it.
- [X] T006 [US2] Confirm T004 passes.

## Phase 3: User Story 3 - Calibration logger UTC fix (P3, closes 002-F3)

### Tests first

- [X] T007 [US3] Create `tests/utils/__init__.py`; `tests/utils/test_calibration.py`: `log_ohlcv`'s
      per-candle timestamp is UTC-based, `_report_anomaly`'s recorded timestamp is a UTC-aware
      ISO string (FR-005, FR-006).

### Implementation

- [X] T008 [US3] In `app/utils/calibration.py`, fix `log_ohlcv`'s
      `datetime.fromtimestamp(ts/1000)` → `datetime.fromtimestamp(ts/1000, tz=timezone.utc)`, and
      `_report_anomaly`'s `datetime.now()` → `datetime.now(timezone.utc)`; add `timezone` to the
      existing `from datetime import datetime` import.
- [X] T009 [US3] Confirm T007 passes.

## Phase 4: Polish

- [X] T010 Run full suite inside `crypto-signal:dev` Docker image; confirm 77 existing + new tests
      all pass (SC-001).
- [X] T011 [P] Refresh Graphify project graph.
- [X] T012 Mark the three originating findings (001-F3, 002-F2, 002-F3) resolved in
      `specs/001-no-repaint-signals/tasks.md` and `specs/002-utc-internal-time/tasks.md` (SC-004).

## Dependencies & Execution Order

Three user stories touch disjoint files — independent, any order. T001→T002→T003,
T004→T005→T006, T007→T008→T009 each self-contained; T010-T012 run after all three.

## Phase 5: Convergence

Assessed 2026-09-28. 8/8 functional requirements (FR-001 through FR-008) verified by code + tests.
11 new tests added (5 `TestGetTopPairs`, 4 `test_rendering/test_utils.py`, 2
`test_utils/test_calibration.py`); full suite now 88/88 passing (77 prior + 11 new), zero
regressions. SC-002 verified directly (`grep -n "DEBUG:" app/data/manager.py` returns nothing).
SC-004 verified: 001-F3, 002-F2, 002-F3 all marked resolved in their source `tasks.md` files. 7/7
constitution principles checked, no violations. One edge case (`convert_to_dataframe([])` raising
`ValueError`) was found to be the exact same pre-existing, out-of-scope bug already documented for
`analyzers/utils.py` in slice 002 — characterized in spec.md's Edge Cases, not fixed, consistent
with that precedent (no real caller passes an empty list). `CalibrationLogger` remains confirmed
dead code (FR-008) — noted, not a new finding, not actioned.

**Outcome**: `converged` — no additional tasks appended.
