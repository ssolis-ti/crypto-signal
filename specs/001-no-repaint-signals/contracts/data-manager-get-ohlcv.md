# Contract: `DataManager.get_ohlcv`

No network-facing API exists for this feature; this is a module-boundary contract between
`data/manager.py` and every one of its callers (`behaviour/data.py::DataCollector`, indirectly all
of `behaviour/strategies.py`).

## Before this feature

```
get_ohlcv(exchange, market_pair, timeframe, limit=240) -> List[List]
```
Returns up to `limit` candles, **including the currently-forming candle if the exchange includes
it** (which ccxt's `fetch_ohlcv` always does).

## After this feature

```
get_ohlcv(exchange, market_pair, timeframe, limit=240) -> List[List]
```
Same signature. Returns up to `limit` candles, **guaranteed to contain only closed candles** — the
trailing unclosed candle, if the exchange returned one, is removed before the result is cached or
returned. Callers require **zero code changes**; they already treat the last element as "the most
recent state," which is now true.

## Guarantees added

1. **G1 (closed-only)**: For every element `c` in the returned list, `c[0] + parse_timeframe(timeframe) * 1000 <= now_utc_ms` at the time of the call that populated the cache entry.
2. **G2 (cache consistency)**: A cache hit within the existing 5-minute OHLCV TTL returns the same
   already-trimmed series; the trim is not re-evaluated on every cache read (candles don't
   un-close), so no extra cost is added to cache hits.
3. **G3 (no shape change)**: Return type, element shape (`[ts, o, h, l, c, v]`), and ascending sort
   order are unchanged.
4. **G4 (short-history safety)**: If trimming would leave fewer candles than an indicator's required
   `period_count`, that is surfaced as "insufficient data" through the same path that already
   handles a short/empty response today (no new exception type).

## Non-goals

- Does not change `limit`'s meaning (still "up to N candles requested from the exchange"); the
  effective usable count after trimming may be `limit` or `limit - 1` depending on candle alignment.
- Does not add a call to fetch exchange server time.
- Does not change caching TTL or cache-key format.
