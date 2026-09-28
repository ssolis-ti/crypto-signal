# Tasks: UTC-Consistent Internal Time Handling

**Input**: Design documents from `specs/002-utc-internal-time/`

**Tests**: Included and REQUIRED — Constitution Principle VI covers both modified files
(`analyzers/utils.py` is part of the `IndicatorUtils` god node; `notifications/` is explicitly
listed).

## Phase 1: Setup

- [X] T001 [P] Create `tests/analyzers/__init__.py`, `tests/notifications/__init__.py`.

## Phase 2: User Story 1 - Indicator timestamps correct regardless of host timezone (P1) 🎯 MVP

### Tests first

- [X] T002 [P] [US1] `tests/analyzers/test_utils.py`: known epoch ms → UTC-aware index value;
      tz-awareness assertion (`.tzinfo is not None`, equals UTC); empty input → empty DataFrame,
      no exception; same input produces identical result when the test process's `TZ` env differs
      (parametrize or explicitly construct via a fixed epoch and assert against a computed UTC
      expectation rather than relying on process TZ, since pytest processes don't reliably let a
      single run switch TZ mid-test on all platforms).

### Implementation

- [X] T003 [US1] Rewrite `IndicatorUtils.convert_to_dataframe` in `app/analyzers/utils.py` to build
      the `datetime` column via `pandas.to_datetime(dataframe['timestamp'], unit='ms', utc=True)`,
      removing the `datetime.fromtimestamp`/`strftime('%c')` round trip and the now-unused
      `from datetime import datetime` import if nothing else in the file needs it.
- [X] T004 [US1] Confirm T002 passes.

**Checkpoint**: Indicator DataFrame index is UTC-aware and host-timezone-independent.

## Phase 3: User Story 2 - Alert rate-limiting immune to clock/DST shifts (P2)

### Tests first

- [X] T005 [P] [US2] `tests/notifications/test_builder.py`: `should_i_alert` suppresses a second
      call immediately after recording a frequency; freeze/mock `datetime.datetime.now` to simulate
      a local-clock rollback with no UTC time elapsed and assert the suppression is unaffected by
      that rollback (US2 Acceptance Scenario 2); confirm `creation_date` output (FR-003) is
      unchanged by mocking only the UTC-facing calls, not the existing local-timezone call at
      line ~179.

### Implementation

- [X] T006 [US2] In `app/notifications/builder.py`, change `parse_alert_frequency`'s
      `now = datetime.datetime.now()` to `datetime.datetime.now(datetime.timezone.utc)`, and
      `should_i_alert`'s comparison `datetime.datetime.now()` to the same UTC-aware call. Leave the
      `creation_date` line (`datetime.datetime.now(timezone(self.timezone_str))`) untouched.
- [X] T007 [US2] Confirm T005 passes.

**Checkpoint**: Both user stories independently verified.

## Phase 4: Polish

- [X] T008 [P] Run `graphify update .` to refresh the dependency graph.
- [X] T009 [P] Grep `app/` for any other naive `datetime.now()`/`fromtimestamp()` call sites not
      covered by this slice's two confirmed spots, to record as a future-slice finding if any exist
      (do not fix beyond scope here — record only).

## Dependencies & Execution Order

- User Story 1 (Phase 2) and User Story 2 (Phase 3) touch different files and are independent of
  each other; either can be done first. Numbered sequentially here only for a single linear
  narrative.
- Phase 4 runs after both.

## Implementation Strategy

MVP = Phase 1 + Phase 2 (indicator timestamps). Phase 3 is a smaller, independent follow-on fixing
the same class of bug in a different, lower-traffic code path.

## Phase 5: Convergence

Assessed 2026-09-28. T009's grep surfaced 3 additional naive-datetime spots beyond this slice's
two confirmed targets (FR-scope was explicitly "two confirmed spots"; not expanded mid-slice per
Development Workflow — recorded here for a future slice instead).

## Convergence Findings

| ID | Gap Type | Severity | Source | Evidence | Remaining Work |
|----|----------|----------|--------|----------|----------------|
| F1 | unrequested | HIGH | Principle V (new evidence, not in original spec scope) | `app/exchanges/driver.py:145` `_calculate_start_date` uses naive `datetime.now()` to compute the `since` timestamp passed to `fetch_ohlcv` — unlike the two fixed spots, this feeds an actual exchange API parameter, so a non-UTC host could request the wrong historical window | New slice: apply the same UTC-aware fix to `_calculate_start_date` |
| F2 | unrequested | LOW | Principle V | `app/rendering/utils.py:22` uses naive `datetime.datetime.fromtimestamp` for chart x-axis labels | **Resolved in specs/006-deferred-cleanup-findings/** (2026-09-28): UTC-aware fix, same pattern as F1/slice 002/003 |
| F3 | unrequested | LOW | Principle VII (overlaps slice 001 F3) | `app/utils/calibration.py:83,227` naive datetime in debug/calibration logging | **Resolved in specs/006-deferred-cleanup-findings/** (2026-09-28) |

**Summary metrics**: 5/5 FR verified by code + tests (23/23 passing) · 4/4 SC verified · 7/7
constitution principles checked, no violations in this slice's own scope · 3 `unrequested`
findings surfaced by the mandated T009 scan, 0 `missing`/`contradicts`.

**Outcome**: `tasks_appended` — F1 (HIGH) is the natural next slice (003); F2/F3 are LOW and can
ride along with F1 or wait.
