# Validation Report: Taker Buy/Sell Flow as a Wyckoff Refinement

**Date**: 2026-09-28 | **Feature**: `specs/021-wyckoff-taker-flow`
**Companion reports**: `specs/017/`, `specs/019/`, `specs/020-orderflow-and-social-data-research/research.md`

## Data source

Same 14-pair basket (`MATIC/USDT` excluded), ~10 months, but fetched via Binance's **raw**
`publicGetKlines` endpoint (not CCXT's unified `fetch_ohlcv`) specifically to recover
`taker_buy_base_volume` per candle — verified present and correctly parsed (321 events with a valid
`taker_buy_ratio` at their break candle, out of slice 017's 330).

## Methodology

Reused slice 017's exact 330-event population (extreme break-candle volume ≥2.5x). For each,
reconstructed the break candle's index (same approach as slice 019, via `detect_trading_range`'s
support/resistance arrays) and computed `taker_buy_ratio = taker_buy_base_volume / volume` at that
candle. Tested both pre-declared hypotheses (see `spec.md`) with the same chronological 70/30
in-sample/out-of-sample split as slices 017/019.

## Results

Overall `taker_buy_ratio` across all events: mean 0.496, median 0.492 — essentially balanced, as
expected for a large aggregate (most candles are not extreme in either direction).

| Hypothesis | In-sample win rate (lift) | Out-of-sample win rate (lift) | n (in/out) | Verdict (mechanical) |
|---|---|---|---|---|
| Baseline (slice 017 alone) | 58.9% (—) | 62.9% (—) | 224/97 | — |
| 1. Absorption (taker opposite to reversal) | 45.1% (**−13.8pp**) | **70.3%** (+7.4pp) | 51/37 | confirmed* |
| 2. Aggressive entry (taker same as reversal) | — | — | 8/3 | insufficient_sample |

*\*See Interpretation below — this "confirmed" label is mechanical (passed the pre-declared
out-of-sample bar) but does not survive closer scrutiny.*

### Hypothesis 2 could not be meaningfully tested

Only 8 in-sample and 3 out-of-sample events had taker flow aligned *with* the reversal direction
beyond the ±0.55/0.45 threshold — far below the pre-declared MIN_SAMPLE=30. This itself is
informative: extreme-volume Spring/Upthrust breaks in this sample are rarely driven by buyers-into-a-
Spring or sellers-into-an-Upthrust; when the taker flow is lopsided at all, it more often runs
opposite to the eventual reversal (consistent with the absorption mechanic being the more common
shape, even though its net predictive value is unproven — see below).

## Interpretation: why "confirmed" is not trustworthy here

Slice 017's extreme-volume filter was convincing specifically because it was **consistent** in both
directions: +6.6pp in-sample, +5.5pp out-of-sample — the same effect, similar size, in both periods.
The absorption hypothesis here shows the opposite pattern: **-13.8pp in-sample (worse than baseline,
not significant, negative mean return) vs. +7.4pp out-of-sample (better, significant)** — a sign flip
between the two periods, on a small out-of-sample sample (n=37). This is the signature of noise, not
a real effect: if absorption genuinely sharpened the edge, it should have looked at least directionally
positive in-sample too. Mechanically passing the pre-declared bar (out-of-sample win rate ≥60%,
p<0.05) does not, by itself, make this trustworthy — the bar was designed to catch overfit filters
that decay from a good in-sample number to a bad out-of-sample one (as filters 2 and 4 did in slice
017); it was not designed to catch the mirror case (bad in-sample, good out-of-sample by chance),
which is equally consistent with noise given a small enough out-of-sample bucket.

**Honest verdict: `inconclusive`, not confirmed.** This does not join slice 017's extreme-volume
filter as a second validated edge. It also does not rule out that taker flow carries information —
the underlying idea (distinguish absorbed selling from real buying at the same raw volume level) is
still theoretically sound and directly answers what `specs/020`'s research flagged as the gap in
slice 017's volume-only filter. It simply needs a larger sample (more months of history, and/or a
wider basket) before a real conclusion is possible, given how few events (51-88 depending on
threshold) fall into the extreme-ratio buckets to begin with.

## Recommendation

- **Do not add this to any alert framing yet** — the in-sample/out-of-sample inconsistency is
  disqualifying under this project's own standard, even though it technically cleared the mechanical
  bar.
- **If pursued further**: extend the historical window beyond 10 months (Binance's raw klines go back
  further) specifically to grow the absorption-bucket sample size past the ~50-90 events seen here,
  since the core idea remains theoretically well-motivated and cost nothing to compute (same
  zero-marginal-cost data source as this slice).
- **This does not change the pending operator decision from slices 017-019**: the extreme-volume
  filter alone remains the only validated basis for any Telegram alert; taker flow is neither added
  to nor subtracted from that recommendation by this result.

## Assumptions and limitations

Same as slices 017/019 (single historical window, pre-declared thresholds not swept). The ±0.45/0.55
thresholds were a reasonable first choice, not tuned — a different threshold might change the sample
sizes materially given how tightly `taker_buy_ratio` clusters around 0.5 in aggregate.
