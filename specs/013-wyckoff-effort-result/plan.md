# Implementation Plan: Wyckoff Effort-vs-Result Primitives

**Branch**: `main` | **Date**: 2026-09-28 | **Spec**: `specs/013-wyckoff-effort-result/spec.md`

## Summary

Add `app/analyzers/indicators/wyckoff.py::WyckoffPrimitives`, a static-method class (same shape as
the existing `DerivedIndicators`) computing `relative_volume`, `relative_range`,
`effort_result_ratio`, `is_climax`, and `is_thin_move` from a pandas OHLCV DataFrame. Pure functions,
no config.yml wiring, no alert generation — the foundational primitive slices 014/015 build on.

## Technical Context

**Language/Version**: Python 3.12 (unchanged) | **New Dependencies**: none (`pandas`/`numpy`/`talib`
already pinned) | **Testing**: pytest, Docker-based execution as all prior slices

## Constitution Check

| Principle | Check | Result |
|---|---|---|
| I. Read-Only, No Custody | Pure computation over already-fetched OHLCV; no new exchange/order surface | PASS |
| II. No Repaint | Operates on whatever OHLCV it's given — same no-repaint contract as `DataManager.get_ohlcv` already provides upstream; this slice adds no new candle-freshness logic | PASS |
| III. Validate Before You Trust a Heuristic | Explicitly informational-only per FR-005; no gating happens until slice 015 validates it | PASS |
| VI. Tests Guard the Core Pipeline | New analytical surface gets full test coverage from day one (FR-006) | PASS |
| IV/V/VII | Not applicable / unaffected | PASS (N/A) |

No violations.

## Project Structure

```
app/analyzers/indicators/wyckoff.py       (new: WyckoffPrimitives)
tests/analyzers/test_wyckoff.py            (new)
```
