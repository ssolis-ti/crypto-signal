# Feature Specification: Read-Only Agent Integration API

**Feature Branch**: `main` (Spec Kit feature directory: `specs/009-agent-api`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Es mas de integracion para agentes, falta un buen debug/logs/info
para que la IA sepa que info disponible y apoye en la toma de decisiones." Clarified via follow-up
questions: access mechanism is a **REST API** (not MCP, not just structured logs); scope is
**comprehensive** — market context, signal history with score breakdown, full indicator/informant
snapshots per pair, and bot operational status, all "organizada, estructurada y ordenada"; the API
requires **no authentication** but MUST be bound so it is reachable only from the host machine (not
the public internet or LAN); signal/context history MUST **persist across container restarts**
(SQLite), not just live in memory.

Today, every cycle's market context, per-signal scoring breakdown, and indicator values are computed
in `Behaviour.run()`/`_enhance_signals()`/`_enhance_pair_signals()` and then immediately discarded —
only a text log line and (for qualifying signals) a Telegram message survive. There is no queryable
record of "what did the bot see and decide this cycle" for an external agent to consult.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An agent can ask "what is the bot seeing right now?" (Priority: P1)

**Why this priority**: This is the actual ask — an AI agent (e.g. a Claude session helping the
operator) needs a queryable, structured source of truth about current market conditions and recent
decisions, instead of parsing free-text container logs.

**Independent Test**: With the bot running a real cycle, `GET /market-context`, `GET /signals/recent`,
`GET /indicators`, and `GET /status` each return current, structured JSON matching what the same
cycle's logs show for BTC trend, the last few enhanced signals, per-pair indicator values, and
worker health.

**Acceptance Scenarios**:

1. **Given** the bot has completed at least one analysis cycle, **When** `GET /market-context` is
   called, **Then** it returns the latest `MarketContextData` fields (btc_trend, btc_change_24h,
   market_sentiment, gainers/losers, dominance_ratio) for each exchange, plus an optional
   `?history=N` to see the last N cycles' snapshots.
2. **Given** at least one signal was generated, **When** `GET /signals/recent` is called (optionally
   filtered by `pair`, `quality`, or `signal_type`), **Then** it returns the signal's full score
   breakdown (score, quality, confidence, recommendation, btc_trend, relative_strength,
   market_sentiment, context_note, derived indicators) and whether it was actually sent
   (`should_notify`), most recent first.
3. **Given** the bot has analyzed a pair, **When** `GET /indicators?pair=BTC/USDT` is called,
   **Then** it returns the latest computed value(s) for every indicator/informant configured for
   that pair (not only the ones that fired hot/cold), organized by candle period.
4. **Given** the bot is running, **When** `GET /status` is called, **Then** it returns each worker's
   pairs, cycle count, last cycle timestamp, and last error (if any) — enough for an agent to judge
   whether the bot is healthy without reading container logs.
5. **Given** no request-time filters are supplied, **When** any endpoint is called, **Then** it
   still returns a well-formed (possibly empty) response — never a 500 for "no data yet."

### User Story 2 - An agent can discover what's available without reading source code (Priority: P1)

**Why this priority**: The explicit ask was that "the AI knows what info is available" — a
self-describing API (OpenAPI schema) is exactly the mechanism that lets any agent introspect
capabilities without a human explaining the endpoints first.

**Independent Test**: `GET /openapi.json` (and the human-facing `/docs`) returns a complete,
accurate schema for every endpoint added by this feature, with descriptions.

**Acceptance Scenarios**:

1. **Given** the API is running, **When** `/docs` is opened, **Then** every endpoint in this feature
   is listed with its parameters and response shape, generated automatically by FastAPI from type
   hints and docstrings (no hand-maintained API reference to fall out of date).

### User Story 3 - The API exposes the bot's active configuration without leaking secrets (Priority: P2)

**Why this priority**: An agent helping debug or tune the bot needs to see which indicators,
thresholds, and pairs are active — but the Telegram token must never appear in an HTTP response,
even on a localhost-only API (Principle IV).

**Independent Test**: `GET /config` returns `settings`, `indicators`, `informants`, `crossovers`, and
the list of enabled exchanges/notifier types, but `notifiers.telegram.required.token` /
`chat_id` (and any other `required` secret field) are always omitted, never merely masked-looking.

**Acceptance Scenarios**:

1. **Given** `.env` has a real Telegram token, **When** `GET /config` is called, **Then** the
   response body does not contain that token string anywhere, even nested.

### Edge Cases

- API called before the first cycle completes: every endpoint returns empty lists/nulls, not an
  error (SC per Acceptance Scenario 5).
- A worker crashes mid-cycle (existing `AnalysisWorker` catch-all in `app.py`): `GET /status` shows
  the caught exception's message for that worker, and the API itself keeps serving (it runs in its
  own thread, independent of any single worker's health).
- SQLite file doesn't exist yet on first-ever startup: created automatically with schema, no manual
  migration step.
- Two workers (multiple pair chunks) write concurrently: no `database is locked` errors under
  normal cycle cadence (writes are infrequent — one batch per worker per `update_interval`).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose a REST API (FastAPI) running alongside the existing analysis
  workers in the same container/process, without blocking or slowing the analysis loop.
- **FR-002**: The API MUST be reachable from the host machine but NOT from the public internet or
  LAN: bound to `0.0.0.0` inside the container, published in `docker-compose.yml` as
  `127.0.0.1:8090:8090` (host-loopback-only), no authentication required.
- **FR-003**: Every enhanced signal (`EnhancedSignal`, from `SignalEnhancer.enhance()`) MUST be
  persisted with its full score breakdown, the exchange/pair/indicator it came from, and whether it
  was actually sent (`should_notify`), surviving container restarts (SQLite).
- **FR-004**: Every cycle's `MarketContextData` per exchange MUST be persisted as a timestamped
  snapshot, surviving container restarts.
- **FR-005**: The latest computed value(s) for every indicator/informant/crossover, for every
  analyzed pair and candle period, MUST be persisted and queryable — independent of whether
  correlation/`SignalEnhancer` is enabled (FR-005 does not depend on FR-003).
- **FR-006**: Each analysis worker's operational status (pairs covered, cycles completed, last cycle
  timestamp, last error if any) MUST be persisted and queryable.
- **FR-007**: The API MUST expose, at minimum: `GET /health`, `GET /status`, `GET /market-context`,
  `GET /signals/recent` (filterable by pair/quality/signal_type, paginated via `limit`),
  `GET /indicators` (filterable by pair/exchange), `GET /config` (sanitized).
- **FR-008**: `GET /config` MUST NEVER include any value under a notifier's `required` block (token,
  chat_id, webhook url/credentials) — omitted entirely, not masked.
- **FR-009**: The OpenAPI schema (`/openapi.json`, `/docs`) MUST accurately describe every endpoint
  this feature adds, generated by FastAPI from the route definitions (no separate hand-written API
  doc to maintain).
- **FR-010**: This feature MUST NOT change any existing notification behavior, indicator calculation,
  or scoring logic — it is a read-only, additive observability layer.
- **FR-011**: The three additional leftover `print(f"DEBUG: ...")` / `logger.info(f"DEBUG: ...")`
  statements found in `app/conf.py` (lines ~32/40/49/51), `app/behaviour/core.py` (lines ~75-76), and
  `app/app.py` (line ~58) — in the exact files this feature already needs to modify for wiring — MUST
  be cleaned up (demoted to `logger.debug` without the redundant prefix), per Constitution
  Principle VII, consistent with slice 006's precedent.

### Key Entities

- **`SignalRecord`**: persisted row per enhanced signal — mirrors `EnhancedSignal.to_dict()` plus
  `exchange`, `should_notify`, `created_at` (UTC).
- **`MarketContextSnapshot`**: persisted row per (exchange, cycle) — mirrors `MarketContextData`
  fields plus `created_at` (UTC).
- **`IndicatorSnapshot`**: latest-value-only row keyed by (exchange, pair, candle_period,
  indicator_type, indicator_name) — holds that indicator's last computed row as JSON, plus
  `updated_at` (UTC). Upserted, not append-only (FR-005 is about current state, not full history, to
  keep the store bounded).
- **`WorkerStatus`**: latest-value-only row keyed by worker name — pairs covered, cycle count, last
  cycle timestamp, last error. Upserted.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the bot running a real cycle, all six endpoints in FR-007 return HTTP 200 with
  well-formed JSON matching that cycle's actual data (cross-checked against container logs).
- **SC-002**: `GET /config`'s raw response body, searched as plain text, never contains the real
  Telegram token or chat ID configured in `.env`.
- **SC-003**: The existing test suite (88 tests through slice 008) continues to pass unchanged; new
  tests cover the store's read/write contract and every new endpoint (target: 25+ new tests).
- **SC-004**: A from-outside-the-host request (e.g. attempting the same request against the
  container's LAN-visible IP instead of `127.0.0.1`) is refused at the Docker port-publishing level,
  not merely "unauthenticated but reachable."
- **SC-005**: Restarting the container preserves prior signals/market-context history (queryable via
  the same endpoints after restart) — indicator/worker-status "latest" tables naturally reset to
  fresh values on the next cycle, which is expected (FR-005/FR-006 are current-state, not history).

## Assumptions

- "The AI" consuming this API runs on the same host machine (e.g., this Claude Code session, or
  another local agent) — not a remote service, consistent with the "no auth, host-only" decision.
- Full historical indicator time-series (every value ever computed) is explicitly NOT required —
  only signals and market-context snapshots need history; indicator/informant values only need
  "latest known state," since that is what "supports decision-making right now" calls for, and an
  unbounded indicator-history table would grow without limit for no stated use case.
- No new external dependency beyond `fastapi`+`uvicorn` (both already pip-installable in the existing
  Python 3.12 image; pinned per Principle VII to the versions confirmed compatible today:
  `fastapi==0.141.1`, `uvicorn==0.54.0`).
