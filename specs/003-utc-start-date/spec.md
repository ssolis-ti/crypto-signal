# Feature Specification: Correct UTC Start-Date Calculation for Historical Data Fetch

**Feature Branch**: `main` (Spec Kit feature directory: `specs/003-utc-start-date`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Fix exchanges/driver.py::CCXTDriver._calculate_start_date, which
computes the 'since' timestamp passed to the exchange's fetch_ohlcv call. It does
`datetime.now() - (max_periods * period_delta)` using naive local `datetime.now()`, then
`.replace(tzinfo=timezone.utc)` to force UTC labeling. `.replace(tzinfo=...)` does not convert a
timezone, it only relabels the existing wall-clock value as if it already were UTC — so if the host
process's local time is ever not UTC, the requested historical window is silently shifted by the
host's UTC offset, fetching the wrong candles (this is the F1 finding surfaced by slice 002's
convergence check). Found during specs/002-utc-internal-time's convergence scan. Today it happens to
produce correct results only because the container's system time defaults to UTC — the same latent
class of bug already fixed in analyzers/utils.py and notifications/builder.py."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Historical data requests cover the intended time window regardless of host timezone (Priority: P1)

An operator's bot requests, e.g., 240 periods of `4h` candles. The exchange receives a `since`
parameter that correctly marks "240 × 4 hours before the current UTC instant," independent of
whether the host process's system timezone is UTC or something else — so the fetched historical
window is always the one the operator's `limit`/`max_periods` configuration actually intended.

**Why this priority**: `since` is a real parameter sent to a third-party API; an incorrect value
here doesn't just mislabel data internally (as the two already-fixed spots did) — it changes *which
candles are requested at all*, potentially causing a multi-hour gap or overlap in the fetched
series depending on the host's UTC offset and sign.

**Independent Test**: Compute the `since` timestamp for a fixed `time_unit`/`max_periods` pair,
once with the process under UTC and once under a non-UTC system timezone, and confirm both produce
the identical epoch-millisecond value.

**Acceptance Scenarios**:

1. **Given** a `time_unit` of `"4h"` and `max_periods` of `240`, **When** the start date is
   calculated, **Then** the resulting epoch-millisecond value equals "the current UTC instant minus
   240 × 4 hours," computed without any dependency on the host process's local timezone setting.
2. **Given** the same `time_unit`/`max_periods` pair is calculated under two different host system
   timezones, **When** the two results are compared, **Then** they are identical.
3. **Given** the existing supported `time_unit` formats (minutes, hours, days, weeks, and the
   month/year approximations already in the period map), **When** the start date is calculated for
   each, **Then** each produces a value consistent with Acceptance Scenario 1's UTC-based
   calculation for that period's duration.

### Edge Cases

- What happens for an unrecognized `time_unit` format? Unchanged: the existing `ValueError` for a
  non-matching regex is preserved as-is (out of scope for this fix).
- What happens for `max_periods = 0`? The calculated start date should equal "now" in UTC (no
  regression from current arithmetic, which already handles this correctly — only the "now" itself
  is being corrected).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The start-date calculation MUST compute "the current instant" as UTC-aware from the
  moment it is read, not as a naive local value later relabeled as UTC.
- **FR-002**: The resulting epoch-millisecond timestamp MUST be numerically identical regardless of
  the host process's system timezone configuration.
- **FR-003**: This fix MUST NOT change the supported `time_unit` formats, the period-map
  approximations for month/year, or the `ValueError` behavior for an invalid `time_unit` string.
- **FR-004**: This fix MUST NOT change the function's signature or its caller
  (`get_historical_data`'s use of `_calculate_start_date` when `start_date` is not explicitly
  supplied).

### Key Entities

- **Start-date calculation**: pure function of `(time_unit, max_periods, current UTC instant)` →
  epoch milliseconds; gains a defined UTC-only current-instant source.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The calculated `since` value for a fixed `time_unit`/`max_periods` pair is identical
  across at least two different host system timezones, in 100% of tested cases.
- **SC-002**: For the current default deployment (UTC-system container), the calculated value is
  unchanged from before this fix (no regression for today's actual operating condition).
- **SC-003**: All currently-supported `time_unit` period types (`m`, `h`, `d`, `w`, `M`, `y`)
  continue to produce a start date without raising, with `M`/`y` keeping their existing 30-day/
  365-day approximations.

## Assumptions

- No exchange credential or network call is involved (pure arithmetic function), consistent with
  Constitution Principle I.
- This is a narrower, single-function follow-on to `specs/002-utc-internal-time` (its Convergence
  finding F1), not a new independent concern — same principle (V), different call site.
