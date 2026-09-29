# Validation Report: Wyckoff Spring/Upthrust Signals

**Date**: 2026-09-28 | **Feature**: `specs/015-wyckoff-historical-validation`
**Constitution reference**: Principle III | **Companion reports**: `specs/007-.../validation-report.md`, `specs/011-.../validation-report.md`

## Data source

Binance, `4h` timeframe, ~10 months back from 2026-09-28, 14-pair basket (BTC/USDT now included
directly rather than held out as a pure reference pair, since this validation does not use
`SignalEnhancer`/market-context scoring — see Methodology). `MATIC/USDT` again returned zero candles
(delisted/renamed) and was skipped, consistent with slices 007/011.

## Methodology

Unlike slices 007/011 (which validated `SignalEnhancer`'s 0-100 score), this validation tests the
**raw Spring/Upthrust price pattern itself** — the real, unmodified
`WyckoffPrimitives.detect_springs`/`detect_upthrusts` (slice 014), with no scoring formula in
between. This matches what the operator's recollection is actually about ("alerta HOT" → price
outcome), not a quality-tier judgment.

For every detected event: recorded `break_relative_volume` (volume at the break candle, relative to
its 20-period average) and `confirm_relative_volume` (same, at the confirmation candle), plus
realized forward returns (direction-normalized: raw for Spring/"hot", negated for Upthrust/"cold") at
**four pre-declared horizons**: 24h, 72h (for comparability with slices 007/011) and **7d, 14d**
(specifically to test the operator's recollection). Events were split into "volume-confirmed"
(`break_relative_volume >= 1.5`, i.e. a break on at least 50% above-average volume — the classic
Wyckoff "effort" signature) vs. not, to test whether that refinement adds predictive power.
Significance was tested two ways: a Spearman-rank permutation test (same method as slices 007/011,
2000 shuffles, seed 42) between `break_relative_volume` and outcome, and — new for this report — a
normal-approximation z-test of each bucket's win rate against a 50% baseline (implemented with
`math.erf`, no `scipy` dependency, same rationale as prior reports).

## Results

**2,839 total events** (1,504 Spring/"hot", 1,335 Upthrust/"cold") across 14 pairs over ~10 months —
by far the largest sample of the three validation slices (007: 642, 011: 1,776).

### Win rate by horizon (ALL events, both directions combined via `expected_dir_return`)

| Horizon | n | mean | median | win rate | z | p-value |
|---|---|---|---|---|---|---|
| 24h | 2827 | +0.09% | +0.23% | 53.6% | +3.82 | **0.0001** |
| 72h | 2813 | +0.18% | +0.52% | 54.8% | +5.11 | **<0.0001** |
| 7d | 2777 | +0.09% | +0.42% | 52.6% | +2.75 | **0.0059** |
| 14d | 2689 | +0.49% | +0.84% | 53.8% | +3.95 | **0.0001** |

**Every horizon's win rate is statistically significantly above 50%** — the first time in this
project's three validation slices (007, 011, 015) that a raw signal shows a robust, positive
directional edge rather than "no effect" (007) or a significant *adverse* effect (011).

### Volume confirmation (break_relative_volume >= 1.5) — does it help?

| Horizon | Volume-confirmed win rate | Not-confirmed win rate | Which is better? |
|---|---|---|---|
| 24h | 52.9% (p=0.040) | 54.2% (p=0.001) | not-confirmed, slightly |
| 72h | 56.9% (p<0.0001) | 53.0% (p=0.017) | confirmed |
| 7d | 52.6% (p=0.060, not sig.) | 52.6% (p=0.044) | ~tied |
| 14d | 54.7% (p=0.001) | 53.0% (p=0.021) | confirmed, slightly |

Mixed and inconsistent — sometimes the volume-confirmed bucket does slightly better (72h, 14d),
sometimes slightly worse or tied (24h, 7d). The direct correlation test between
`break_relative_volume` (continuous) and outcome is **not significant at any horizon**
(p ranges 0.40–0.87) — the win-rate edge exists in the raw Spring/Upthrust pattern overall, but this
specific volume-confirmation refinement does not reliably sharpen it in this sample.

## Fact-check: the operator's recollection

> "La versión antigua mostraba alerta de potenciales HOT y luego de una semana o 2 el precio de los
> token subían un 20%-30%."

| Horizon | Mean (HOT only) | Median (HOT only) | % of events landing in the 20-30% range |
|---|---|---|---|
| 7d | +0.25% | +0.07% | 2.6% |
| 14d | +0.85% | +0.51% | 3.9% |

**This does not replicate.** The typical (mean/median) move 1-2 weeks after a Spring event in this
sample is a small fraction of a percent — two orders of magnitude below the recalled 20-30%. Only
about 3-4% of individual events happened to land in that range at all (some events surely did move
that much — crypto is volatile — but that is expected noise in a 1,500-event sample, not a typical or
reliable outcome). The recollection likely reflects a small number of memorable, large winners (or a
different bot version's different signal logic) rather than the pattern's typical behavior.

## Comparison to slices 007 and 011

| | RSI (007) | macd_cross (011) | Spring/Upthrust (015) |
|---|---|---|---|
| Sample size | 642 | 1,776 | 2,839 |
| Win rate vs 50% | ~52% (not tested for significance) | ~43-52% (n/a, correlation-based) | **52.6%-54.8%, significant at every horizon** |
| Score/pattern correlates with outcome? | No (p=0.36-0.87) | **Yes, negatively** (p=0.0055 at 72h) | No significant correlation with volume-confirmation (p=0.40-0.87) |
| Typical magnitude | Small (<1%) | Small (<1%) | Small (<1%) |

**This is a genuinely different result from 007/011**: for the first time, a raw signal (not a scored
one) shows a real, statistically robust directional edge. But it is a small edge (53-55% win rate,
not the "clearly better" signal a 20-30% move would imply), and — critically — it does **not**
confirm the operator's specific magnitude recollection.

## Recommendation

This is a **Convergence finding requiring operator decision**, not a unilateral next step, because
the result is genuinely mixed:

- **In favor of continuing to slice 016** (multi-timeframe integration): the raw win-rate edge is
  real and statistically significant across all four horizons — the first such finding in this
  project. `specs/016-wyckoff-multiframe-integration/spec.md`'s FR-002 gate ("blocked unless slice
  015 shows a real, statistically credible effect") is arguably satisfied on the win-rate criterion.
- **Against over-investing further**: the effect size is small (a ~3-5 point edge over a coin flip),
  volume-confirmation doesn't sharpen it, and the magnitude the operator specifically recalled does
  not replicate — so slice 016 should not be framed as "chasing the 20-30% pattern," which this data
  says isn't the typical outcome.

**Recorded here for operator sign-off, per FR-006**: (a) proceed to slice 016 treating the modest,
validated win-rate edge as the actual (smaller, more realistic) basis for a filter — not the
remembered magnitude; (b) hold and look for a stronger/more specific pattern before investing in
multi-timeframe integration; (c) something else. No `SignalEnhancer` or `notify_all` change made by
this slice either way.

## Assumptions and limitations

- 14-pair/~10-month/single-exchange snapshot, same scope as slices 007/011.
- `break_relative_volume >= 1.5` as the "volume-confirmed" threshold was chosen before running (not
  tuned after seeing results), but is still just one reasonable choice — a different threshold might
  show a cleaner (or muddier) split; not swept/optimized here to avoid post-hoc curve-fitting.
- This validates the pattern's *existence* as a directional edge, not any specific trading strategy
  (position sizing, stop placement, fees/slippage are all out of scope) — a 53% win rate with small
  average magnitude is a research finding, not by itself evidence of a profitable strategy after
  costs.
