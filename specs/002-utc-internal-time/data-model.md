# Phase 1 Data Model: UTC-Consistent Internal Time Handling

No new entities. Two existing values gain explicit UTC-awareness as a type-level property:

## Indicator DataFrame index

- **Before**: `pandas.DatetimeIndex`, timezone-naive, wall-clock value equal to the host's local
  interpretation of the candle's epoch timestamp (correct only if host system tz is UTC).
- **After**: `pandas.DatetimeIndex`, timezone-aware (`tz='UTC'`), value equal to the candle's epoch
  timestamp interpreted as UTC directly — independent of host system timezone.
- **Consumers**: every `analyzers/indicators/*.py` and `analyzers/informants/*.py` class that
  receives this DataFrame; all use the index positionally (`iloc`, `index.get_loc`, `dropna`), not
  via explicit timezone-sensitive arithmetic, so no consumer code changes are required — this is a
  type/correctness upgrade, not a contract change to callers (matches FR-004: no behavior-semantics
  change to indicators).

## Alert frequency deadline (`MessageBuilder.alert_frequencies[key]`)

- **Before**: naive `datetime`, host-local wall-clock "do not alert again until" instant.
- **After**: UTC-aware `datetime` (`tzinfo=timezone.utc`), same semantic meaning, immune to host
  DST/local-clock shifts.
- **Consumers**: only `MessageBuilder.should_i_alert`, in the same class — fully internal, no
  external contract to preserve beyond "still correctly suppresses duplicate alerts."
