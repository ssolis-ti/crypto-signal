# Phase 1 Data Model: Read-Only Agent Integration API

## SQLite schema (`app/agent_state/agent_state.db`)

### `signals` (append-only history)

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `created_at` | TEXT | ISO-8601 UTC |
| `exchange` | TEXT | |
| `symbol` | TEXT | e.g. `BTC/USDT` |
| `signal_type` | TEXT | hot/cold/neutral |
| `indicator` | TEXT | |
| `quality` | TEXT | A+/A/B/C |
| `confidence` | INTEGER | 0-100 |
| `score` | REAL | 0-100 |
| `recommendation` | TEXT | strong_buy/buy/hold/avoid/sell/strong_sell |
| `context_note` | TEXT | |
| `btc_trend` | TEXT | |
| `btc_change_24h` | REAL | |
| `relative_strength` | REAL | |
| `divergence` | TEXT | |
| `market_sentiment` | TEXT | |
| `rsi_slope` | REAL | |
| `macd_acceleration` | REAL | |
| `vwap_distance` | REAL | |
| `momentum_divergence` | TEXT | |
| `should_notify` | INTEGER | 0/1 |

Indexed on `(symbol, created_at)` and `(quality, created_at)` for the `/signals/recent` filters.

### `market_context_snapshots` (append-only history)

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `created_at` | TEXT | ISO-8601 UTC |
| `exchange` | TEXT | |
| `btc_trend` | TEXT | |
| `btc_change_24h` | REAL | |
| `btc_change_1h` | REAL | |
| `market_sentiment` | TEXT | |
| `total_gainers` | INTEGER | |
| `total_losers` | INTEGER | |
| `dominance_ratio` | REAL | |

Indexed on `(exchange, created_at)`.

### `indicator_snapshots` (latest-only, upsert)

| Column | Type | Notes |
|---|---|---|
| `exchange` | TEXT | part of composite PK |
| `symbol` | TEXT | part of composite PK |
| `candle_period` | TEXT | part of composite PK |
| `indicator_type` | TEXT | `indicators`/`informants`/`crossovers`, part of composite PK |
| `indicator_name` | TEXT | part of composite PK |
| `values_json` | TEXT | JSON dict of the indicator's last computed row |
| `updated_at` | TEXT | ISO-8601 UTC |

PK: `(exchange, symbol, candle_period, indicator_type, indicator_name)`.

### `worker_status` (latest-only, upsert)

| Column | Type | Notes |
|---|---|---|
| `worker_name` | TEXT | PK |
| `pairs_json` | TEXT | JSON list of symbols this worker covers |
| `cycle_count` | INTEGER | |
| `last_cycle_at` | TEXT | ISO-8601 UTC |
| `last_error` | TEXT | nullable |
| `updated_at` | TEXT | ISO-8601 UTC |

## API response shapes (Pydantic models in `app/api/server.py`)

- `SignalOut`: mirrors the `signals` row, `created_at` as an ISO string, `should_notify` as `bool`.
- `MarketContextOut`: mirrors `market_context_snapshots` row.
- `IndicatorSnapshotOut`: `{exchange, symbol, candle_period, indicator_type, indicator_name, values: dict, updated_at}` (`values_json` parsed back to a dict).
- `WorkerStatusOut`: mirrors `worker_status` row, `pairs` as a `List[str]` (parsed from `pairs_json`).
- `ConfigOut`: `{settings: dict, indicators: dict, informants: dict, crossovers: dict, enabled_notifiers: List[str], enabled_exchanges: List[str]}` — never includes any notifier's `required` block.
