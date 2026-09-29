# Implementation Plan: 1D/4h Structural Confluence and Existing-TA Confirmation

**Branch**: `main` | **Date**: 2026-09-28 | **Spec**: `specs/019-wyckoff-confluence-and-ta-confirmation/spec.md`

## Summary

Write `test_confluence_and_ta.py`: regenerate slice 017's confirmed extreme-volume 4h event set
(330 events), enrich each with (a) a same-direction 1D Spring/Upthrust confluence flag (±3-day
window, real `WyckoffPrimitives` on 1D data), (b) RSI(14) extremity at the confirmation candle, (c)
ADX(14) at the confirmation candle — then evaluate all three with the same chronological 70/30
in-sample/out-of-sample split and lift-over-baseline framing slice 017 established.

## Technical Context

Same as slices 007/011/015/017/018 (no new dependency — `talib.ADX`/`talib.RSI` already used
elsewhere in `app/analyzers/indicators/`, research artifact outside `app/`, Docker execution).

## Constitution Check

Same PASS table as prior validation slices (Principles I, II, III, V, VII relevant). FR-005
reinforces Principle III. No violations.

## Project Structure

```
specs/019-wyckoff-confluence-and-ta-confirmation/
├── spec.md
├── plan.md                        (this file)
├── tasks.md
├── test_confluence_and_ta.py       (new script)
└── validation-report.md           (written after the script runs)
```
