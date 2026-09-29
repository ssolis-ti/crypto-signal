# Implementation Plan: Taker Buy/Sell Flow as a Wyckoff Refinement

**Branch**: `main` | **Date**: 2026-09-28 | **Spec**: `specs/021-wyckoff-taker-flow/spec.md`

## Summary

Write `test_taker_flow.py`: regenerate slice 017's confirmed extreme-volume 4h event set, but fetch
the underlying 4h OHLCV via Binance's raw `publicGetKlines` (not CCXT's unified `fetch_ohlcv`) to
recover `taker_buy_base_volume` per candle. Compute `taker_buy_ratio` at each event's break candle
and test both pre-declared hypotheses (absorption vs. aggressive-entry) with the same 70/30
chronological in-sample/out-of-sample split and lift-over-baseline framing as slices 017/019.

## Technical Context

Same as prior validation slices (no new dependency — `ccxt`'s `publicGetKlines` raw-endpoint access
is already part of the pinned `ccxt` package; research artifact outside `app/`; Docker execution).

## Constitution Check

Same PASS table as slices 007/011/015/017/018/019 (Principles I, II, III, V, VII relevant). FR-004
reinforces Principle III. No violations — read-only public market data, no new credential surface.

## Project Structure

```
specs/021-wyckoff-taker-flow/
├── spec.md
├── plan.md                (this file)
├── tasks.md
├── test_taker_flow.py       (new script)
└── validation-report.md    (written after the script runs)
```
