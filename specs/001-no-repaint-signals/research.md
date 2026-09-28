# Phase 0 Research: Eliminate Signal Repaint

No `NEEDS CLARIFICATION` markers remained in the Technical Context, so this phase documents the
decisions already grounded in direct code inspection rather than open unknowns.

## Decision: Where to fix it

**Decision**: Fix at `DataManager.get_ohlcv` (`app/data/manager.py`), the single choke point every
indicator/informant/crossover path already goes through (confirmed via
`behaviour/strategies.py::_get_indicator_results` and `_get_informant_results`, both reading from
`all_historical_data[exchange][market_pair][candle_period]`, which is populated exclusively by
`DataCollector._get_historical_data` → `ExchangeInterface.get_historical_data` →
`CCXTDriver.get_historical_data`).

**Rationale**: FR-003 requires the fix to apply to *every* current and future indicator without each
one needing its own patch. `outputs.py` and `notifications/builder.py` both call `.iloc[-1]` on
results derived from this one shared series; there is no second path that bypasses it (confirmed by
grep across `app/` for `fetch_ohlcv` and `get_historical_data` call sites — `CCXTDriver` is the only
caller of `ccxt`'s OHLCV fetch).

**Alternatives considered**:
- *Patch every indicator's `analyze()` to drop its own last row* — rejected: ~15 indicator classes,
  each would need the same timestamp-vs-now logic duplicated, violating FR-003 and inviting the next
  new indicator to reintroduce the bug.
- *Patch every `iloc[-1]` call site in `outputs.py`/`notifications/builder.py` to use `iloc[-2]`* —
  rejected: assumes the last row is always unclosed, which is false once the candle *has* closed;
  would discard one full extra closed candle needlessly and still not fix indicators that compute
  rolling values (RSI, MACD) using the unclosed candle internally before that final row.

## Decision: How to know a candle is closed

**Decision**: `close_time = candle_start_ms + ccxt.Exchange.parse_timeframe(timeframe) * 1000`;
candle is closed iff `close_time <= now_utc_ms` (`now_utc_ms` computed once per `get_ohlcv` call via
`datetime.now(timezone.utc)`, not per-candle, and not from any additional exchange round trip).

**Rationale**: `ccxt.Exchange.parse_timeframe` is a static method (verified: callable as
`ccxt.Exchange.parse_timeframe('4h')` → `14400` seconds, `'1d'` → `86400`, with no exchange
instance construction, no network call, no credentials) — satisfies Constitution Principle I and
avoids a second, redundant "what time is it on the exchange" request that would add latency and a
new failure mode (FR-006, Constraints).

**Alternatives considered**:
- *Fetch exchange server time explicitly (`exchange.fetch_time()`)* — rejected: adds a network call
  per cycle per exchange for a correction that's within seconds, while local-vs-exchange clock drift
  is already handled at the infrastructure level for the *sibling* Freqtrade deployment (see
  `freq/ops/stack.ps1` drift check) and is not a documented problem for this project; can be revisited
  later as a follow-up if drift is ever observed in practice.
- *Assume the last candle is always unclosed and always drop it* — rejected: this is exactly the
  "count rows" approach FR-006 explicitly forbids; it silently discards a legitimately-closed final
  candle whenever the fetch happens to land right after a close, which is common with
  `update_interval: 300` against a `4h`/`1d` `candle_period` (i.e., not synchronized to candle
  boundaries).

## Decision: Test framework

**Decision**: `pytest`, added via a new `requirements-dev.txt` (not referenced by the Dockerfile, so
the production image size and dependency surface are unchanged).

**Rationale**: Constitution Principle VI mandates tests for `data/`; no test framework exists in the
repo today (`requirements-step-2.txt` has no test dependency; no `tests/` directory, no
`pytest.ini`/`conftest.py` found). `pytest` is the de facto standard for this stack and is already
implied by Spec Kit's own scaffolding conventions.

**Alternatives considered**:
- `unittest` (stdlib, zero new dependency) — viable, but rejected in favor of `pytest` for
  parametrized test cases (useful here: multiple `candle_period` values, multiple "how far past
  close" offsets) with less boilerplate; the marginal dependency-surface cost is one pinned
  dev-only package.
