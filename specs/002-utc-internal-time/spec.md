# Feature Specification: UTC-Consistent Internal Time Handling

**Feature Branch**: `main` (Spec Kit feature directory: `specs/002-utc-internal-time`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Make internal timestamp handling explicitly UTC everywhere it is not
user-facing presentation. Two confirmed spots: (1) analyzers/utils.py converts each candle's epoch
milliseconds through datetime.fromtimestamp() (implicit system-local interpretation) then a
locale-dependent strftime('%c')/to_datetime round trip to build the indicator DataFrame's index —
this only 'happens to work' because the container's system timezone defaults to UTC, not because it
is guaranteed to be UTC; (2) notifications/builder.py's anti-spam alert-frequency window uses naive
datetime.datetime.now() for both writing and comparing the 'do not re-alert until' timestamp, which
is self-consistent today but fragile to any DST or system-clock change. The one correct existing
example (notifications/builder.py's creation_date, which already converts to the configured local
timezone only at final message-rendering time) must be left unchanged and used as the pattern."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Indicator timestamps are correct regardless of host timezone (Priority: P1)

An operator deploys crypto-signal on a host or container whose system timezone is not UTC (e.g. a
future deployment change, a different base image, or a host misconfiguration). The indicator
calculations and any log output referencing candle times remain numerically identical to a UTC-host
deployment — the bot's technical analysis does not depend on an unstated assumption about the
container's local timezone.

**Why this priority**: This is the load-bearing assumption Constitution Principle V exists to close.
It currently holds only by accident (Debian slim images default to UTC); nothing in the code
documents or enforces it, so it is one base-image or deployment change away from silently shifting
every candle's recorded time by the host's UTC offset.

**Independent Test**: Convert a known epoch-millisecond timestamp through the indicator DataFrame
construction path twice — once with the process's system timezone set to UTC and once set to a
non-UTC zone (e.g. `America/Santiago`, UTC-3/UTC-4) — and confirm the resulting indicator DataFrame
index values are identical in both runs.

**Acceptance Scenarios**:

1. **Given** a batch of closed OHLCV candles with known epoch-millisecond timestamps, **When** they
   are converted into the indicator DataFrame, **Then** the resulting datetime index values are
   timezone-aware UTC and numerically equal to `epoch_ms` converted directly to UTC, independent of
   the host process's system timezone setting.
2. **Given** the same conversion runs under two different host system timezones, **When** their
   outputs are compared, **Then** they are identical.

### User Story 2 - Alert rate-limiting is immune to clock/DST shifts (Priority: P2)

An operator's alert-frequency setting (e.g. "don't re-alert on this signal for 1 hour") continues to
suppress duplicate alerts correctly even across a daylight-saving-time transition or a host clock
adjustment, because the internal "don't alert again until" bookkeeping is computed in UTC rather
than the host's local wall-clock time.

**Why this priority**: Lower risk than User Story 1 (DST transitions are rare, and the current bug
is latent, not observed), but it is the same class of defect and is cheap to fix alongside it.

**Independent Test**: Set an alert frequency, trigger `should_i_alert`, then simulate a one-hour
local-clock rollback (as happens at a "fall back" DST transition) without any UTC time having
elapsed, and confirm the anti-spam window is not incorrectly reset or extended by that rollback.

**Acceptance Scenarios**:

1. **Given** an alert frequency of "1h" was just recorded for a signal, **When** `should_i_alert` is
   checked again immediately after, **Then** it correctly reports "do not alert" regardless of the
   host's local timezone or DST state.
2. **Given** the host's local wall-clock time is adjusted backward (DST fall-back) with no UTC time
   having elapsed, **When** `should_i_alert` is checked, **Then** its answer is unaffected by that
   local adjustment (it depends only on elapsed UTC time).

### Edge Cases

- What happens to the one place that intentionally uses local time — the notification's displayed
  `creation_date` (via `settings.timezone`)? It MUST be left exactly as-is: this feature only
  changes *internal* bookkeeping (indicator index, anti-spam window), never the final,
  operator-configured, user-facing local time shown in a Telegram/webhook/stdout message.
- What happens if `historical_data` is empty when building the indicator DataFrame? The conversion
  MUST continue to produce an empty DataFrame without raising, same as today.
- What happens on a host where the system timezone truly is UTC (today's actual deployment)? Output
  MUST be unchanged from current behavior — this is a correctness/robustness fix, not a behavior
  change for the current default deployment.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The indicator DataFrame's datetime index MUST be constructed directly from each
  candle's epoch-millisecond timestamp as UTC, without any intermediate conversion that depends on
  the host process's system timezone or locale.
- **FR-002**: The alert anti-spam bookkeeping (recording and checking "do not alert again until")
  MUST use UTC-aware timestamps for both writing and comparing, so the stored deadline and the
  current-time check are computed on the same, host-timezone-independent clock.
- **FR-003**: The existing local-timezone conversion used only for the notification's displayed
  `creation_date` MUST NOT be changed by this feature — it already correctly converts to local time
  solely at final message rendering, which is the desired pattern this feature extends everywhere
  else.
- **FR-004**: This feature MUST NOT change `config.yml` schema, indicator/informant/crossover
  behavior semantics (hot/cold thresholds, periods), or notification message content, beyond the
  precision/correctness of internal time bookkeeping.
- **FR-005**: The DataFrame index conversion MUST NOT rely on a locale-dependent string
  format/parse round trip (the current `strftime('%c')` → `pandas.to_datetime` path), to remove both
  the timezone ambiguity and the locale dependency in one change.

### Key Entities

- **Indicator DataFrame index**: the per-candle datetime label used positionally by every indicator
  (`analyzers/indicators/*.py`) and by informants; gains a defined, explicit UTC timezone-awareness
  property it does not clearly have today.
- **Alert frequency deadline**: the "do not re-alert before this instant" value stored per
  `alert_frequency_key` in `MessageBuilder.alert_frequencies`; becomes UTC-aware.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Converting the same OHLCV batch to an indicator DataFrame under two different host
  system timezones produces byte-for-byte identical index values, in 100% of tested cases.
- **SC-002**: The anti-spam alert deadline comparison produces the same allow/suppress decision
  regardless of the host's local timezone or DST state, for a fixed amount of elapsed UTC time.
- **SC-003**: The notification's displayed `creation_date` is unchanged (same value, same format)
  before and after this feature, for the same input conditions and configured `settings.timezone`.
- **SC-004**: Zero new exceptions on empty or minimal historical data.

## Assumptions

- "UTC-aware" means a `pandas`/`datetime` value carrying explicit UTC tzinfo, not a naive value that
  is merely numerically equal to UTC by convention.
- No exchange or notifier credential is involved in this change (pure internal time-handling
  refactor), consistent with Constitution Principle I.
- The current default deployment (Debian slim container, effectively UTC system time) is not itself
  broken today in a user-visible way; this feature is a robustness/correctness fix for
  Principle V and for any future deployment where that accidental assumption no longer holds, not a
  reported bug in current output.
