# Phase 1 Data Model: Test Coverage for Untested Pure-Logic Core Modules

No new entities or persistent storage — this slice adds tests for existing in-memory structures only.

## `CrossOver.analyze` output DataFrame

- Columns: `{key_signal}_{key_indicator_index}` (one or more), `{crossed_signal}_{crossed_indicator_index}`
  (one or more), plus `is_hot: bool`, `is_cold: bool`.
- Rows: inner-joined on the input DataFrames' shared index, with any row containing a NaN in either
  side dropped.
- No change to this shape — tests characterize the existing contract.

## `PairResolver.resolve` output

- `List[str]` of market symbols, e.g. `['BTC/USDT', 'ETH/USDT']`. Empty list on any unconfigured/
  unsupported path. No change to this contract.

## `QueuedNotification` / `NotificationQueue` (existing, `notifications/queue.py`)

- No new fields. Tests characterize: `add()`'s bool return, `queue: List[QueuedNotification]`
  ordering after `sort_by_priority()`, `is_update` flag set by `_is_duplicate()`, and `process_all()`'s
  return value (count sent).

## `SignalSummary` / `SmartNotificationManager` (existing, `notifications/smart.py`)

- No new fields. Tests characterize: `build_summary_message()`'s returned string's branch selection
  (via substring assertions on the known literal headers), and `finalize_cycle()`'s returned
  `{'summary': int, 'details': int, 'charts': int}` stats dict.

## `ConfigValidator.validate_required_config` (existing, `notifications/validator.py`)

- No new fields. Tests characterize the existing `bool` return for three input shapes.
