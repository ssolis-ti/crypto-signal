# Tasks: Read-Only Agent Integration API

**Input**: Design documents from `specs/009-agent-api/`

## Phase 1: Setup

- [X] T001 Add `fastapi==0.141.1`, `uvicorn==0.54.0` to `app/requirements-step-2.txt`.
- [X] T002 [P] Create `app/api/__init__.py`, `tests/api/__init__.py`.
- [X] T003 [P] Add `app/agent_state/` to `.gitignore` (runtime SQLite file, like `config.yml`/`.env`).

## Phase 2: User Story 1 - Queryable current state (P1)

### Tests first

- [X] T004 [P] [US1] `tests/api/test_store.py`: `AgentStateStore` round-trips for signals (insert +
      query, filters by symbol/quality/signal_type, ordering, limit), market context (insert + query,
      `history` param), indicator snapshots (upsert semantics — second write for same key replaces,
      not appends), worker status (upsert semantics) (FR-003, FR-004, FR-005, FR-006).
- [X] T005 [P] [US1] `tests/api/test_server.py`: `GET /health`, `GET /status`, `GET /market-context`,
      `GET /signals/recent` (with filters), `GET /indicators` (with filters) against a
      pre-populated `AgentStateStore`, using FastAPI's `TestClient`; cold-start (empty store) returns
      well-formed empty responses, not errors (FR-007, Edge Cases).

### Implementation

- [X] T006 [US1] `app/api/store.py`: `AgentStateStore` class — schema creation, thread-safe
      short-lived-connection writes guarded by a `threading.Lock`, read methods with
      filter/limit/history support (FR-003 through FR-006).
- [X] T007 [US1] `app/api/server.py`: FastAPI app + Pydantic response models + the 5 read endpoints
      from T005, backed by an injected `AgentStateStore` (FR-007).
- [X] T008 [US1] `app/behaviour/core.py`: accept optional `state_store` param; record market context
      in `_enhance_signals`, enhanced signals in `_enhance_pair_signals`, indicator/informant
      snapshots for every analyzed pair (new method, called from `run()` regardless of whether
      `signal_enhancer` is enabled), and a worker heartbeat at the end of `run()`.
- [X] T009 [US1] `app/app.py`: construct one shared `AgentStateStore`; start the FastAPI app via
      `uvicorn.Server` in a daemon thread bound to `0.0.0.0:8090`; pass `state_store` into every
      `Behaviour(...)` construction; pass a worker name so heartbeats are attributable.
- [X] T010 [US1] Confirm T004-T005 pass.

## Phase 3: User Story 2 - Self-describing discovery (P1)

- [X] T011 [US2] Confirm `/openapi.json` and `/docs` are served automatically by FastAPI (no
      additional code needed beyond well-typed route definitions from T007) — add a docstring/
      `summary`/`description` to each route for a clearer schema (FR-009).

## Phase 4: User Story 3 - Sanitized config exposure (P2)

### Tests first

- [X] T012 [P] [US3] `tests/api/test_server.py`: `GET /config` with a fake notifier config
      containing a fake secret string asserts that exact string never appears anywhere in the
      response body (FR-008, SC-002).

### Implementation

- [X] T013 [US3] `app/conf.py`: add `Configuration.to_sanitized_dict()` — explicit allow-list of
      `settings`/`indicators`/`informants`/`crossovers` plus enabled-notifier/-exchange name lists,
      never touching any `required` block's contents (per research.md's allow-list decision).
- [X] T014 [US3] `app/api/server.py`: `GET /config` endpoint using T013's sanitized dict.
- [X] T015 [US3] Confirm T012 passes.

## Phase 5: Principle VII cleanup (FR-011)

- [X] T016 [P] Demote the 4 leftover `print(f"DEBUG: ...")` lines in `app/conf.py` to
      `logger.debug` (add a module logger; remove the prefix).
- [X] T017 [P] Demote the 2 leftover `print(f"DEBUG: ...")` lines in `app/behaviour/core.py` to
      `self.logger.debug`.
- [X] T018 [P] Demote the 1 leftover `logger.info(f"DEBUG: ...")` line in `app/app.py` to
      `logger.debug`.

## Phase 6: Infrastructure

- [X] T019 `docker-compose.yml`: publish `127.0.0.1:8090:8090`; mount
      `./app/agent_state:/app/agent_state`.
- [X] T020 Rebuild the Docker image (`--no-cache`) with the new dependencies; run the full test suite
      inside it (SC-003).
- [X] T021 Start the bot for a real cycle; validate all six endpoints per `quickstart.md`, confirm
      host-only port binding (SC-001, SC-004), confirm no secret leakage (SC-002).
- [X] T022 [P] Refresh Graphify project graph.

## Dependencies & Execution Order

T001-T003 → T004/T005 (tests) → T006-T009 (implementation) → T010 → T011 → T012 → T013-T014 → T015
→ T016-T018 (parallel, independent files) → T019 → T020 → T021 → T022.

## Phase 7: Convergence

Assessed 2026-09-28. 11/11 functional requirements verified by code + tests. 115/115 tests passing
(88 prior + 27 new), zero regressions. SC-001 verified live: all six endpoints returned real,
well-formed data matching the same cycle's container logs. SC-002 verified: `/config` response
searched for the real `.env` Telegram token returned zero matches. SC-003 met (115 total, target was
25+ new — delivered 27). SC-004 verified: `docker port crypto-signal 8090` prints `127.0.0.1:8090`,
not `0.0.0.0:8090`. SC-005 not yet re-verified across an actual container restart in this session
(would require stopping/restarting and waiting for a new cycle) but is true by construction
(`signals`/`market_context_snapshots` are SQLite tables on a bind-mounted volume, unaffected by
container recreation). 7/7 constitution principles checked, no violations.

## Convergence Findings

| ID | Gap Type | Severity | Source | Evidence | Remaining Work |
|----|----------|----------|--------|----------|----------------|
| F1 | unrequested | MEDIUM | Pre-existing bug, found via this slice's own live verification | `GET /market-context` on real data showed `btc_change_1h: -630.06` — implausible for a percentage. Root cause: `app/analysis/market_context.py::_get_btc_data` reads CCXT's unified ticker `change` field and labels it `change_1h`, but CCXT's `change` is the *absolute* price change (e.g., -630 USD), not a percentage — this field has likely always been wrong, just never visible before this API exposed it in isolation | Future slice: fix `_get_btc_data` to either compute a real 1h percentage change (would need 1h OHLCV, not the 24h ticker) or drop the misleading `btc_change_1h` field until it's computed correctly. Out of scope here — this slice exposes existing computed values, it does not fix `MarketContext`'s own calculations (FR-010). |

**Outcome**: `tasks_appended` — F1 is a real, newly-surfaced (by this feature's own dogfooding) data
correctness bug, but lives entirely inside `MarketContext`, a file this slice's FR-010 explicitly
commits not to change; tracked for a dedicated future slice.
