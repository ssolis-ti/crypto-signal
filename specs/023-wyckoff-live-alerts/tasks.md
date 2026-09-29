# Tasks: Live Wyckoff Spring/Upthrust Telegram Alerts

## Phase 1: Tests first

- [X] T001 `tests/analysis/test_wyckoff_alerts.py`: confirmed Spring fixture → one alert sent with
      both framing sections and correct numbers; confirmed Upthrust mirror; repeated cycle on the
      same confirming candle → no duplicate; disabled config → never alerts; insufficient history →
      no-op, no exception; injected detection exception → caught, logged, no propagation; wrong
      candle period (not `4h`) → not checked (FR-001 through FR-007).

## Phase 2: Implementation

- [X] T002 `app/notifications/core.py`: add `Notifier.send_direct_text(message)` — loops
      `telegram_clients`, calls `send_messages([message])`, catches/logs per-client errors (FR-003).
- [X] T003 `app/analysis/wyckoff_alerts.py`: `WyckoffAlerter` — detection via real
      `WyckoffPrimitives`, dual-framed message construction with the exact slices 017/018 numbers,
      in-memory dedup keyed on (exchange, pair, direction, candle timestamp) (FR-001, FR-002, FR-004,
      FR-006).
- [X] T004 `app/behaviour/core.py`: construct `WyckoffAlerter` in `__init__` (reading
      `config.settings.get('wyckoff_alerts', {})`), call `check_and_alert` per pair's `4h` data
      (if present) right after historical data collection in `run()` (FR-005).
- [X] T005 `app/defaults.yml`: add `settings.wyckoff_alerts.enabled: false`.
- [X] T006 `config-clean.yml` and the operator's own `config.yml`: add
      `settings.wyckoff_alerts.enabled: true`, documented.
- [X] T007 Confirm T001 passes.

## Phase 3: Verification

- [X] T008 Run full suite inside `crypto-signal:dev` Docker image; confirm all existing + new tests
      pass (SC-001).
- [X] T009 Rebuild image, redeploy (`docker compose up -d --build`), confirm the feature is live and
      does not crash the analysis cycle (SC-002) — a real qualifying event is not guaranteed within
      the observation window, so absence of a message is not itself a failure; absence of errors and
      correct message content IF one fires are what's checked.
- [X] T010 `grep` the message-building code for the exact validated numbers (SC-003).
- [X] T011 [P] Refresh Graphify project graph.

## Phase 4: Convergence

Assessed 2026-09-29. 7/7 functional requirements verified by code + tests. 11 new tests added; full
suite now 155/155 passing (144 prior + 11 new), zero regressions. SC-001 met. SC-002 verified live:
rebuilt image, redeployed, ran a full real cycle against 20 pairs — zero errors, zero exceptions,
container stayed healthy, worker completed and slept normally. No qualifying event occurred this
particular cycle (expected — slice 018 found ~330 events over 10 months across 14 pairs, roughly one
per pair every couple of weeks, so a silent cycle is the normal case, not a failure). SC-003 verified
directly via grep: the exact validated numbers (72-78%, 64%, +2.84%, ≥10%) are present in the message-
building code. 7/7 constitution principles checked, no violations. This is the first slice in the
Wyckoff arc (012-023) with real live blast radius — deliberately gated by `wyckoff_alerts.enabled`
(default `false`, operator's own `config.yml` set to `true`) and kept fully independent of
`SignalEnhancer`/`SmartNotificationManager` (FR-003).

**Outcome**: `converged` — no additional tasks appended. The bot is now live with the operator's
chosen dual-framed alert for the one edge validated across specs/017-022's entire investigation.
