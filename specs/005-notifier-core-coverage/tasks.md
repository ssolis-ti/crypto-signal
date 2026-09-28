# Tasks: Test Coverage for notifications/core.py::Notifier

**Input**: Design documents from `specs/005-notifier-core-coverage/`

## Phase 1: Setup

- [X] T001 [P] Confirm `TelegramNotifier`/`WebhookNotifier`/`StdoutNotifier` constructors are I/O-free
      (read source, documented in research.md).

## Phase 2: User Story 1 - Notifier initialization (P1)

- [X] T002 [US1] `tests/notifications/test_core.py`: telegram-only, missing-required-field,
      all-three-configured, and empty-config initialization cases (FR-001).

## Phase 3: User Story 2 - Webhook chart_file bug fix (P1)

### Test first (characterizes the bug before the fix)

- [X] T003 [US2] `tests/notifications/test_core.py`: `notify_webhook` forwards `chart_file`
      (both `None` and a real path) to the underlying client's `notify` call.

### Implementation

- [X] T004 [US2] Fix `app/notifications/core.py::notify_webhook` to call
      `self.webhook_clients[notifier].notify(message, chart_file)` (FR-002).
- [X] T005 [US2] Confirm T003 passes.

## Phase 4: User Story 3 - Telegram send paths (P1)

- [X] T006 [US3] `tests/notifications/test_core.py`: `notify_telegram` chart-fallback-on-exception,
      `_send_telegram_queued` UPDATE prefix, `_send_smart_text` str-vs-dict branching,
      `_send_smart_chart` chart-then-text fallback and double-failure containment (FR-003).

## Phase 5: User Story 4 - notify_all routing (P2)

- [X] T007 [US4] `tests/notifications/test_core.py`: stdout-only routing, telegram-only routing via
      smart manager, `enable_charts=False` gating of `create_charts` (FR-004).

## Phase 6: Polish

- [X] T008 Run full suite inside `crypto-signal:dev` Docker image; confirm 58 existing + new tests all
      pass (SC-001).
- [X] T009 [P] Refresh Graphify project graph.

## Dependencies & Execution Order

T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009.

## Phase 7: Convergence

Assessed 2026-09-28. 7/7 functional requirements (FR-001 through FR-007) verified by code + tests.
19 new tests added; full suite now 77/77 passing (58 prior + 19 new), zero regressions. SC-002
directly verified: reverted the fix via `git stash`, confirmed all 3 webhook tests failed with the
exact predicted `TypeError`, then restored the fix and confirmed they pass. SC-003 met — zero
network/credential dependence (only client `__init__` runs for real; all outbound methods are
recording stubs). 7/7 constitution principles checked, no violations. One production fix landed
(`notify_webhook` forwarding `chart_file`), scoped exactly to FR-002/FR-006. No new out-of-scope
findings; `MessageBuilder.build_indicator_messages` and the TA modules remain deferred (FR-007).

**Outcome**: `converged` — no additional tasks appended.
