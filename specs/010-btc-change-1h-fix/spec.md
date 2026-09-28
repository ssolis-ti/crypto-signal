# Feature Specification: Correct btc_change_1h to a Real 1-Hour Percentage Change

**Feature Branch**: `main` (Spec Kit feature directory: `specs/010-btc-change-1h-fix`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Arregla el bug pendiente, queda en modo autonomo hasta finalizar, se
eficaz." The pending bug is Convergence finding F1 from `specs/009-agent-api/tasks.md`:
`MarketContext._get_btc_data` reads CCXT's unified ticker `change` field and labels it
`btc_change_1h`. CCXT's `change` field is the *absolute* price delta over the ticker's own period
(24h on Binance), not a percentage and not a 1-hour window — so `btc_change_1h` has never actually
measured a 1-hour change; it silently duplicates (in raw-price-delta form) the same 24h window
`btc_change_24h` already covers correctly via the `percentage` field. This was invisible before
slice 009's Agent API exposed the raw value in isolation (`GET /market-context` showed
`btc_change_1h: -630.06`, an impossible percentage).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - btc_change_1h reflects an actual 1-hour price move (Priority: P1)

**Why this priority**: The field's own name and docstring (`% cambio 1h`) promise a 1-hour
percentage change; today it delivers neither a percentage nor a 1-hour window. An agent or operator
reading `GET /market-context` should be able to trust the field means what it says.

**Independent Test**: With a known, controlled 1h-candle close-price fixture for the reference pair,
`MarketContext.get_context()` returns `btc_change_1h` equal to
`(last_closed_1h_close - previous_1h_close) / previous_1h_close * 100`, computed from real OHLCV data
via `DataManager.get_ohlcv(exchange, reference_pair, '1h')` — not from the ticker's `change` field.

**Acceptance Scenarios**:

1. **Given** at least two closed 1-hour candles are available for the reference pair, **When**
   `get_context` runs, **Then** `btc_change_1h` equals the percentage change between the last two
   closed 1h candles' close prices.
2. **Given** fewer than two 1-hour candles are available (e.g. `DataManager` returns an empty or
   single-candle list), **When** `get_context` runs, **Then** `btc_change_1h` is `0.0` and no
   exception propagates (same safe-fallback contract as the rest of `MarketContext`).
3. **Given** `DataManager.get_ohlcv` raises (network/exchange error), **When** `get_context` runs,
   **Then** `btc_change_1h` is `0.0`, the error is logged at `debug` level, and the rest of
   `get_context`'s fields (btc_trend, sentiment, gainers/losers) are still computed normally — a
   failure fetching the 1h window MUST NOT break the whole cycle's market context.
4. **Given** the exact same ticker fixture that previously produced the impossible `-630.06` value
   (a large 24h absolute BTC price delta), **When** `get_context` runs with the new implementation,
   **Then** `btc_change_1h` is a plausible percentage (bounded, realistically, well within ±20% for
   any real 1-hour crypto move) — the regression this fix specifically closes.

### Edge Cases

- Only one closed 1h candle available (e.g. brand-new exchange or extremely short cache window):
  treated the same as "fewer than two," returns `0.0`.
- `previous_1h_close == 0` (degenerate/bad data): division-by-zero guarded, returns `0.0`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `MarketContext` MUST compute `btc_change_1h` from real 1-hour OHLCV data (via the
  already-injected `DataManager`), never from the ticker's ambiguous `change` field.
- **FR-002**: The computation MUST use only closed candles (rely on `DataManager.get_ohlcv`'s
  existing no-repaint guarantee — Principle II — rather than reimplementing candle-closure logic).
- **FR-003**: Any failure fetching or computing the 1-hour change (insufficient data, exchange error)
  MUST degrade to `0.0` without raising, and MUST NOT prevent the rest of `get_context`'s fields from
  being computed (FR-003 mirrors `MarketContext`'s existing fallback philosophy elsewhere in the
  file).
- **FR-004**: This feature MUST NOT change `btc_change_24h`, `btc_trend`, `market_sentiment`, or any
  other existing `MarketContextData` field's computation — scoped strictly to `btc_change_1h`.
- **FR-005**: `MarketContext` MUST gain test coverage (previously it had none) covering: normal
  computation, the insufficient-data edge case, the exchange-error edge case, and a regression test
  reproducing the specific bug (implausible percentage from a large absolute price delta).

### Key Entities

- **`MarketContextData.btc_change_1h`**: unchanged field name/type/consumers (Agent API, `to_dict()`
  for templates); only its computation source changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All new tests pass; the full existing suite (115 tests through slice 009) continues to
  pass unchanged.
- **SC-002**: A test reproducing the original bug's fixture (large 24h absolute delta on the ticker)
  would have failed against the pre-fix code and passes against the post-fix code.
- **SC-003**: A live smoke check (`GET /market-context` against the running bot after redeploy) shows
  a `btc_change_1h` value within a realistic range (e.g. `abs(value) < 20`), not the `-630.06`-style
  value observed before this fix.

## Assumptions

- "A real 1-hour change" means comparing the two most recently *closed* 1h candles' close prices —
  not the current in-progress candle (would violate Principle II) and not a longer/shorter window.
- This fix adds one additional cached OHLCV fetch per cycle (`'1h'` timeframe for the reference pair,
  via `DataManager`'s existing 5-minute TTL cache) — negligible cost, no new external dependency, no
  new exchange credential surface (Principle I unaffected).
