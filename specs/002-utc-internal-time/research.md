# Phase 0 Research: UTC-Consistent Internal Time Handling

## Decision: Indicator DataFrame index conversion

**Decision**: Replace
`dataframe['datetime'] = dataframe.timestamp.apply(lambda x: pandas.to_datetime(datetime.fromtimestamp(x / 1000).strftime('%c')))`
with `dataframe['datetime'] = pandas.to_datetime(dataframe['timestamp'], unit='ms', utc=True)`.

**Rationale**: `pandas.to_datetime(..., unit='ms', utc=True)` interprets the epoch-millisecond value
directly as UTC — no dependency on the host's system timezone (`datetime.fromtimestamp` without a
`tz` argument uses the system local timezone) and no locale-dependent string formatting (`%c`,
which is affected by the process locale). It is also vectorized (single call over the whole column)
rather than a per-row Python-level `.apply()`, so it is strictly faster, not just more correct.

**Alternatives considered**:
- *Pass `tz=timezone.utc` to `datetime.fromtimestamp`* — rejected: still a per-row Python loop via
  `.apply()`, and still routes through a string round trip if left otherwise unchanged; the
  vectorized `pandas.to_datetime` approach fixes both problems in one change (FR-005).
- *Leave naive but document "container must be UTC"* — rejected: this is exactly the deferred,
  invisible bug the constitution closes off; a documentation-only fix does not satisfy FR-001
  ("MUST be constructed... without any intermediate conversion that depends on... system timezone").

## Decision: Alert anti-spam window

**Decision**: Replace `datetime.datetime.now()` in `parse_alert_frequency` and `should_i_alert` with
`datetime.datetime.now(datetime.timezone.utc)`.

**Rationale**: Both the write (`parse_alert_frequency`, called from `should_i_alert`) and the read
(`should_i_alert`'s comparison) must use the same clock; switching both to UTC-aware `now()`
preserves internal self-consistency while removing the host-local-time/DST fragility (FR-002,
SC-002). This is a minimal, two-call-site change — no new class or storage format needed, since
`self.alert_frequencies` already just stores whatever `datetime` object `parse_alert_frequency`
returns.

**Alternatives considered**:
- *Store elapsed-seconds integers instead of datetime objects* — rejected: larger diff, changes the
  stored type/contract for no added correctness once both sides are UTC-aware; out of proportion to
  the bug being fixed.

## Decision: `creation_date` (presentation layer)

**Decision**: No change. `datetime.datetime.now(timezone(self.timezone_str))` at line ~179 already
converts to the operator's configured local timezone *only* at final message-string construction,
which is precisely the pattern Constitution Principle V asks for everywhere else. This line is the
existing "correct example" cited in the spec's Input and Edge Cases, and FR-003 makes not touching
it an explicit requirement, not an oversight.
