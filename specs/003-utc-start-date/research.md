# Phase 0 Research: Correct UTC Start-Date Calculation

## Decision: Fix location and approach

**Decision**: Change `max_days_date = datetime.now() - (max_periods * start_date_delta)` to
`max_days_date = datetime.now(timezone.utc) - (max_periods * start_date_delta)`, and change the
return line from `int(max_days_date.replace(tzinfo=timezone.utc).timestamp() * 1000)` to
`int(max_days_date.timestamp() * 1000)` (the value is already UTC-aware, so `.replace()` is no
longer needed — and would in fact be a no-op once the value already carries `tzinfo=utc`, so
removing it is a correctness clarification, not just a simplification).

**Rationale**: `datetime.now(tz)` — with a `tz` argument — returns the current instant correctly
converted into that timezone, unlike `datetime.now()` followed by `.replace(tzinfo=...)`, which
never converts, only relabels. This is confirmed by direct inspection: `timezone` is already
imported in `exchanges/driver.py` (used in the current, buggy line), so this fix introduces no new
import and is a two-token change on two lines.

**Alternatives considered**:
- *Keep `.replace(tzinfo=timezone.utc)` for defensive clarity even though redundant* — rejected:
  keeping it invites a future reader to think it's doing real conversion work (it's the exact
  pattern that caused this bug), whereas removing it makes the UTC-awareness visibly originate from
  `datetime.now(timezone.utc)` alone.
- *Use `datetime.now().astimezone(timezone.utc)`* — rejected: `.astimezone()` on a naive datetime
  assumes the *system* local timezone to interpret the naive value before converting, which
  reintroduces the same host-timezone dependency this fix removes; `datetime.now(timezone.utc)`
  gets the UTC instant directly with no intermediate naive-local step.

## Verification: no other behavior depends on the old (buggy) value

Confirmed via `grep` (already run for slice 002's Convergence T009) that `_calculate_start_date` has
exactly one caller (`get_historical_data`, only when `start_date` is not explicitly passed), and
`get_historical_data` has exactly one caller (`DataManager.get_ohlcv`, slice 001), which never
passes `start_date`. No other code path is affected by this change.
