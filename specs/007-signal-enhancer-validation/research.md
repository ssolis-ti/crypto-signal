# Phase 0 Research: Historical Validation of the SignalEnhancer Score/Quality Heuristic

## Decision: Reconstruct signal events and context directly from OHLCV, don't replay the live app

**Rationale**: The live pipeline (`DataManager` → indicator classes → `SignalEnhancer.enhance()`) is
built around a single "now" snapshot with live caching and a real `MarketContext` that queries live
tickers. Re-running that machinery 8-12 months into the past for every historical candle would require
either a live exchange time machine (impossible) or extensively mocking every layer — which would
risk testing the mocks, not the real scoring formula. Instead: fetch real historical OHLCV once,
compute RSI/EMA99/MACD directly via `talib` (the same library every indicator class already uses
internally), reconstruct `MarketContextData`/`AltStrengthData` instances with historically-accurate
field values using the exact formulas in `app/analysis/market_context.py`, and call the real
`SignalEnhancer._calculate_score` directly. This validates the actual scoring formula (the thing
Principle III is about) without needing to fake the live application's plumbing.

**Alternatives considered**: Mocking `DataManager`/`MarketContext` to replay history through the full
`SignalEnhancer.enhance()` call — rejected as much higher implementation risk (many more seams to get
subtly wrong) for no additional validity, since `enhance()` itself is a thin wrapper that just calls
`_calculate_quality`/`_calculate_score` with the context values — the same values this script
constructs directly.

## Decision: RSI(14) crossing 30/70 on 4h candles as the raw signal trigger, one event per crossing

**Rationale**: Matches `config-clean.yml`'s actual enabled production indicator
(`indicators.rsi`: `hot: 30`, `cold: 70`, `candle_period: 4h`, `period_count: 14`) exactly — not an
invented proxy. Defining an event as the *first* candle where RSI crosses below 30 (previous ≥ 30,
current < 30) — rather than every candle while RSI stays below 30 — matches how the bot's real
`alert_frequency: once` anti-spam behavior would fire in practice (one alert per oversold excursion,
not one per candle), giving a realistic event count instead of an inflated one from sustained
oversold/overbought stretches.

**Alternatives considered**: Counting every below-30 candle as its own event — rejected: would
massively over-count clustered, highly-correlated observations during a single extended dip, biasing
the statistics toward whatever that one dip did.

## Decision: Basket of 15 liquid, established USDT pairs, ~10 months of 4h history each

**Rationale**: Needs to be liquid/established (so history is long enough and price action isn't
dominated by listing-day noise), diverse enough to avoid one asset's idiosyncrasies dominating the
sample, and small enough to fetch quickly and respect exchange rate limits. Basket: BTC/USDT (as the
reference pair, excluded from being scored itself — it IS the market context), ETH, BNB, SOL, XRP,
ADA, DOGE, AVAX, LINK, MATIC/POL, DOT, LTC, BCH, ATOM, NEAR — 14 non-BTC pairs. ~10 months of 4h
candles (~1800 candles/pair via two paginated `fetch_ohlcv` calls) balances sample size against
script runtime and exchange rate-limit courtesy.

**Alternatives considered**: A single pair (e.g. only SOL) — rejected: one asset's regime (e.g. a
single strong trend) could make the score look better or worse than it generally is. The full dynamic
top-20-by-volume list from production — rejected as unnecessarily larger without materially better
statistical power for this validation's purpose.

## Decision: Approximate market-breadth sentiment using the sampled basket, not the full exchange

**Rationale**: `MarketContext._calculate_sentiment` needs gainers/losers counts across "the market" —
reconstructing that historically for literally every USDT pair on Binance at every timestamp is
infeasible (hundreds of pairs × thousands of timestamps). Using the 15-pair basket itself as a
market-breadth proxy is a reasonable, clearly-documented approximation: `sentiment_weight` is the
smallest scoring factor (±5 of a 0-100 score), so this approximation's impact on the overall
conclusion is bounded and disclosed, not hidden.

**Alternatives considered**: Fetching all ~300+ Binance USDT pairs' historical data to compute exact
sentiment — rejected as disproportionate effort for a ±5-point factor; would multiply script runtime
by ~20x for a refinement unlikely to change the conclusion.

## Decision: Permutation test for the score/outcome correlation p-value, no new `scipy` dependency

**Rationale**: `scipy.stats.spearmanr` would be the standard tool, but `scipy` is not currently a
project dependency and Principle VII requires exact/narrow pins for anything added. A permutation
test — shuffle the outcome labels N times, recompute the correlation each time, compare the real
correlation's percentile rank against the shuffled distribution — needs only `numpy`/`pandas` (already
pinned) and is arguably more transparent (no black-box formula, directly interpretable as "how often
would random chance produce a correlation this strong").

**Alternatives considered**: Adding `scipy` as a new dependency for one script — rejected as
disproportionate; a permutation test is equally rigorous for this sample size and adds no runtime
dependency to the Docker image.

## Decision: Forward horizon pre-declared as 6 candles (24h) and 18 candles (72h), before running

**Rationale**: Per FR-005, the horizon must be fixed before seeing results to avoid cherry-picking
whichever horizon happens to look best. 24h (one full day) and 72h (three days) are two economically
meaningful, pre-registered horizons for a 4h-candle mean-reversion signal — short enough to reflect
the signal's actual intended trade horizon, long enough to smooth single-candle noise. Both are
reported; neither is dropped regardless of outcome.
