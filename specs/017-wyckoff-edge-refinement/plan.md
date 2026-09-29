# Implementation Plan: Search for a Trade-Worthy Wyckoff Edge

**Branch**: `main` | **Date**: 2026-09-28 | **Spec**: `specs/017-wyckoff-edge-refinement/spec.md`

## Summary

Write `search_wyckoff_edge.py`: regenerate slice 015's exact event set (same
`detect_springs`/`detect_upthrusts`, same basket/horizons), enrich each event with four
Wyckoff-motivated context fields (1D EMA trend alignment, range compression at the break,
break-candle `is_climax`, BTC 4h regime alignment), then evaluate each as a candidate filter using a
strict chronological 70/30 in-sample/out-of-sample split — reporting every candidate's in-sample AND
out-of-sample numbers, honestly, whether or not it held up.

## Technical Context

Same as slices 007/011/015 (no new dependency, research artifact outside `app/`, Docker execution).
New: a small local `find_break_index` helper (reconstructs which candle triggered a confirmed
event, using the same support/resistance arrays `WyckoffPrimitives.detect_trading_range` already
computes) so `is_climax` can be evaluated at the actual break candle without modifying slice
013/014's frozen `app/` code.

## Constitution Check

Same PASS table as slices 007/011/015 (Principles I, II, III, V, VII relevant). FR-004 explicitly
reinforces Principle III at a second level: even a filter that survives this slice's own
out-of-sample check is not wired into any live path here — that is an explicit follow-up slice's job.

## Project Structure

```
specs/017-wyckoff-edge-refinement/
├── spec.md
├── plan.md                    (this file)
├── tasks.md
├── search_wyckoff_edge.py      (new backtest/search script)
└── validation-report.md       (written after the script runs)
```
