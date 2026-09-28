# Validation Report: SignalEnhancer Score/Quality Heuristic — macd_cross Signals

**Date**: 2026-09-28 | **Feature**: `specs/011-macd-cross-validation`
**Constitution reference**: Principle III | **Companion report**: `specs/007-signal-enhancer-validation/validation-report.md`

## Data source

Identical to slice 007: Binance, `4h` timeframe, ~10 months back from 2026-09-28, reference pair
`BTC/USDT`, basket of 13 usable pairs (`MATIC/USDT` again returned zero candles — delisted/renamed,
same as slice 007, automatically skipped).

## Methodology

Identical to slice 007 (see that report for the full methodology, reused unchanged here) except for
the signal trigger: instead of RSI crossing 30/70, this validation detects the **exact** condition
`app/analyzers/indicators/macd_cross.py::MACDCross.analyze` uses — MACD(12,26,9) line crossing its
signal line — implemented as a MACD-histogram sign change (mathematically identical, see
`specs/011-macd-cross-validation/research.md`). One event per crossing, no lookahead. Same
context reconstruction, same real `SignalEnhancer._calculate_quality` call, same two pre-declared
horizons (24h/72h), same permutation-test significance check (2000 shuffles, seed 42).

## Results

**1,776 total events** (882 hot, 894 cold) across 13 pairs over ~10 months — nearly 3x slice 007's
RSI sample size (MACD crosses occur far more often than RSI threshold crossings).

Quality tier distribution: **C: 667, B: 568, A: 541, A+: 0.** Unlike slice 007's RSI validation
(where only 12 `A`-tier events occurred), macd_cross produces a substantial `A`-tier sample here —
enough to draw a real conclusion about that tier specifically, not just note "insufficient sample."

### Horizon 24h (n=1770)

| Tier | n | mean | median | win rate |
|---|---|---|---|---|
| A+ | 0 | — | — | — (insufficient sample) |
| A | 536 | +0.27% | +0.05% | 50.4% |
| B | 568 | **-0.46%** | -0.37% | **42.8%** |
| C | 666 | +0.28% | +0.13% | 51.8% |

Spearman-rank correlation(score, expected_dir_return_24h) = **-0.0226**, permutation p-value =
**0.3103** (not significant).

### Horizon 72h (n=1754)

| Tier | n | mean | median | win rate |
|---|---|---|---|---|
| A+ | 0 | — | — | — (insufficient sample) |
| A | 536 | **-0.27%** | -0.52% | 45.7% |
| B | 562 | **-0.91%** | -0.43% | 45.2% |
| C | 656 | **+0.69%** | +0.14% | 50.6% |

Spearman-rank correlation(score, expected_dir_return_72h) = **-0.0694**, permutation p-value =
**0.0055** — **statistically significant** (p < 0.01, unlike anything found in slice 007).

## Interpretation

At the 72h horizon, with a large sample (n=1754), the score/outcome correlation is not just
indistinguishable from zero — it is **significantly negative**. Higher-scored `macd_cross` signals
performed *worse* than lower-scored ones: `C`-tier (the lowest quality) had the best mean return
(+0.69%) and best win rate (50.6%), while `A`-tier (the highest quality actually observed) and
`B`-tier both underperformed it. The 24h horizon shows the same qualitative pattern (B underperforms
A and C) without reaching significance.

This is a stronger and more concerning result than slice 007's RSI validation, which found the score
simply uncorrelated with outcome. Here, across a much larger, statistically credible sample, the
heuristic shows a real, significant relationship with outcome — in the *wrong direction*. Combined
with slice 007's finding that the one small `A`-tier RSI sample also underperformed B/C, this is now
the second independent signal-type validation in which the score's highest tier did not outperform
lower tiers, and the second in which the pattern trended the wrong way, not merely toward zero.

## Comparison to slice 007 (RSI)

| | RSI (slice 007) | macd_cross (slice 011) |
|---|---|---|
| Sample size | 642 | 1,776 |
| 24h correlation | -0.0073 (p=0.87) | -0.0226 (p=0.31) |
| 72h correlation | -0.0369 (p=0.36) | **-0.0694 (p=0.0055, significant)** |
| Highest-tier (A) vs. lower tiers | A underperformed (n=12, low confidence) | A and B underperformed C (n=536-568, high confidence) |

**Conclusion is consistent and reinforced, not merely "also inconclusive": across both of the bot's
two enabled production signal types, the `SignalEnhancer` score does not identify better-performing
signals, and macd_cross's much larger sample now shows this with statistical significance in the
adverse direction.**

## Recommendation

This does not change the operator's standing decision from slice 007 (keep `notify_all`'s
`detail_min_quality: 'A'` gate as-is pending a redesigned/recalibrated heuristic and fresh
validation) — it reinforces the case for that redesign rather than requiring a new decision. Recorded
as a Convergence finding (not a unilateral change), consistent with FR-008.

## Assumptions and limitations

Same as slice 007 (13-pair/~10-month/single-exchange snapshot; sentiment approximated via the
sampled basket). The MACD-histogram-sign-change detection is mathematically identical to the
line-crosses-signal condition the live indicator uses (see research.md) — not an approximation.
