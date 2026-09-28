# Implementation Plan: Correct btc_change_1h to a Real 1-Hour Percentage Change

**Branch**: `main` | **Date**: 2026-09-28 | **Spec**: `specs/010-btc-change-1h-fix/spec.md`

## Summary

Replace `MarketContext._get_btc_data`'s use of the CCXT ticker's ambiguous `change` field with a real
1-hour percentage change computed from `DataManager.get_ohlcv(exchange, reference_pair, '1h')` (the
same already-injected, already-cached, already-no-repaint-safe data source every indicator uses).
Add `tests/analysis/test_market_context.py` (new package — `MarketContext` had zero tests before this
slice, required by Principle VI).

## Technical Context

**Language/Version**: Python 3.12 (unchanged) | **New Dependencies**: none | **Testing**: pytest,
Docker-based execution as all prior slices | **Constraints**: no new network credential, one
additional cached OHLCV fetch per cycle (5-minute TTL, negligible)

## Constitution Check

| Principle | Check | Result |
|---|---|---|
| I. Read-Only, No Custody | Uses existing `DataManager.get_ohlcv` (public OHLCV), no new exchange surface | PASS |
| II. No Repaint | Reuses `DataManager.get_ohlcv`'s existing no-repaint guarantee (slice 001) rather than reimplementing candle-closure logic | PASS |
| VI. Tests Guard the Core Pipeline | `MarketContext` (`analysis/`) gains its first test coverage, including the specific regression | PASS |
| III/IV/V/VII | Not applicable / unaffected | PASS (N/A) |

No violations.

## Project Structure

```
app/analysis/market_context.py   (_get_btc_data + new _compute_change_1h)
tests/analysis/__init__.py       (new)
tests/analysis/test_market_context.py   (new)
```
