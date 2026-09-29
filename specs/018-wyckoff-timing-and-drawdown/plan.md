# Implementation Plan: Timing and Drawdown Risk of the Extreme-Volume Wyckoff Signal

**Branch**: `main` | **Date**: 2026-09-28 | **Spec**: `specs/018-wyckoff-timing-and-drawdown/spec.md`

## Summary

Write `analyze_wyckoff_timing.py`: regenerate slice 017's confirmed-filter event set (extreme
break-candle volume ≥2.5x), fetch real 1h OHLCV for the 14-day window following each event's
confirmation candle, compute the cumulative-return checkpoint curve plus MAE/MFE per event, and
report the aggregated timing/drawdown picture with an explicit resolution-boundary disclaimer
(FR-005).

## Technical Context

Same as prior validation slices (no new dependency, research artifact outside `app/`, Docker
execution). New: 1h OHLCV fetch (finer than the 4h used elsewhere), and path-dependent metrics
(cumulative-return-at-checkpoint, MAE, MFE) rather than a single end-of-window return.

## Constitution Check

Same PASS table as slices 007/011/015/017 (Principles I, II, III, V, VII relevant). FR-006
reinforces Principle III: characterizing risk/timing is not the same decision as wiring a live alert.

## Project Structure

```
specs/018-wyckoff-timing-and-drawdown/
├── spec.md
├── plan.md                       (this file)
├── tasks.md
├── analyze_wyckoff_timing.py      (new script)
└── validation-report.md          (written after the script runs)
```
