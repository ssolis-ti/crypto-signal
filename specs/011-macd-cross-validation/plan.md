# Implementation Plan: Historical Validation of the SignalEnhancer Score for macd_cross

**Branch**: `main` | **Date**: 2026-09-28 | **Spec**: `specs/011-macd-cross-validation/spec.md`

## Summary

Write a new backtest script, `validate_macd_cross.py`, reusing slice 007's basket/date-range/context-
reconstruction/scoring/aggregation/significance-test decisions unchanged, but replacing the RSI
threshold-crossing trigger with `app/analyzers/indicators/macd_cross.py`'s exact MACD/signal-line
crossing condition. Run it, write `validation-report.md`, compare explicitly to slice 007's RSI
result, and apply the same FR-008 discipline (no unilateral behavior change) to any recommendation.

## Technical Context

Identical to slice 007's Technical Context (same dependencies, same execution environment, same
"research artifact, not application code" scope) — not restated. The only new logic is MACD/signal
crossover event detection, replicated from `app/analyzers/indicators/macd_cross.py`.

## Constitution Check

Identical PASS table to slice 007 (Principles I, II, III, V, VII relevant; same reasoning). No
violations.

## Project Structure

```
specs/011-macd-cross-validation/
├── spec.md
├── checklists/requirements.md
├── plan.md                    (this file)
├── research.md
├── tasks.md
├── validate_macd_cross.py     (new backtest script)
└── validation-report.md       (written after the script runs)
```
