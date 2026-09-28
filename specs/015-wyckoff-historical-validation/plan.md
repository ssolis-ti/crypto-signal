# Implementation Plan: Historical Validation of Wyckoff Spring/Upthrust Signals

**Branch**: `main` | **Date**: 2026-09-28 | **Spec**: `specs/015-wyckoff-historical-validation/spec.md`
**Blocked on**: `specs/014-wyckoff-range-spring-upthrust`

## Summary

Write `validate_wyckoff_springs.py`, reusing slices 007/011's fetch/context/permutation-test
infrastructure, replacing the signal trigger with slice 014's `detect_springs`/`detect_upthrusts`,
and adding two new horizons (7d, 14d = 42/84 four-hour candles) specifically to fact-check the
operator's recollection (HOT → +20-30% over 1-2 weeks). Extend the historical window beyond 10 months
if the initial run's Spring/Upthrust sample size is too small (these events are expected to be rarer
than RSI/MACD triggers).

## Technical Context

Same as slices 007/011 (no new dependency, research artifact outside `app/`, Docker execution). New:
two additional horizons; a note that market-context scoring (`SignalEnhancer`) may or may not be
part of this validation depending on what slice 014 exposes — at minimum, raw forward-return-by-event
statistics (independent of any scoring formula) MUST be reported, since the operator's recollection is
about the raw "HOT alert" outcome, not about a score/quality tier.

## Constitution Check

Same PASS table as slices 007/011 (Principles I, II, III, V, VII relevant). No violations.

## Project Structure

```
specs/015-wyckoff-historical-validation/
├── spec.md
├── plan.md                        (this file)
├── tasks.md
├── validate_wyckoff_springs.py     (new backtest script)
└── validation-report.md           (written after the script runs)
```
