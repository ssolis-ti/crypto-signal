# Tasks: Correct UTC Start-Date Calculation for Historical Data Fetch

**Input**: Design documents from `specs/003-utc-start-date/`

**Tests**: Included — same discipline as slices 001/002, applied here even though
`exchanges/driver.py` isn't in the constitution's explicit package list, because it directly feeds
the tested `data/manager.py` pipeline.

## Phase 1: Setup

- [X] T001 [P] Create `tests/exchanges/__init__.py`.

## Phase 2: User Story 1 - Correct historical window regardless of host timezone (P1) 🎯 MVP

### Tests first

- [X] T002 [P] [US1] `tests/exchanges/test_driver.py`: for a fixed `time_unit`/`max_periods`,
      compute `_calculate_start_date` and assert it equals
      `int((datetime.now(timezone.utc) - max_periods*delta).timestamp()*1000)` within a small
      tolerance (a few hundred ms for test execution time) rather than relying on process `TZ`
      switching (same rationale as slice 002's tests); parametrize across `m/h/d/w/M/y` period
      types to cover SC-003; assert `ValueError` still raised for an invalid `time_unit` string
      (FR-003 regression guard).

### Implementation

- [X] T003 [US1] In `app/exchanges/driver.py::_calculate_start_date`, change
      `datetime.now() - (max_periods * start_date_delta)` to
      `datetime.now(timezone.utc) - (max_periods * start_date_delta)`, and simplify the return line
      from `int(max_days_date.replace(tzinfo=timezone.utc).timestamp() * 1000)` to
      `int(max_days_date.timestamp() * 1000)`.
- [X] T004 [US1] Confirm T002 passes.

**Checkpoint**: `since` timestamps sent to the exchange are correct regardless of host timezone.

## Phase 3: Polish

- [X] T005 [P] Run `graphify update .`.

## Dependencies & Execution Order

Single user story, single function — no cross-story dependencies. T001 → T002 → T003 → T004 → T005.

## Phase 4: Convergence

Assessed 2026-09-28. 4/4 FR verified by code + tests (8/8 new tests passing, 31/31 total suite).
3/3 SC verified, including a direct before/after reproduction under `TZ=America/Santiago` showing
the pre-fix code was off by exactly 3 hours (10,800,000 ms) — confirming this was a real,
reproducible bug for this deployment's configured timezone, not theoretical. 7/7 constitution
principles checked, no violations. No new findings beyond this slice's scope.

**Outcome**: `converged` — no additional tasks appended.
