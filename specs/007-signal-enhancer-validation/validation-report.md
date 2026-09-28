# Validation Report: SignalEnhancer Score/Quality Heuristic

**Date**: 2026-09-28 | **Feature**: `specs/007-signal-enhancer-validation`
**Constitution reference**: Principle III (Validate Before You Trust a Heuristic)

## Data source

- Exchange: Binance (public REST API via `ccxt`, read-only `fetch_ohlcv` — no credentials, no
  orders, consistent with Principle I).
- Timeframe: `4h` (matches production `config-clean.yml: indicators.rsi.candle_period`).
- Date range: ~10 months back from 2026-09-28 (paginated `fetch_ohlcv`, deduplicated/sorted).
- Reference pair: `BTC/USDT`.
- Basket (14 intended, 13 usable): `ETH/USDT, BNB/USDT, SOL/USDT, XRP/USDT, ADA/USDT, DOGE/USDT,
  AVAX/USDT, LINK/USDT, DOT/USDT, LTC/USDT, BCH/USDT, ATOM/USDT, NEAR/USDT`. `MATIC/USDT` returned
  zero candles (delisted/renamed on Binance — Polygon's token migrated to `POL/USDT` since this
  basket was chosen) and was automatically skipped by the script, exactly as FR-008/Edge Cases
  specify for insufficient-history pairs — not treated as an error.

## Methodology

1. Computed RSI(14), EMA(99), and MACD(12,26,9) histogram via `talib` directly from historical
   closes, per pair — the same library every indicator class in `app/analyzers/indicators/` already
   uses internally.
2. Detected signal events exactly as the production bot's enabled `indicators.rsi` config would fire
   one alert per excursion: a **hot** event on the candle where RSI crosses from ≥30 to <30, a
   **cold** event where RSI crosses from ≤70 to >70 (config-clean.yml: `hot: 30`, `cold: 70`). No
   lookahead: each event only uses RSI/EMA/MACD values computed from candles up to and including its
   own timestamp.
3. For each event, reconstructed `MarketContextData`/`AltStrengthData` fields using the *exact*
   formulas in `app/analysis/market_context.py` (`_determine_trend`, `_calculate_sentiment`,
   `get_alt_strength`'s relative-strength formula), computed from real historical 24h % changes
   (6 candles back on 4h data) — with one documented simplification: market-breadth sentiment
   (gainers/losers ratio) is computed across the 13-pair basket rather than the full Binance USDT
   universe (infeasible to fetch historically at this scope; `sentiment_weight` is the smallest
   scoring factor, ±5 of 100, bounding this approximation's influence).
4. Scored every event with the real, unmodified, imported
   `SignalEnhancer._calculate_quality`/`_calculate_score` (`app/analysis/signal_enhancer.py`),
   constructed with default settings — which are numerically identical to `config-clean.yml`'s
   `correlation.scoring` block (`btc_weight=15`, `structure_weight=10`, `rsi_weight=5`,
   `rsi_weight_bearish=3`, `sentiment_weight=5`, RSI thresholds 25/40/60/75).
5. Measured realized forward return at two horizons pre-declared before running (FR-005): 24h
   (6 candles) and 72h (18 candles). Defined `expected_dir_return` as the raw forward return for hot
   (buy-bias) signals and its negation for cold (sell-bias) signals, so "higher is better" uniformly
   across both directions.
6. Aggregated by quality tier (sample size, mean, median, win rate) and computed a Spearman-rank
   correlation between continuous `score` and `expected_dir_return`, with a permutation-test p-value
   (2000 shuffles, seed 42) — chosen over `scipy.stats.spearmanr` specifically to avoid adding a new
   pinned dependency for one script (Principle VII; see `research.md`).

## Results

**642 total events** (326 hot, 316 cold) across 13 pairs over ~10 months — well above the ~30/30
sample-size target (SC-001).

Quality tier distribution: **C: 520, B: 109, A: 13, A+: 0.** No `A+` events occurred in this sample —
consistent with the spec's anticipated edge case (score ≥80 requires several bonus factors to align
simultaneously) and reported here as a finding, not a defect.

### Horizon 24h (n=641 with valid forward data)

| Tier | n | mean | median | win rate |
|---|---|---|---|---|
| A+ | 0 | — | — | — (insufficient sample) |
| A | 12 | **-4.95%** | -3.14% | **8.3%** |
| B | 109 | -0.25% | +0.83% | 60.6% |
| C | 520 | -0.32% | +0.17% | 52.1% |

Spearman-rank correlation(score, expected_dir_return_24h) = **-0.0073**, permutation p-value =
**0.8656** (not distinguishable from chance).

### Horizon 72h (n=637 with valid forward data)

| Tier | n | mean | median | win rate |
|---|---|---|---|---|
| A+ | 0 | — | — | — (insufficient sample) |
| A | 12 | **-4.43%** | -2.41% | **8.3%** |
| B | 105 | -1.00% | +0.36% | 53.3% |
| C | 520 | -0.70% | +0.48% | 52.9% |

Spearman-rank correlation(score, expected_dir_return_72h) = **-0.0369**, permutation p-value =
**0.3558** (not distinguishable from chance).

## Interpretation

The score shows **no measurable predictive value** at either horizon: both correlations are
statistically indistinguishable from zero (p = 0.87 and p = 0.36, both far above any conventional
significance threshold). If anything, in this sample, the single highest tier actually achieved
(`A`, n=12) performed **worse** than both lower tiers — an 8.3% win rate vs. ~52-61% for B/C — though
with only 12 observations this is itself not a reliable signal in either direction; it does, however,
rule out the score being validated as "at least directionally useful but noisy."

B and C tiers perform similarly to each other and close to a 50/50 coin-flip win rate, which is what
would be expected from an RSI-oversold/overbought mean-reversion trigger with no additional
edge — the raw trigger itself may carry some value, but the `SignalEnhancer` scoring layer on top of
it (BTC trend, structure/EMA99, alt relative strength, sentiment, RSI-extremity bonus) does not
measurably sort outcomes by quality in this data.

## Recommendation

**Per Principle III's explicit fallback, this heuristic has not earned the right to gate what an
operator sees.** Today, `notifications/core.py::notify_all` hardcodes `detail_min_quality: 'A'` and
`chart_min_quality: 'A'`, meaning only `A`/`A+` signals get a full detail message + chart; everything
else appears in the summary only. Given this validation, that gate is not evidence-based.

This was flagged as a **Convergence finding requiring operator sign-off (FR-009's second branch)**
rather than a unilateral code change, because loosening the gate changes real Telegram message volume
and chart-rendering load for an active deployment — a live-behavior change with a real operational
cost, not a pure bug fix.

**Operator decision (2026-09-28): keep the gate as-is (`detail_min_quality: 'A'` unchanged)**,
pending a redesigned/recalibrated `SignalEnhancer` scoring heuristic and a fresh run of this same
validation methodology (`validate_signal_enhancer.py`) against it before restoring confidence in
the gate. No code changed by this slice. See `tasks.md` Phase 4, finding F1.

## Assumptions and limitations (for future reference)

- 13-pair, ~10-month, single-exchange sample. A larger basket, longer history, or a different market
  regime could change these numbers — this is a snapshot validation, not a permanent proof.
- Sentiment approximated via the sampled basket, not the full exchange (documented in Methodology
  step 3; bounded impact given its ±5 weight).
- Only the RSI-based signal trigger was validated (the bot's other enabled signal, `macd_cross`, was
  not — reconstructing historical crossover detection faithfully was judged out of scope for this
  slice; flagged as a candidate follow-up in Convergence).
- This validates the *scoring formula*, not the underlying RSI-oversold/overbought trigger's own
  standalone edge, which is a separate question this slice does not answer.
