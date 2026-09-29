# Validation Report: 1D/4h Structural Confluence and Existing-TA Confirmation

**Date**: 2026-09-28 | **Feature**: `specs/019-wyckoff-confluence-and-ta-confirmation`
**Companion reports**: `specs/017-.../validation-report.md`, `specs/018-.../validation-report.md`

## Data source

Same 14-pair basket (`MATIC/USDT` excluded), ~10 months, Binance 4h + 1D real OHLCV. Base population:
slice 017's already-validated 330 confirmed extreme-break-volume events, 321 with a complete 14-day
forward return.

## Methodology

Answers the operator's fractal-timeframe question with one bounded, pre-declared hypothesis instead
of sweeping all nine mentioned timeframes (1M/1W/1D/8h/4h/2h/1h/30m/15m) — see `spec.md` for why a
full sweep would repeat the multiple-comparisons risk this project has consistently guarded against.
Three candidates, each evaluated with the same chronological 70/30 in-sample/out-of-sample split and
lift-over-baseline framing slice 017 established:

1. **1D/4h structural confluence**: a same-direction Spring/Upthrust confirmed on 1D (real
   `WyckoffPrimitives` detection) within ±3 days of the 4h event.
2. **RSI(14) extremity** (<35 for hot / >65 for cold) at the 4h confirmation candle — reusing
   `talib.RSI`, the same library every live indicator already uses.
3. **ADX(14) ≥ 25** ("strong trend," a standard threshold) at the confirmation candle.

## Results

| Filter | In-sample win rate (lift) | Out-of-sample win rate (lift) | Verdict |
|---|---|---|---|
| Baseline (slice 017 filter alone) | 58.9% (—) | 62.9% (—) | — |
| 1. 1D/4h confluence (140/321 events had it) | 60.4% (+1.5pp) | 55.1% (**−7.8pp**) | did_not_replicate |
| 2. RSI extremity aligned | 57.1% (−1.8pp) | 48.6% (**−14.3pp**) | did_not_replicate |
| 3. ADX(14) ≥ 25 | 57.6% (−1.4pp) | 59.4% (−3.5pp) | did_not_replicate |

**None of the three held up.** All three either added nothing or made the out-of-sample result
*worse* than the unfiltered slice 017 baseline — most strikingly RSI extremity, which drags
out-of-sample win rate down to 48.6% (below a coin flip) despite looking roughly neutral in-sample.
This is consistent with slice 007's original finding that RSI extremity alone is not predictive; this
report extends that conclusion to "RSI extremity does not add value even as a secondary filter on
top of an already-validated signal."

## Answering the operator's original question directly

**"¿Qué mejoras habría al usar fractales en la misma moneda con diferentes temporalidades? ¿Se ve
algún detalle o correlación?"** — Tested the most theoretically-motivated version of that idea (true
structural recurrence, not just "is the higher timeframe trending the right way," which slice 017
already found weak): **no, in this sample, 1D/4h confluence does not strengthen the signal — if
anything it produced a worse out-of-sample result** (fewer, not better, qualifying events: only 140/
321 base events had confluence at all, and that subset underperformed the full set out-of-sample).
Combined with slices 007, 011, and this slice's RSI/ADX results, the pattern across this entire
project is consistent: **classic technical indicators and cross-timeframe trend/pattern alignment do
not add value on top of what the raw extreme-volume Wyckoff signal already captures** — the volume
signature at the break candle itself remains the only validated, holdout-tested edge found so far.

## Recommendation

This does not change the pending operator decision from slices 017/018 — it removes three specific
candidate refinements from consideration (they were tested honestly and did not hold up), leaving
slice 017's extreme-volume filter, characterized by slice 018's timing/drawdown profile, as the
single validated basis for any future Telegram alert. No further filter-search slices are recommended
using this same event population and these same tools — continuing to test more candidates against
the same 321-event dataset would itself start to risk the multiple-comparisons problem this slice
was designed to avoid.

If the operator wants to continue searching for a sharper edge, the more promising directions are
either (a) a genuinely different data source (order-flow/order-book imbalance, which this project's
OHLCV-only data cannot see), or (b) accepting slice 017's validated edge as final and moving to the
implementation/framing decision instead of further refinement.

## Assumptions and limitations

Same as slices 017/018 (single historical window, thresholds chosen once and not swept, no
trading-cost/slippage modeling).
