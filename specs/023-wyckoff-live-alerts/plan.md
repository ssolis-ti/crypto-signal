# Implementation Plan: Live Wyckoff Spring/Upthrust Telegram Alerts

**Branch**: `main` | **Date**: 2026-09-29 | **Spec**: `specs/023-wyckoff-live-alerts/spec.md`

## Summary

Add `app/analysis/wyckoff_alerts.py::WyckoffAlerter`, wired into `Behaviour.run()` right after
historical data collection (reusing the already-fetched `4h` OHLCV, no new exchange calls). On a
confirmed Spring/Upthrust with `break_relative_volume >= 2.5` on the last closed candle, sends one
dual-framed Telegram message via a new `Notifier.send_direct_text()` method — bypassing
`SignalEnhancer`/`SmartNotificationManager` entirely. Gated by `settings.wyckoff_alerts.enabled`
(default `false` in `defaults.yml`; `true` in the operator's own `config.yml`/`config-clean.yml`).

## Technical Context

**Language/Version**: Python 3.12 (unchanged) | **New Dependencies**: none | **Testing**: pytest,
Docker-based execution as all prior slices, plus one live-cycle smoke test (SC-002) against the
running bot.

## Constitution Check

| Principle | Check | Result |
|---|---|---|
| I. Read-Only, No Custody | Pure alerting on already-fetched public OHLCV; no new exchange/order surface | PASS |
| II. No Repaint | Reuses `DataManager.get_ohlcv`'s existing no-repaint guarantee (slice 001) — checks only the already-trimmed last candle, no new candle-freshness logic | PASS |
| III. Validate Before You Trust a Heuristic | This is exactly the "build" step Principle III gates on validation for — slice 017 provided that validation (holdout-tested), and FR-003 keeps this path independent of the still-unvalidated `SignalEnhancer` score | PASS |
| IV. Secrets Never in VCS/Image | No new secret surface; reuses existing Telegram client/credentials | PASS |
| V. UTC Internally | Dedup keys use the OHLCV DataFrame's existing UTC-aware index (from `IndicatorUtils.convert_to_dataframe`, slice 002) | PASS |
| VI. Tests Guard the Core Pipeline | New `analysis/` module gets full test coverage from day one (FR-007) | PASS |
| VII. Pinned Deps, No Permanent Debug Logging | No new dependency; normal `logger.info`/`logger.error`, no debug-investigation prints left behind | PASS |

No violations. This is the first slice in the Wyckoff arc with real blast radius (an actual new
Telegram message type for the operator) — everything upstream (013-022) was deliberately built to
have none.

## Project Structure

```
app/analysis/wyckoff_alerts.py       (new: WyckoffAlerter)
app/notifications/core.py            (add: Notifier.send_direct_text)
app/behaviour/core.py                (wire: construct + call WyckoffAlerter)
app/defaults.yml                     (add: settings.wyckoff_alerts.enabled: false)
config-clean.yml                     (add: settings.wyckoff_alerts.enabled: true, documented)
config.yml                           (operator's own: enabled: true)

tests/analysis/test_wyckoff_alerts.py   (new)
```
