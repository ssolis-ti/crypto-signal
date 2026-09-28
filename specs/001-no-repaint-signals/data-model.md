# Phase 1 Data Model: Eliminate Signal Repaint

No persistent storage or schema is involved (Storage: N/A). The only conceptual entity from the
spec is realized as a pure function, not a new stateful class, to keep the fix minimal (FR-004).

## Historical Candle Batch (spec Key Entity)

Represented as-is today: `List[List[float]]`, each inner list
`[timestamp_ms, open, high, low, close, volume]`, sorted ascending by timestamp (existing behavior
in `CCXTDriver.get_historical_data`, which already sorts by `d[0]`).

**Derived property this feature adds**: "closed-candle count" — not stored as a field, but computed
and applied in place, as a trimming step before the batch is cached/returned.

## New pure helper

```
drop_unclosed_candle(ohlcv: List[List], timeframe: str, now_utc: datetime) -> List[List]
```

- **Input**: the raw OHLCV batch (as returned by the exchange driver, ascending order), the
  `candle_period` string (e.g. `"4h"`, `"1d"`), and the current UTC instant.
- **Output**: the same batch, with its trailing element removed *iff* that element's candle has not
  yet closed at `now_utc`. Never removes more than the single trailing element (closed candles
  earlier in the batch are never touched — this is a trim of the *tail*, not a re-filter).
- **Invariants**:
  - If `ohlcv` is empty, returns it unchanged (no-op; existing "no historical data" handling
    downstream is unaffected).
  - If `ohlcv` has one element and it is unclosed, returns an empty list (consistent with the spec's
    Edge Cases: "no usable closed data for that cycle").
  - Never raises for a recognized `candle_period`; an unrecognized one surfaces
    `ccxt`'s own `ValueError` from `parse_timeframe`, which is the existing error-handling pattern
    already used elsewhere in `CCXTDriver` (e.g., `_calculate_start_date`'s timeframe regex match).

## Integration point

`DataManager.get_ohlcv` (app/data/manager.py) calls this helper on the result of
`self.driver.get_historical_data(...)`, before `self.cache.set(...)`, so the cached value is already
trimmed and every cache hit downstream is correct by construction — no consumer of `get_ohlcv` needs
to know this happened.
