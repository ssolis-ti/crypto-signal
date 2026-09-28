# Feature Specification: Historical Validation of the SignalEnhancer Score/Quality Heuristic

**Feature Branch**: `main` (Spec Kit feature directory: `specs/007-signal-enhancer-validation`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Avanza al slice 007, valida el score de SignalEnhancer." Constitution
Principle III requires: "Any scoring, weighting, or classification heuristic (including but not
limited to `SignalEnhancer`'s 0-100 score and quality tiers A+/A/B/C) MUST be validated against
historical market data — showing that higher-scored signals actually perform better on some
measurable forward-looking outcome — before it is allowed to gate which alerts reach the user...
Until validated, a heuristic MAY ship as informational-only." This has never been done; the
constitution itself flags it as an open item. `app/analysis/signal_enhancer.py::SignalEnhancer`'s
score is hand-tuned (`btc_weight=15`, `structure_weight=10`, `rsi_weight=5`, `sentiment_weight=5`,
per `config-clean.yml`'s `correlation.scoring`) and currently soft-gates output: `quality_filter` is
disabled today (`enabled: false` in `config-clean.yml`, so nothing is fully suppressed), but
`notifications/core.py::notify_all`'s hardcoded `detail_min_quality: 'A'` / `chart_min_quality: 'A'`
means only A/A+ signals get full detail + chart, regardless of validation status.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The score's real-world predictive value is measured, not assumed (Priority: P1)

**Why this priority**: This is the entire point of the slice and of Constitution Principle III — an
unvalidated heuristic is currently influencing what a real operator sees in detail vs. summary-only,
based on nothing more than plausible-sounding weights.

**Independent Test**: Fetch real historical OHLCV data (read-only, via CCXT — permitted under
Principle I) for a basket of liquid pairs, replay the actual RSI-oversold/overbought signal trigger
the bot uses in production (`indicators.rsi`: `hot: 30`, `cold: 70`, `candle_period: 4h`,
`period_count: 14`, per `config-clean.yml`) at each historical point in time using only
data available up to that point (no lookahead), score each occurrence with the real, unmodified
`SignalEnhancer._calculate_score` using historically-reconstructed market context, then measure each
occurrence's realized forward price movement and compare it across score/quality buckets.

**Acceptance Scenarios**:

1. **Given** a historical RSI-oversold ("hot") event for a pair, **When** scored by the real
   `SignalEnhancer` scoring function with historically-accurate inputs, **Then** the event's realized
   forward return over a fixed horizon is recorded alongside its score/quality tier.
2. **Given** a historical RSI-overbought ("cold") event, **When** scored the same way, **Then** its
   realized forward return (expected-direction: price falling is "correct" for a cold/sell signal)
   is recorded alongside its score/quality tier.
3. **Given** the full set of scored historical events (hot and cold combined, using a direction-
   normalized "expected-direction return" metric), **When** aggregated by quality tier, **Then** the
   report states, with actual numbers, whether higher tiers show better mean/median expected-direction
   return and win rate than lower tiers, and whether score correlates with outcome at a level not
   plausibly due to chance (via a permutation-test p-value on the score/outcome correlation).
4. **Given** the results, **When** the report concludes, **Then** it makes one explicit recommendation:
   keep the current soft-gate (`detail_min_quality: 'A'`) as-is because it's supported by the data,
   loosen/tighten it, or (if the score shows no measurable predictive value) recommend demoting the
   heuristic to fully informational-only per the constitution's explicit fallback.

### User Story 2 - Methodology and results are recorded for future reference (Priority: P1)

**Why this priority**: Principle III explicitly requires "Validation results and methodology MUST be
recorded alongside the feature that introduces or changes the heuristic" — without this, the next
person (or agent) touching `SignalEnhancer` has no way to know whether its weights are evidence-based.

**Independent Test**: A `validation-report.md` exists in this feature's spec directory documenting:
data source and date range, exact signal-trigger and scoring reconstruction logic, sample sizes per
bucket, all summary statistics, the significance test and its result, every simplifying assumption
made (and why), and the final recommendation.

**Acceptance Scenarios**:

1. **Given** the validation script has run, **When** its output is captured, **Then** it is written
   into `validation-report.md` in a form a future maintainer can read without re-running anything to
   understand what was tested and what was found.
2. **Given** the recommendation differs from the current configuration, **When** this slice
   concludes, **Then** either the config/code is updated to match the recommendation, or the
   discrepancy is explicitly logged as a Convergence finding for a follow-up decision (an operator
   call, not a unilateral config change, if the change would affect what real alerts look like).

### Edge Cases

- Pairs with insufficient historical depth (recently listed) are simply excluded from that pair's
  contribution — not treated as zero/error events.
- A quality tier with too few samples (e.g. fewer than ~10 events) to draw any conclusion is reported
  as "insufficient sample," not silently folded into a neighboring tier or omitted from the report.
- Because `A+` in production requires `score >= 80`, which needs several bonus factors to align at
  once, it is plausible that very few or zero real `A+` events occur in the sampled window — this is
  reported as a finding (the tier may be rare in practice), not treated as a test failure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The validation MUST use the real, unmodified `SignalEnhancer._calculate_score` (or
  `_calculate_quality`) function from `app/analysis/signal_enhancer.py` — not a reimplementation or
  approximation of the scoring formula.
- **FR-002**: The validation MUST use real historical OHLCV market data fetched read-only via CCXT
  (Principle I) — no synthetic/simulated price data.
- **FR-003**: The signal-trigger definition (what counts as a "hot"/"cold" raw signal event) MUST
  match the bot's actual production configuration (`config-clean.yml`'s `indicators.rsi`: RSI(14) on
  4h candles, hot at RSI<30, cold at RSI>70), and MUST NOT use any information not available at the
  signal's own timestamp (no lookahead into future candles when computing the signal or its inputs).
- **FR-004**: Market-context inputs fed into the score (`btc_trend`, `market_sentiment`,
  `relative_strength`, structure via EMA99, RSI, MACD histogram) MUST be reconstructed from the same
  historical data using the same formulas as `app/analysis/market_context.py`, with any necessary
  simplification (e.g., using the sampled pair basket as a market-breadth proxy for sentiment instead
  of the full exchange universe) explicitly documented in `research.md`.
- **FR-005**: The forward-looking outcome measured MUST be a realized, objective price return over a
  fixed, pre-declared horizon (not selected after seeing results) — no re-running with a different
  horizon to find a more favorable outcome after the fact.
- **FR-006**: Results MUST be aggregated by quality tier (and/or continuous score) with sample size,
  central tendency (mean and median), win rate, and a statistical test of whether score correlates
  with outcome beyond chance.
- **FR-007**: `validation-report.md` MUST record: data source/date range/pairs, exact methodology,
  every simplifying assumption, full results, and one explicit recommendation.
- **FR-008**: This feature MUST NOT change `SignalEnhancer`'s scoring weights or thresholds based on
  this validation alone — if the data suggests recalibration, that MUST be logged as a Convergence
  finding for a separate, explicit follow-up slice (changing production heuristics is a bigger,
  riskier change than measuring them).
- **FR-009**: If the validation finds no measurable predictive value in the score, this feature MUST
  either demote the current hardcoded `detail_min_quality`/`chart_min_quality` gate in
  `notifications/core.py::notify_all` to fully informational-only (per Principle III's explicit
  fallback) or, if that behavior change is judged too consequential to make unilaterally, log it as a
  Convergence finding requiring operator sign-off rather than silently leaving an unvalidated gate in
  place with no record that it was checked.

### Key Entities

- **Historical signal event**: one (pair, timestamp, direction, score, quality, forward_return) tuple
  produced by the validation script — not persisted in the app, only in the validation artifact/report.
- **Validation script**: a standalone, one-time analysis script (not a pytest regression test, not
  part of the runtime application) that performs the fetch + replay + scoring + aggregation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The validation script runs successfully against real exchange data and produces a
  non-trivial sample (target: at least ~30 hot events and ~30 cold events combined across the basket,
  reported honestly even if the actual count falls short).
- **SC-002**: `validation-report.md` contains concrete numbers (not placeholders) for every metric
  named in FR-006, and one unambiguous recommendation.
- **SC-003**: The existing test suite (88 tests from slices 001-006) is unaffected — this feature adds
  a research artifact, not application code that requires new pytest coverage (the scoring function
  it exercises is already exercised indirectly via existing behavior; a dedicated backtest script is
  not itself unit-tested).
- **SC-004**: The recommendation is acted on: either the code changed to match it (FR-009), or a
  Convergence finding is recorded requesting operator sign-off, with no silent no-op.

## Assumptions

- "Historical market data" for this validation means real exchange OHLCV data fetched at validation
  time (today, 2026-09-28) covering the preceding several months — not the bot's own recorded
  production signal history (which does not exist yet as a queryable dataset), consistent with
  Principle III's wording ("validated against historical market data").
- The validation script is a research artifact that lives under this feature's spec directory (not
  `app/`), since it is not part of the running application and does not need to ship in the Docker
  image — consistent with how `graphify-out/` and other tooling output is treated as outside the
  application's runtime surface.
- Network access to a live exchange (Binance, via CCXT, read-only `fetch_ohlcv`) is available in this
  execution environment — confirmed before writing this spec.
