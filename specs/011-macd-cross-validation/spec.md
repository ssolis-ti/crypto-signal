# Feature Specification: Historical Validation of the SignalEnhancer Score for macd_cross Signals

**Feature Branch**: `main` (Spec Kit feature directory: `specs/011-macd-cross-validation`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Validar macd_cross igual que RSI en slice 007." Slice 007 validated
`SignalEnhancer`'s 0-100 score against real historical data for the bot's RSI-based signal trigger
and found no measurable predictive value. `config-clean.yml`'s other enabled production indicator,
`macd_cross` (MACD line crossing its signal line), was explicitly left unvalidated (slice 007's FR-008
/ F2 Convergence finding) because reconstructing historical crossover detection was judged out of
scope for that slice. This feature closes that gap using the same methodology, applied to the actual
`macd_cross` trigger condition read directly from `app/analyzers/indicators/macd_cross.py`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Measure whether the score predicts anything for macd_cross signals (Priority: P1)

**Why this priority**: Same rationale as slice 007 — Constitution Principle III requires validating
any heuristic that gates output before trusting it, and `macd_cross` is one of only two signal
triggers actually enabled in production (`config-clean.yml`).

**Independent Test**: Reuse slice 007's basket (14 liquid USDT pairs, ~10 months of real Binance 4h
OHLCV, same reference pair BTC/USDT), but detect signal events using the **exact** condition
`app/analyzers/indicators/macd_cross.py::MACDCross.analyze` uses: MACD(12,26,9) line crossing above
its signal line (hot) or below it (cold) — not RSI thresholds. Score each event with the real,
unmodified `SignalEnhancer._calculate_quality`, using the same historically-reconstructed market
context formulas as slice 007. Measure realized forward returns at the same two pre-declared
horizons (24h, 72h) and aggregate by quality tier with the same permutation-test significance check.

**Acceptance Scenarios**:

1. **Given** a historical MACD bullish cross ("hot") event for a pair, **When** scored by the real
   `SignalEnhancer`, **Then** the event's realized forward return is recorded alongside its
   score/quality tier.
2. **Given** a historical MACD bearish cross ("cold") event, **When** scored the same way, **Then**
   its realized expected-direction forward return is recorded alongside its score/quality tier.
3. **Given** the full set of scored MACD-cross events, **When** aggregated by quality tier, **Then**
   the report states, with actual numbers, whether higher tiers show better mean/median
   expected-direction return and win rate, and whether score correlates with outcome beyond chance
   (permutation-test p-value, same method as slice 007).
4. **Given** the results, **When** the report concludes, **Then** it makes one explicit
   recommendation, and states whether it changes, confirms, or is independent of slice 007's
   RSI-based conclusion and the operator's standing decision (keep the `detail_min_quality: 'A'` gate
   as-is pending a redesigned heuristic).

### User Story 2 - Methodology and results are recorded (Priority: P1)

**Why this priority**: Same as slice 007 — Principle III requires recording validation results and
methodology alongside the feature.

**Independent Test**: A `validation-report.md` exists in this feature's spec directory with the same
structure as slice 007's: data source/range/pairs, exact methodology (explicitly noting what's reused
unchanged from slice 007 vs. what's new for MACD), sample sizes, full results, and one recommendation.

**Acceptance Scenarios**:

1. **Given** the validation script has run, **When** its output is captured, **Then** it is written
   into `validation-report.md` without needing to re-run anything to understand what was tested.

### Edge Cases

- Same as slice 007: pairs with insufficient history excluded, not errored; a quality tier with
  fewer than ~10 events reported as "insufficient sample," not silently dropped; a rare/absent `A+`
  tier is a reported finding, not a test failure.
- The `-2` index lookback `macd_cross.py` uses (comparing the last two rows after `dropna(how='all')`)
  must be replicated exactly — including that `dropna` uses `how='all'` (drops a row only if *every*
  column is NaN), not `how='any'`, which matters during the MACD warm-up period.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The validation MUST use the real, unmodified `SignalEnhancer._calculate_quality`
  (same requirement as slice 007's FR-001).
- **FR-002**: The validation MUST use real historical OHLCV data fetched read-only via CCXT (same as
  slice 007's FR-002) — reusing the same basket/date-range choice for direct comparability with
  slice 007's RSI results.
- **FR-003**: The signal-trigger definition MUST replicate
  `app/analyzers/indicators/macd_cross.py::MACDCross.analyze`'s exact condition: MACD(12,26,9) line
  crossing its signal line between the previous and current closed candle, with no lookahead.
- **FR-004**: Market-context inputs (btc_trend, sentiment, relative_strength, structure/EMA99,
  RSI, MACD histogram) MUST be reconstructed using the same formulas and the same documented
  simplifications as slice 007 (cited by reference, not re-derived).
- **FR-005**: The forward-looking outcome and horizons (24h/72h, direction-normalized
  `expected_dir_return`) MUST be identical to slice 007's, to keep the two validations comparable.
- **FR-006**: Results MUST be aggregated by quality tier with sample size, mean, median, win rate,
  and the same permutation-test significance check as slice 007.
- **FR-007**: `validation-report.md` MUST explicitly compare its conclusion to slice 007's RSI
  result (same finding, different finding, or inconclusive) and state one recommendation.
- **FR-008**: This feature MUST NOT change `SignalEnhancer`'s scoring weights/thresholds, and MUST
  NOT unilaterally change the `notify_all` quality gate — any recommendation implying a behavior
  change is recorded as a Convergence finding for operator sign-off (same discipline as slice 007's
  FR-008/FR-009).

### Key Entities

- **Historical MACD-cross signal event**: (pair, timestamp, direction, score, quality,
  forward_return) tuple, same shape as slice 007's `SignalEvent` but detected via MACD/signal-line
  crossing instead of RSI threshold crossing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The validation script runs against real exchange data and produces a non-trivial
  sample (target: at least ~30 combined hot+cold events, reported honestly even if short).
- **SC-002**: `validation-report.md` contains concrete numbers for every FR-006 metric and one
  unambiguous recommendation, including the explicit comparison to slice 007 (FR-007).
- **SC-003**: The existing test suite (121 tests through slice 010) is unaffected — same as slice
  007, this is a research artifact, not application code requiring new pytest coverage.
- **SC-004**: Slice 007's F2 Convergence finding (`macd_cross` unvalidated) is marked resolved.

## Assumptions

- Same assumptions as slice 007 regarding what "historical market data" means, network access, and
  the script living outside `app/` as a research artifact — carried over by reference, not restated.
