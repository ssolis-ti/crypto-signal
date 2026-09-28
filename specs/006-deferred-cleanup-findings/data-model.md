# Phase 1 Data Model: Clean Up Deferred Convergence Findings

No new entities or persistent storage. Three existing functions' internal correctness/hygiene
properties change:

## `DataManager.get_top_pairs(exchange, quote, top_n, min_volume) -> List[str]`

- **Before**: two `logger.info` calls contain a literal `"DEBUG:"` prefix; two dead commented-out
  `logger.debug` lines present.
- **After**: diagnostic logs use `logger.debug` without the redundant prefix; dead lines removed.
- **Signature/return contract**: unchanged.

## `rendering.utils.convert_to_dataframe(historical_data) -> pandas.DataFrame`

- **Before**: `timestamp` column built via naive `datetime.datetime.fromtimestamp(x / 1000.0)` —
  depends on host process system timezone.
- **After**: built via `pandas.to_datetime(dataframe['timestamp'], unit='ms', utc=True)` — UTC-aware,
  host-timezone-independent, matching `analyzers/utils.py`'s already-fixed sibling function.
- **Signature**: unchanged. **Columns**: unchanged (`open`, `high`, `low`, `close`, `volume`, index
  by `timestamp`).

## `CalibrationLogger.log_ohlcv` / `CalibrationLogger._report_anomaly`

- **Before**: `datetime.fromtimestamp(ts/1000)` (naive, host-local) for per-candle log lines;
  `datetime.now()` (naive, host-local) for anomaly record timestamps.
- **After**: `datetime.fromtimestamp(ts/1000, tz=timezone.utc)` and `datetime.now(timezone.utc)`
  respectively — UTC-aware.
- **Signature/return contract**: unchanged (still logs via `self.logger`, still appends dicts to
  `self.anomalies`).
