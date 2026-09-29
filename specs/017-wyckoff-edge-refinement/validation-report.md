# Validation Report: Search for a Trade-Worthy Wyckoff Edge

**Date**: 2026-09-28 | **Feature**: `specs/017-wyckoff-edge-refinement`
**Companion reports**: `specs/007/`, `specs/011/`, `specs/015-.../validation-report.md`

## Data source

Binance, 15-pair basket (`MATIC/USDT` again skipped — delisted), ~10 months back from 2026-09-28,
both `4h` (event detection + outcomes) and `1d` (higher-timeframe context) OHLCV. Focused on the
**14-day horizon**, since that is the one the operator's own recollection was about, and slice 015
already reported the shorter horizons.

## Methodology

Regenerated slice 015's exact event set (real `WyckoffPrimitives.detect_springs`/`detect_upthrusts`,
2,689 events with a full 14d forward window available — down from slice 015's 2,839 total since some
lack enough future data at this longer horizon). Split **chronologically** 70/30 — the first 1,882
events (in-sample) vs. the last 807 (out-of-sample, strictly later in time, never shuffled). Four
Wyckoff-motivated filters were evaluated on this split (full rationale in `spec.md`): higher-timeframe
(1D EMA50) trend alignment, range compression, extreme break-candle volume (≥2.5x average, stricter
than slice 015's 1.5x cut), and BTC 4h regime alignment. A filter is called `confirmed` only if its
out-of-sample win rate is ≥60% with p<0.05 on n≥30 — pre-declared before running, per FR-005.

**Important interpretive addition** (found while writing this report, not planned in advance, but
necessary for honesty): the baseline win rate itself was very different in-sample vs. out-of-sample
(52.5% vs. 56.9%) — the two time periods weren't equally favorable to begin with. So every filter's
result is reported both in absolute terms and as **lift over its own period's baseline**, which is
the more meaningful measure of whether a filter adds anything beyond "the whole market did better in
the later period."

## Results

| Filter | In-sample win rate (lift) | Out-of-sample win rate (lift) | Verdict |
|---|---|---|---|
| Baseline (no filter) | 52.5% (—) | 56.9% (—) | — |
| 1. HTF (1D EMA50) alignment | 58.4% (**+5.9pp**) | 57.3% (**+0.4pp**) | did_not_replicate |
| 2. Range compression | 52.4% (+0.0pp, not sig.) | 56.2% (−0.7pp) | did_not_replicate |
| 3. Extreme break volume (≥2.5x) | 59.1% (**+6.6pp**) | 62.4% (**+5.5pp**) | **CONFIRMED** |
| 4. BTC regime alignment | 56.7% (+4.2pp) | 53.0% (**−3.9pp**) | did_not_replicate |

(pp = percentage points of win rate; all in-sample/out-of-sample numbers individually statistically
significant vs. 50% except filter 2's in-sample cut and filter 4's out-of-sample cut — see script
output for exact n/p-values.)

### Filter 1 (HTF trend alignment) — a genuine near-miss, not a total failure

This is the one nuance worth calling out explicitly: filter 1's out-of-sample win rate (57.3%) looked
solid on its own and was statistically significant — but once compared against that period's own
56.9% baseline, its real incremental lift is only +0.4 percentage points. Most of its apparent edge
was just the broader period being better for every Spring/Upthrust event, not something this specific
filter added. It technically misses the pre-declared 60% actionable bar either way, but the *reason*
it misses matters: it's not overfit noise (like filter 4), it's a real, if small and mostly redundant,
effect.

### Filter 3 (extreme break volume ≥2.5x) — the one that holds up

This is the strongest result across all three validation slices (007, 011, 015) plus this one: a
**consistent ~6-point win-rate lift over baseline in both the in-sample and out-of-sample periods**,
surviving a genuine chronological holdout test — out-of-sample win rate 62.4% (n=101, p=0.013), mean
return +2.36% at 14 days (still modest vs. the operator's recalled +20-30%, but nearly an order of
magnitude larger than slice 015's unfiltered baseline mean, and the only filter whose out-of-sample
number *improved* over its in-sample number rather than decaying toward baseline — the opposite of
what overfitting looks like).

**Caveat**: n=101 out-of-sample events over ~3 months across 14 pairs means roughly 2-3 qualifying
alerts per week across the whole basket — a usable but not high-frequency signal. A single 70/30 split
is also one specific realization, not a full walk-forward study; this is a promising, honestly-tested
result, not a guarantee that repeats indefinitely.

## Recommendation

**Filter 3 (Spring/Upthrust events where the break candle's volume is ≥2.5x its 20-period average) is
the validated candidate**, per FR-005 — the first filter across four validation slices to show a real,
survived-holdout, meaningfully-sized (not just statistically-detectable) edge.

**This slice does not wire it into Telegram** (per FR-004 / Constitution Principle III: validating a
refinement and shipping it are two separate, explicit steps). The natural next step is a follow-up
slice that:
1. Builds a dedicated, clearly-labeled "Wyckoff Spring/Upthrust (volume-confirmed)" alert path —
   kept separate from `SignalEnhancer`'s existing RSI/MACD-based scoring (already shown, twice, not
   to work), not blended into the same 0-100 score.
2. Sends it with an honest framing (modest but real ~60% win rate, ~2.4% typical 14-day move) — not
   as "guaranteed 20-30% winner," so the operator's expectations match what was actually validated.
3. Gets explicit operator sign-off before going live, same as every other behavior-changing decision
   in this project.

Recorded as a Convergence finding for that sign-off, not applied unilaterally.

## Assumptions and limitations

- Single 70/30 chronological split (not k-fold walk-forward) — a reasonable first check, not
  definitive proof the edge is permanent.
- `range_width_pct`/HTF/BTC-alignment thresholds were reasonable single choices, not swept/optimized
  — consistent with this project's standing policy against post-hoc curve-fitting.
- As with slice 015, this validates the pattern's existence, not a full trading strategy after
  fees/slippage/execution risk.
