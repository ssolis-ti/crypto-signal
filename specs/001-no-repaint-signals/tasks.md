# Tasks: Eliminate Signal Repaint

**Input**: Design documents from `specs/001-no-repaint-signals/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included and REQUIRED — Constitution Principle VI mandates tests for any change to
`data/`, and this feature modifies `data/manager.py` directly.

## Phase 1: Setup

- [X] T001 Create `requirements-dev.txt` at repo root with `pytest` pinned to a specific version;
      not referenced by `Dockerfile` (dev-only).
- [X] T002 [P] Create `tests/__init__.py` and `tests/data/__init__.py` (new top-level `tests/`
      directory, sibling to `app/`, per plan.md Project Structure).

## Phase 2: Foundational (blocking prerequisite)

- [X] T003 Implement pure helper `drop_unclosed_candle(ohlcv, timeframe, now_utc)` in
      `app/data/manager.py` (or a small private module-level function in the same file — no new
      file needed for one ~15-line pure function), per data-model.md: uses
      `ccxt.Exchange.parse_timeframe(timeframe)` (static call, no exchange instance) to get period
      duration in seconds, drops the trailing OHLCV row iff
      `row[0] + duration_seconds * 1000 > now_utc_ms`. Handles empty input and
      single-unclosed-element input per the Edge Cases / data-model.md invariants.

**Checkpoint**: Helper exists and is unit-testable in isolation before wiring it in.

## Phase 3: User Story 1 - Alerts reflect a settled market state (Priority: P1) 🎯 MVP

**Goal**: No indicator/informant/crossover ever sees an unclosed candle; repeated cycles with no new
close produce identical results.

**Independent Test**: Run the analysis cycle twice with a mocked/fixed "now," same fetched data, no
new candle closed in between → results identical (this is exactly what the unit + integration tests
below assert, without needing a live exchange).

### Tests for User Story 1 (write first, confirm they fail against current code)

- [X] T004 [P] [US1] Unit tests for `drop_unclosed_candle` in `tests/data/test_manager.py`:
  - closed-only batch → unchanged
  - trailing candle unclosed → trailing candle removed, rest unchanged
  - empty input → unchanged (no-op)
  - single unclosed element → returns empty list
  - parametrized across `candle_period` in `["4h", "1d"]` with boundary timestamps (exactly at
    close, one second before close, one second after close)
- [X] T005 [P] [US1] Integration test in `tests/data/test_manager.py` (or
  `tests/data/test_manager_integration.py`) for `DataManager.get_ohlcv`: stub/mock
  `self.driver.get_historical_data` to return a fixed batch ending in an unclosed candle, freeze
  "now," assert the returned (and cached) series excludes it — proves the wiring, not just the
  helper (contracts/data-manager-get-ohlcv.md Guarantee G1).
- [X] T006 [P] [US1] Regression test reproducing spec Acceptance Scenario 2: call `get_ohlcv` twice
  with the same mocked driver response and no time advance between calls → both results are
  identical (asserts G2, cache consistency, and that trimming is deterministic).

### Implementation for User Story 1

- [X] T007 [US1] Wire `drop_unclosed_candle` into `DataManager.get_ohlcv` in `app/data/manager.py`:
      apply it to the result of `self.driver.get_historical_data(...)` **before**
      `self.cache.set(cache_key, ohlcv, self.TTL_OHLCV)`, using `datetime.now(timezone.utc)` as
      `now_utc` (per Constitution Principle V — UTC only, no `settings.timezone` involved here).
- [X] T008 [US1] Confirm T004-T006 now pass against the wired implementation.
- [ ] T009 [US1] Manual validation per quickstart.md "Manual validation" section against a real (or
      sandbox) exchange connection, for at least one pair on a `4h` `candle_period`, to confirm the
      fix holds outside of mocks.

**Checkpoint**: User Story 1 is independently complete — the repaint bug is fixed and proven by
automated tests plus one manual confirmation.

## Phase 4: User Story 2 - Existing configuration keeps working (Priority: P2)

**Goal**: No `config.yml` schema change; existing operator configs keep working unmodified.

**Independent Test**: Start the bot with `config-clean.yml` copied to `config.yml` (unmodified) and
confirm one full successful analysis + notification cycle.

- [ ] T010 [US2] Code review pass confirming T007's change touches only `app/data/manager.py`
      (already true by construction from Phase 3, since no other file was modified) — record this
      confirmation as a checklist item rather than new code, since FR-004 is satisfied by *not*
      touching config/schema code at all.
- [ ] T011 [US2] Manual validation per quickstart.md "Regression check for existing config
      compatibility": run the bot with a pre-existing `config.yml` (or `config-clean.yml` copied in)
      and confirm a full cycle completes with unchanged notification structure.

**Checkpoint**: Both user stories independently verified; feature is complete.

## Phase 5: Polish & Cross-Cutting

- [X] T012 [P] Update `app/requirements-step-2.txt` — NO change needed (pytest is dev-only, per
      research.md Decision); this task exists only to explicitly confirm that decision was followed
      (i.e., grep `requirements-step-2.txt` for `pytest` and confirm absence).
- [ ] T013 [P] Add a one-line note to `CHANGELOG.md` (if the project maintains one) or the PR
      description (see below) documenting the fix, referencing this spec directory, for future
      `graphify update .` / spec history continuity.
- [X] T014 Run `graphify update .` (or a fresh `graphify . --output graphify-out --code-only` if
      `update` is unavailable) to refresh the dependency graph now that `data/manager.py` changed,
      per the constitution's Development Workflow guidance.

## Dependencies & Execution Order

- **Phase 1 (Setup)** → **Phase 2 (Foundational)**: T003 has no dependency on T001/T002 content but
  T004+ (tests) need `tests/` to exist (T002) and `pytest` available (T001) to run.
- **Phase 2** blocks **Phase 3**: T007 wires the helper built in T003.
- **User Story 1 (Phase 3)** is the MVP and has no dependency on User Story 2.
- **User Story 2 (Phase 4)** depends on Phase 3 being implemented (it validates the *result* of the
  fix causes no config regression) but requires no new production code of its own.
- **Phase 5** runs after both user stories are checkpointed.

## Parallel Execution Notes

- T004, T005, T006 are marked [P] — different test concerns, can be written in parallel (they may
  land in the same file, so "parallel" here means independently authorable/reviewable, not
  necessarily concurrent file edits by multiple agents).
- T001 and T002 [P] — independent setup files.
- T012 and T013 [P] — independent polish items.

## Implementation Strategy

**MVP first**: Complete Phase 1 → Phase 2 → Phase 3 (User Story 1) and stop there if time-boxed —
this alone fixes the constitution-critical bug (Principle II) and is independently shippable/
testable. Phase 4 (User Story 2) is a lower-cost verification pass, not new functionality — do not
skip it, but it will not surface new implementation work if Phase 3 was done correctly (US2's
requirements are satisfied *by construction*, per FR-004, not by additional code).

## Phase 6: Convergence

Assessed 2026-09-28 against spec.md, plan.md, and constitution.md. 6/6 functional requirements
verified by code + automated tests (15/15 passing). 2/4 success criteria verified automatically
(SC-002, SC-004); 2/4 require a live exchange/bot run this environment cannot honestly perform
(SC-001, SC-003 — already covered by T009/T011 above, left unchecked, not fabricated as done).
7/7 constitution principles checked, no violations. No `contradicts` findings.

- [ ] T015 [F1][MEDIUM] Operator: run the bot with a pre-existing `config.yml` against a real (or
      sandbox) exchange for at least one full cycle; confirm no required-field errors and that a
      notification is produced with unchanged structure. Duplicate of T011, kept as an explicit
      convergence-tracked item since it could not be executed in this session.
- [ ] T016 [F2][MEDIUM] Operator: with the bot running, confirm across two consecutive cycles that
      land inside the same unclosed candle (per quickstart.md) that indicator values are identical.
      Duplicate of T009, kept as an explicit convergence-tracked item for the same reason.
- [ ] T017 [F3][LOW] Future slice (not 001): remove leftover `DEBUG:`/commented `logger.debug` lines
      in `app/data/manager.py::get_top_pairs` (lines with `f"DEBUG: ..."` and a commented-out
      `# self.logger.debug(...)`), per Constitution Principle VII. Out of scope for repaint fix;
      tracked here so it is not lost.

**Outcome**: `tasks_appended` — 3 items (2 require operator action outside this session; 1 is
explicitly deferred to a future slice, not a defect in this one).
