# Tasks: Test Coverage for Untested Pure-Logic Core Modules

**Input**: Design documents from `specs/004-core-pipeline-test-coverage/`

**Tests**: This entire slice IS the test work — no separate "tests first" phase, since there is no
production code change to test-drive (FR-006).

## Phase 1: Setup

- [X] T001 [P] Create `tests/data/test_pair_resolver.py` module (uses existing `tests/data/__init__.py`).

## Phase 2: User Story 1 - CrossOver detection (P1)

- [X] T002 [US1] `tests/analyzers/test_crossover.py`: hot cross, cold cross, NaN-row dropping,
      multi-config-index column suffixing (FR-001).

## Phase 3: User Story 2 - PairResolver mode selection (P1)

- [X] T003 [US2] `tests/data/test_pair_resolver.py`: manual-mode precedence, dynamic/volume mode with
      exclusion + top_n, `data_manager=None` guard, unconfigured fallback, unsupported-source fallback
      (FR-002).

## Phase 4: User Story 3 - NotificationQueue prioritization/dedup (P1)

- [X] T004 [US3] `tests/notifications/test_queue.py`: quality filtering, priority ordering, duplicate
      detection/`is_update`, `process_all` send-loop + per-item exception isolation (FR-003).

## Phase 5: User Story 4 - SmartNotificationManager formatting/gating (P2)

- [X] T005 [US4] `tests/notifications/test_smart.py`: market-scan header, actionable header,
      `max_c_signals` truncation, `finalize_cycle` detail/chart gating, `clear_cycle` reset (FR-004).

## Phase 6: User Story 5 - ConfigValidator (P3)

- [X] T006 [US5] `tests/notifications/test_validator.py`: all-present, one-missing, no-`required`-key
      cases (FR-005).

## Phase 7: Polish

- [X] T007 Run full suite inside `crypto-signal:dev` Docker image; confirm 31 existing + new tests all
      pass (SC-001).
- [X] T008 [P] Run `graphify . --output graphify-out --code-only && graphify cluster-only graphify-out`
      to refresh the project graph.

## Dependencies & Execution Order

T001 → T002/T003/T004/T005/T006 (independent, parallelizable across files) → T007 → T008.

## Phase 8: Convergence

Assessed 2026-09-28. 8/8 functional requirements (FR-001 through FR-008) verified by code + tests.
27 new tests added (5 crossover, 6 pair_resolver, 6 queue, 7 smart, 3 validator); full suite now
58/58 passing (31 prior + 27 new), zero regressions. All 3 success criteria (SC-001/002/003) met:
zero network/credential dependence, every FR has a corresponding assertion. 7/7 constitution
principles checked, no violations — this slice added zero production-code changes (FR-006).
No new bugs found in the tested logic during test-writing; `notifications/core.py` and the
`analyzers/indicators/*`/`analyzers/informants/*` TA modules remain explicitly out of scope
(FR-008) and are candidates for a future slice.

**Outcome**: `converged` — no additional tasks appended.
