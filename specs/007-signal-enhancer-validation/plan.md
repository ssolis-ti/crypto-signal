# Implementation Plan: Historical Validation of the SignalEnhancer Score/Quality Heuristic

**Branch**: `main` | **Date**: 2026-09-28 | **Spec**: `specs/007-signal-enhancer-validation/spec.md`

## Summary

Write and run a standalone backtest script that replays the bot's real production RSI signal trigger
(hot: RSI<30, cold: RSI>70, 4h candles) over real historical Binance data for a basket of liquid
USDT pairs, scores each occurrence with the actual `SignalEnhancer._calculate_score`, measures
realized forward returns, and reports whether the score/quality tier predicts anything real. Document
methodology, assumptions, and results in `validation-report.md`. Based on the result, either confirm
the current `detail_min_quality: 'A'` gate is evidence-based, or take the action FR-009 specifies.

## Technical Context

**Language/Version**: Python 3.11 (Dockerfile base image, unchanged)
**Primary Dependencies**: `ccxt` (already required, read-only `fetch_ohlcv`/`fetch_ticker`-equivalent
historical calls), `pandas`, `talib` (already required), `numpy` (already required, used for a
permutation-test p-value so no new `scipy` dependency is introduced)
**Testing**: N/A for the script itself (SC-003) — it is a research artifact, not application code
**Target Platform**: run once, interactively, inside the `crypto-signal:dev` Docker image (network
access confirmed) — not deployed, not scheduled
**Constraints**: read-only exchange access only (Principle I); no new pinned dependency in
`requirements-step-2.txt` (Principle VII) since only already-present libraries are used
**Scale/Scope**: 1 script (~150-250 lines), 1 report; basket of ~12-15 liquid USDT pairs; ~8-12 months
of 4h candles per pair

## Constitution Check

| Principle | Check | Result |
|---|---|---|
| I. Read-Only, No Custody | Only `fetch_ohlcv` (public market data) is called; no orders, no keys | PASS |
| II. No Repaint | Script re-derives each historical signal only from data up to and including its own candle (FR-003); no lookahead | PASS |
| III. Validate Before You Trust a Heuristic | This slice's entire purpose | PASS |
| IV. Secrets Never in VCS/Image | No credentials needed for public OHLCV data | PASS |
| V. UTC Internally | Historical timestamps handled via `pandas.to_datetime(..., unit='ms', utc=True)`, same pattern as slices 002/003/006 | PASS |
| VI. Tests Guard the Core Pipeline | N/A — this is a one-time research script, not a pipeline component (SC-003) | PASS (N/A) |
| VII. Pinned Deps, No Permanent Debug Logging | No new dependency added; script prints results once, not permanent application logging | PASS |

No violations.

## Project Structure

### Documentation (this feature)

```
specs/007-signal-enhancer-validation/
├── spec.md
├── checklists/requirements.md
├── plan.md                 (this file)
├── research.md
├── data-model.md
├── quickstart.md
├── tasks.md
├── validate_signal_enhancer.py   (the backtest script itself, kept with its report)
└── validation-report.md    (results — written after the script runs)
```

**Structure Decision**: The script lives inside the spec directory, not `app/`, since it is a one-time
research artifact rather than application code (consistent with Assumptions in spec.md). It imports
from `app/` (via `PYTHONPATH`) to reuse the real `SignalEnhancer`, `MarketContextData`, and
`AltStrengthData` — never reimplementing the scoring formula.

## Complexity Tracking

*No entries — no constitution violations.*
