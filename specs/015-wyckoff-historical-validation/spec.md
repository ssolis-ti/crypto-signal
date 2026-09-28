# Feature Specification: Historical Validation of Wyckoff Spring/Upthrust Signals

**Feature Branch**: `main` (Spec Kit feature directory: `specs/015-wyckoff-historical-validation`)

**Created**: 2026-09-28

**Status**: Draft — **blocked on `specs/014-wyckoff-range-spring-upthrust` landing** (this slice
backtests the events that slice produces).

**Input**: Third slice of the Wyckoff roadmap — the "does this actually predict anything" gate, same
discipline as `specs/007-signal-enhancer-validation/` and `specs/011-macd-cross-validation/`, applied
to Spring/Upthrust events instead of RSI/MACD crosses. The operator additionally recalled: **"la
version antigua mostraba alerta de potenciales HOT y luego de una semana o 2 el precio de los token
subían un 20%-30%"** — a specific, falsifiable, longer-horizon claim this validation MUST test
directly, not only the 24h/72h horizons used in slices 007/011.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Test whether Spring/Upthrust events predict forward returns, at multiple horizons including 1-2 weeks (Priority: P1)

**Why this priority**: This is the actual go/no-go gate for the entire Wyckoff investigation — per
Constitution Principle III, nothing from slices 013/014 may influence a real alert until this
validation shows a real, statistically credible effect. The operator's own recollection of a specific
historical pattern (HOT alert → +20-30% over 1-2 weeks) is a concrete, testable hypothesis this slice
exists to check honestly, not to confirm by construction.

**Independent Test**: Reuse slices 007/011's basket, data source, and permutation-test methodology.
Replace the signal trigger with `detect_springs`/`detect_upthrusts` (slice 014) run over the same
historical OHLCV. Measure realized forward returns at **four** pre-declared horizons: 24h, 72h (for
direct comparability with slices 007/011), **7 days, and 14 days** (to directly test the operator's
recollection).

**Acceptance Scenarios**:

1. **Given** a historical Spring event, **When** scored/measured, **Then** its realized forward
   return is recorded at all four horizons.
2. **Given** a historical Upthrust event, **When** measured, **Then** its expected-direction (sell-
   bias) forward return is recorded at all four horizons.
3. **Given** the full set of events, **When** aggregated, **Then** the report states, per horizon,
   mean/median/win-rate and a permutation-test p-value — including explicitly whether the 7d/14d
   horizons show a materially different (better, worse, or absent) effect than 24h/72h, since the
   operator's recollection is specifically about the longer horizon.
4. **Given** the operator's specific magnitude claim (+20-30% over 1-2 weeks), **When** the 7d/14d
   results are in, **Then** the report states plainly whether ANY quality/event-confidence bucket's
   mean or median return approaches that magnitude, or whether the claim does not replicate in this
   sample — stated as a fact-check, not softened either direction.
5. **Given** results at all four horizons, **When** the report concludes, **Then** it makes one
   explicit recommendation (validated enough to inform `SignalEnhancer`/alerts; needs more/different
   data; or does not replicate), consistent with slices 007/011's FR-008/FR-009 discipline (no
   unilateral gate change either way — a Convergence finding for operator sign-off if the result would
   imply one).

### User Story 2 - Methodology and results recorded (Priority: P1)

Same as slices 007/011: a `validation-report.md` in this feature's directory, explicitly comparing
its conclusion to those two prior reports (does Wyckoff succeed where RSI/MACD scoring failed, or
does the same pattern of no-predictive-value repeat a third time?).

**Acceptance Scenarios**:

1. **Given** the script has run, **When** its output is captured, **Then** `validation-report.md`
   documents data source/range, methodology (citing slices 007/011 by reference for anything reused
   unchanged), full results at all four horizons, the explicit fact-check against the operator's
   recollection, and one recommendation.

### Edge Cases

- If Spring/Upthrust events are too rare in the ~10-month/13-pair sample to reach a usable sample size
  (plausible — these are rarer, more specific patterns than RSI thresholds or MACD crosses), the
  report MUST say so plainly (extend the date range and/or basket rather than silently accepting an
  underpowered result) rather than drawing a conclusion from too few events.
- The 14-day horizon requires 14 days of *future* data past each event — events in the last 14 days
  of the fetched window MUST be excluded from that horizon's aggregation (same `None`-if-insufficient-
  future-data pattern as slices 007/011's existing horizons), not padded or estimated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The validation MUST use the real `detect_springs`/`detect_upthrusts` functions from
  slice 014 — not a reimplementation.
- **FR-002**: The validation MUST use real historical OHLCV via CCXT, same basket/pairs/date-range
  convention as slices 007/011 for comparability (extended further back in time if needed to reach a
  usable Spring/Upthrust sample size per the Edge Cases above).
- **FR-003**: The validation MUST measure realized forward returns at 24h, 72h, 7 days, and 14 days —
  the last two specifically to test the operator's recollection, pre-declared before running (same
  no-cherry-picking discipline as slice 007's FR-005).
- **FR-004**: The report MUST explicitly fact-check the operator's "+20-30% over 1-2 weeks" claim
  against the actual 7d/14d results, stated plainly regardless of outcome.
- **FR-005**: The report MUST explicitly compare its conclusion to slices 007 and 011.
- **FR-006**: This feature MUST NOT change `SignalEnhancer`'s weights or `notify_all`'s gate
  unilaterally — same FR-008/FR-009 discipline as slices 007/011.

### Key Entities

- **`WyckoffSignalEvent`**: `(pair, timestamp, direction, break_relative_volume,
  confirm_relative_volume, forward_return_24h, forward_return_72h, forward_return_7d,
  forward_return_14d)`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The validation script runs against real exchange data; sample size and its adequacy (or
  inadequacy) at each horizon is stated honestly.
- **SC-002**: `validation-report.md` contains concrete numbers for all four horizons and the explicit
  fact-check against the operator's recollection.
- **SC-003**: The existing test suite is unaffected (research artifact, not application code).
- **SC-004**: One clear recommendation is recorded, with any implied behavior change logged as a
  Convergence finding rather than applied unilaterally.

## Assumptions

- "1-2 weeks" is operationalized as exactly 7 and 14 calendar days (42 and 84 four-hour candles
  respectively) — a reasonable, symmetric reading of the operator's recollection, stated explicitly
  so the fact-check is falsifiable rather than fuzzy.
- The "20-30%" recollection is treated as a specific number to check against, not adjusted after
  seeing results — if the actual sample shows, say, a 3% mean move, that is reported as not
  replicating the recollection's magnitude, not reframed as "still meaningful."
