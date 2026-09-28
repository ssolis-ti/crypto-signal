# Feature Specification: Eliminate Signal Repaint

**Feature Branch**: `main` (Spec Kit feature directory: `specs/001-no-repaint-signals`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Eliminate repaint in crypto-signal's indicator/signal pipeline. Today
every indicator (RSI, MACD, Bollinger, Ichimoku, ADX, crossovers, etc.) is calculated including the
current, still-forming candle for its configured candle_period, because the raw OHLCV data returned
from the exchange always includes the in-progress candle as its last element, and every consumer
reads that last row (iloc[-1]) as 'the current signal.' A signal that is hot/cold now can silently
stop being hot/cold a few minutes later when the candle closes with a different value, with no
record that it ever changed. Fix this at the data boundary so no indicator ever sees an unclosed
candle, without changing the notification format, the supported indicators, or requiring the user
to edit config.yml."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Alerts reflect a settled market state (Priority: P1)

A user running crypto-signal against a live exchange receives a Telegram alert that a pair's RSI is
"hot" (oversold). They act on that information (or simply record it) knowing that if they re-ran
the exact same analysis a minute later against the same historical window, they would get the same
verdict — the alert describes something that already happened and is final, not a live, moving
number that can flip before they finish reading it.

**Why this priority**: This is the core trust property of an alerting tool. Every other feature
(scoring, market context, smart notification tiers) is built on top of "the indicator result for
this candle is correct," so an unstable result at the base corrupts everything downstream silently.

**Independent Test**: Run the analysis cycle twice, several minutes apart, for the same market pair
and candle_period, without a new candle having closed in between. The set of closed candles used
for indicator calculation, and therefore every hot/cold verdict and signal value, MUST be identical
across both runs.

**Acceptance Scenarios**:

1. **Given** a market pair's most recent candle for its configured `candle_period` has not yet
   closed, **When** the analysis cycle runs, **Then** no indicator, informant, or crossover result
   is calculated using that unclosed candle — the newest data point used is the most recently
   *closed* candle.
2. **Given** two analysis cycles run back-to-back with no new candle close in between, **When**
   their results are compared for the same pair and candle_period, **Then** all indicator values,
   hot/cold flags, and derived scores are identical.
3. **Given** a candle closes between two analysis cycles, **When** the second cycle runs, **Then**
   its results are calculated using that newly closed candle as the latest data point, and the
   result may legitimately differ from the previous cycle (this is expected, correct behavior, not
   repaint).

### User Story 2 - Existing configuration keeps working (Priority: P2)

An operator who already has a working `config.yml` with indicators, informants, crossovers, and
notifiers configured upgrades to the fixed version and restarts the bot. No configuration change is
required; alerts continue to arrive in the same format and channels as before, just without the
instability described in User Story 1.

**Why this priority**: The project constitution and existing operators depend on `config.yml`
staying stable across bug fixes; a fix that requires reconfiguration is a regression in itself.

**Independent Test**: Start the bot with an unmodified pre-existing `config.yml` (from before this
fix) and confirm it runs to completion for at least one full analysis cycle across all configured
exchanges/pairs without errors, producing notifications in the same structure as before.

**Acceptance Scenarios**:

1. **Given** a `config.yml` written before this fix, **When** the bot starts after the fix is
   applied, **Then** it loads without requiring new required fields.
2. **Given** the bot completes an analysis cycle, **When** a notification is sent, **Then** its
   message structure (fields, template variables available) is unchanged from before the fix.

### Edge Cases

- What happens when an exchange returns fewer candles than requested (e.g., a newly listed pair)?
  Removing the unclosed candle MUST NOT cause an index error or crash if the remaining history is
  short; the pair is simply skipped for that cycle if too little closed history remains for the
  indicator's required period, consistent with existing "invalid data, skipping" handling.
- What happens for a candle_period the exchange defines with an unusual duration, or when exchange
  server time and local system time drift apart? The decision of whether the last candle is closed
  MUST be based on candle *timestamps* (start time + period duration vs. current time), not on
  counting rows, so it stays correct regardless of clock skew between the machine running the bot
  and the exchange server, and regardless of the exchange's specific timeframe strings.
- What happens if literally only the unclosed candle was returned (e.g., a brand-new pair with one
  candle of history)? The pair/period MUST be treated as having no usable closed data for that
  cycle (same handling as "no historical data returned" today), not as an error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST determine, for every fetched batch of historical candle data, whether
  its most recent candle has fully closed, based on that candle's start timestamp and the known
  duration of its `candle_period`.
- **FR-002**: The system MUST exclude the most recent candle from any indicator, informant, or
  crossover calculation whenever that candle has not yet closed at the moment the data was fetched.
- **FR-003**: The system MUST perform this exclusion at the single point where historical data is
  retrieved, so that every existing and future indicator/informant/crossover automatically receives
  only closed candles without needing its own fix.
- **FR-004**: The system MUST NOT change the on-disk `config.yml` schema, the set of supported
  indicators/informants/crossovers, or the notification message template variables as a result of
  this fix.
- **FR-005**: The system MUST continue to operate when an exchange returns a short history (e.g., a
  new listing), treating "too little closed history for this indicator's required period" the same
  way current "invalid/missing data" cases are already handled (log and skip that pair/period for
  the cycle), rather than crashing.
- **FR-006**: The candle-closed determination MUST rely on timestamps only (candle start time plus
  period duration compared to the current time), not on assumptions about which array index is
  "current," so it is correct for every supported `candle_period` value and independent of any
  drift between local system time and exchange server time.

### Key Entities

- **Historical Candle Batch**: The OHLCV series fetched for one (exchange, market pair,
  candle_period) combination for one analysis cycle; conceptually gains a derived property of
  "closed-candle count" used by every downstream calculation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running two analysis cycles for the same pair/candle_period with no candle close in
  between produces byte-for-byte identical hot/cold verdicts and signal values for every
  indicator, informant, and crossover, in 100% of observed cases.
- **SC-002**: Zero indicator/informant/crossover calculations use a candle whose close time is in
  the future relative to the time the data was fetched, verified across all supported
  `candle_period` values in use (`4h`, `1d`, and any others present in `defaults.yml`).
- **SC-003**: An operator's pre-existing `config.yml` continues to produce a complete analysis
  cycle and notification after the fix, with zero required edits.
- **SC-004**: Pairs with insufficient closed history are skipped with a logged reason, with zero
  unhandled exceptions attributable to the closed-candle exclusion logic.

## Assumptions

- The exchange's reported candle timestamp marks the *start* of that candle's interval (standard
  CCXT/OHLCV convention), and "closed" means current time ≥ start time + period duration.
- "Current time" for this determination is the moment the data was fetched (UTC), independent of
  the machine's local timezone setting (`settings.timezone`), consistent with Constitution
  Principle V (UTC internally, local time only at presentation).
- This fix does not attempt to correct any other existing behavior (e.g., the RSI hot-threshold
  floor, timezone handling elsewhere in the codebase) — those are separate, already-scoped slices.
- No new external dependency is required to determine period duration; it is derivable from
  information already available to the exchange integration layer.
