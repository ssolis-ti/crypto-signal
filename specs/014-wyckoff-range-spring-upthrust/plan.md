# Implementation Plan: Trading Range, Spring, and Upthrust Detection

**Branch**: `main` | **Date**: 2026-09-28 | **Spec**: `specs/014-wyckoff-range-spring-upthrust/spec.md`
**Blocked on**: `specs/013-wyckoff-effort-result` (consumes `WyckoffPrimitives.relative_volume`)

## Summary

Extend `app/analyzers/indicators/wyckoff.py::WyckoffPrimitives` with `detect_trading_range`,
`detect_springs`, and `detect_upthrusts` — pure functions over an OHLCV DataFrame, each parametrized
(lookback window, break margin, confirmation window) rather than hardcoded, so slice 015's validation
can sweep parameters instead of the code needing to change per experiment.

## Technical Context

Identical to slice 013 (no new dependency, pytest, Docker execution). New logic: rolling min/max for
range, index-scanning break/confirm detection for spring/upthrust.

## Constitution Check

Same PASS table as slice 013 (Principles I, II, III, VI relevant; IV/V/VII N/A). No violations —
this remains a pure, informational, unwired analytical primitive.

## Project Structure

```
app/analyzers/indicators/wyckoff.py       (extended: range/spring/upthrust detection)
tests/analyzers/test_wyckoff.py            (extended)
```
