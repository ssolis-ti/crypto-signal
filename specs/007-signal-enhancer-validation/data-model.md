# Phase 1 Data Model: Historical Validation of the SignalEnhancer Score/Quality Heuristic

No new entities in the application. One research-artifact-only data structure:

## `SignalEvent` (script-internal record, not persisted in the app)

| Field | Type | Description |
|---|---|---|
| `pair` | str | e.g. `'SOL/USDT'` |
| `timestamp` | pandas.Timestamp (UTC) | candle open time of the triggering 4h candle |
| `direction` | str | `'hot'` or `'cold'` |
| `rsi` | float | RSI(14) value at trigger |
| `score` | float | real `SignalEnhancer._calculate_score(...)` output, 0-100 |
| `quality` | str | real `SignalEnhancer._score_to_quality(score)` output, A+/A/B/C |
| `forward_return_24h` | float or None | `(close[t+6] - close[t]) / close[t]`; `None` if insufficient future data |
| `forward_return_72h` | float or None | `(close[t+18] - close[t]) / close[t]`; `None` if insufficient future data |
| `expected_dir_return_24h` | float or None | `forward_return_24h` for hot, `-forward_return_24h` for cold |
| `expected_dir_return_72h` | float or None | same transform for the 72h horizon |

## Aggregation output (feeds `validation-report.md`)

Per quality tier (`A+`, `A`, `B`, `C`) and per horizon (24h, 72h):
- sample size
- mean / median `expected_dir_return`
- win rate (% of events with `expected_dir_return > 0`)

Plus, across all events combined:
- Pearson/rank correlation between continuous `score` and `expected_dir_return` (both horizons)
- Permutation-test p-value for that correlation
