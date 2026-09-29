# Validation Report: Timing and Drawdown Risk of the Extreme-Volume Wyckoff Signal

**Date**: 2026-09-28 | **Feature**: `specs/018-wyckoff-timing-and-drawdown`
**Companion report**: `specs/017-wyckoff-edge-refinement/validation-report.md`

## Data source

Binance, real 1-hour OHLCV (finer than the 4h resolution used to detect events), covering the full
14-day forward window for each of slice 017's "confirmed filter" events (Spring/Upthrust with
break-candle volume ≥2.5x average) — 330 such events detected across 14 pairs (in-sample + out-of-
sample combined; MATIC/USDT again excluded), **321 with a complete 14-day 1h path available**
(9 excluded for being too close to "now" to have 14 full days of future data — same
insufficient-data-excluded pattern as every prior validation slice).

## Methodology

For each event, walked forward hour-by-hour from the confirmation candle (t=0) to t+336h (14 days),
computing the cumulative expected-direction return at 10 pre-declared checkpoints (1h, 2h, 4h, 8h,
12h, 24h, 48h, 72h, 7d, 14d), plus the Maximum Adverse Excursion (MAE — worst drawdown reached before
each checkpoint) and Maximum Favorable Excursion (MFE — best gain reached) up to each checkpoint.

**Explicit resolution boundary** (per spec FR-005): this uses 1-hour candles. It answers "how does
the move unfold hour by hour," not second-or-minute-level execution timing — that would require
order-book/tick data and live paper-trading, not a historical-candle backtest. This report does not
claim more precision than that.

## Results: the checkpoint curve

| Checkpoint | Mean return | Median return | Win rate | Median MAE | Median MFE |
|---|---|---|---|---|---|
| 1h | +0.56% | +0.37% | **72.9%** | 0.00% | +0.37% |
| 2h | +0.67% | +0.56% | **78.2%** | 0.00% | +0.72% |
| 4h | +0.84% | +0.64% | 73.2% | 0.00% | +1.13% |
| 8h | +1.07% | +0.70% | 68.5% | -0.10% | +1.37% |
| 12h | +1.17% | +0.73% | 64.5% | -0.33% | +1.59% |
| 1d | +1.11% | +0.88% | 62.6% | -0.63% | +2.32% |
| 2d | +1.04% | +1.42% | 62.6% | -1.31% | +3.17% |
| 3d | +1.21% | +1.86% | 61.1% | -2.00% | +3.83% |
| 7d | +0.46% | +1.99% | 61.7% | -3.29% | +6.08% |
| 14d | +1.79% | +2.84% | 63.9% | -4.41% | +8.94% |

**This directly answers the operator's question.** The win rate is at its highest — 72.9% at 1h,
peaking at **78.2% at 2h** — immediately after the alert, then steadily declines toward slice 017's
already-known ~60-64% as the window extends to days. The magnitude works the opposite way: small
early (+0.37-0.56% median in the first 1-2h) and growing toward the known +2.84% median by 14 days.

## Drawdown risk (MAE) — the leverage-critical number

| Adverse threshold | % of events that breached it before 14d |
|---|---|
| -2% | **68.5%** |
| -5% | 47.7% |
| -10% | 26.5% |

Over two-thirds of events see at least a 2% adverse move against the eventual favorable direction at
some point within 14 days, and more than a quarter see 10%+ adverse excursion. **A leveraged position
sized to survive only a 2-3% adverse move would be at real risk of liquidation before slice 017's
average 14-day outcome ever materializes**, even though that average outcome is genuinely positive.

## When does the move peak?

Median time-to-peak (MFE) is **215 hours (~9 days)** — most of the eventual favorable move has not
yet happened by day 1 or day 3. Only 19.3% of events peak within the first 24h, and only 32.1% peak
within the first 3 days. Holding for the full 14-day window captures meaningfully more upside (median
MFE +8.94% vs. the realized median return of only +2.84% — the move frequently gives back a large
part of its peak gain by day 14, which is itself informative about exit timing).

## What this means for a leveraged trader

Two genuinely different, honest strategies emerge from the same data — this report does not pick one,
it characterizes both so the operator can choose with full information:

1. **Fast/scalp approach (act within 1-2h of the alert)**: highest win rate observed (73-78%), but
   small typical magnitude (well under 1%) — needs meaningful leverage to be worth the effort, and
   the sample of *specifically* 1-2h outcomes has not been separately stress-tested for slippage/
   spread at that speed (this backtest assumes fills at candle close prices, which is optimistic for
   very fast execution).
2. **Hold-toward-14d approach**: bigger expected magnitude (median +2.84%, mean +1.79%) and a
   still-respectable 63.9% win rate, but requires tolerating a median 4.4% adverse excursion along
   the way, with roughly 1-in-4 events seeing 10%+ drawdown before it works out — **this is not
   compatible with tight/high leverage without either wide stops (that themselves risk being hit) or
   accepting a real chance of being stopped out of what would have been a winning trade.**

Neither approach supports the originally-recalled "seconds to minutes for a large move" — the data
does not show that scale of speed; the fastest meaningfully-elevated win rate window (1-2h) still
carries a sub-1% typical magnitude, not a fast double-digit swing.

## Recommendation

This is additional Convergence evidence for the same operator decision already pending from slice
017, now with the risk/timing detail needed to size it responsibly:

- If proceeding to a Telegram alert, the message should honestly convey **both** numbers — e.g., "72%
  win rate in the first 2 hours (~0.6% typical move), rising to ~64% win rate / ~2.8% typical move by
  14 days, with a realistic chance of a 5-10%+ adverse swing along the way" — not a single flattering
  statistic.
- Any leveraged use of this signal needs stop/margin sizing informed by the MAE table above, not by
  the mean/median return alone.
- True sub-hour execution timing (which the operator's original question was partly about) remains
  untested by this or any prior slice — validating that would require live paper-trading with
  real-time order-book data, a materially different (and riskier-to-set-up) kind of validation than
  a historical-candle backtest.

No code wired into any live path by this slice, same as every prior validation slice.

## Assumptions and limitations

- Assumes fills at hourly candle close prices — optimistic for genuinely fast (sub-hour) execution,
  which would face real slippage/spread this backtest cannot see.
- 321-event sample across 14 pairs and ~10 months — a meaningful sample, but still one historical
  window, not a guarantee of persistence.
- MAE/MFE are computed per-event independently; this does not model portfolio-level risk if multiple
  such alerts fire concurrently across pairs (a realistic scenario given ~330 events in 10 months
  across 14 pairs).
