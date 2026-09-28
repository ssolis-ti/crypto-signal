# Implementation Plan: Read-Only Agent Integration API

**Branch**: `main` | **Date**: 2026-09-28 | **Spec**: `specs/009-agent-api/spec.md`

## Summary

Add a new `app/api/` package: a thread-safe SQLite-backed `AgentStateStore` and a FastAPI app that
serves it. `app.py` starts the FastAPI server (via `uvicorn.Server` in a daemon thread) alongside the
existing `AnalysisWorker` threads, and constructs one shared `AgentStateStore`. `Behaviour` gains an
optional `state_store` parameter and records market context, enhanced signals, indicator snapshots,
and worker heartbeats at the points where it already computes them — no new computation, only
recording of existing values. `docker-compose.yml` publishes the API on `127.0.0.1:8090` only and
mounts a new volume for the SQLite file so it survives restarts.

## Technical Context

**Language/Version**: Python 3.12 (unchanged)
**New Dependencies**: `fastapi==0.141.1`, `uvicorn==0.54.0` (pinned per Principle VII; both confirmed
installable/importable in the current image)
**Storage**: SQLite (stdlib `sqlite3`, no new dependency), file at `app/agent_state/agent_state.db`
**Testing**: `pytest` + FastAPI's `TestClient` (bundled with `fastapi`, no extra dependency), same
Docker-based execution as prior slices
**Target Platform**: same container, new port `8090` published as `127.0.0.1:8090` only
**Constraints**: read-only observability, no auth (host-loopback-only instead — FR-002), must not
alter existing notification/scoring behavior (FR-010)
**Scale/Scope**: 1 new package (`app/api/`: `store.py`, `server.py`, `__init__.py`), edits to
`app.py`, `behaviour/core.py`, `conf.py` (debug-print cleanup + a sanitized-config helper),
`docker-compose.yml`, `requirements-step-2.txt`; ~25-30 new tests

## Constitution Check

| Principle | Check | Result |
|---|---|---|
| I. Read-Only, No Custody | API only reads/serves already-computed data; no new exchange/order calls | PASS |
| II. No Repaint | Not touched — records post-computation values, doesn't change candle handling | PASS (N/A) |
| III. Validate Heuristic Before Trust | Not applicable — this exposes the score, doesn't change it | PASS (N/A) |
| IV. Secrets Never in VCS/Image | `GET /config` explicitly strips all notifier `required` fields (FR-008); SQLite file and `.env` both gitignored | PASS |
| V. UTC Internally | All `created_at`/`updated_at` timestamps via `datetime.now(timezone.utc)`, same pattern as slices 002/003/006 | PASS |
| VI. Tests Guard the Core Pipeline | New `app/api/` package gets direct test coverage (store + endpoints); this is itself new test-worthy surface, not a bypass of it | PASS |
| VII. Pinned Deps, No Permanent Debug Logging | New deps pinned exactly; FR-011 cleans up 3 more leftover debug prints in files this slice already touches | PASS |

No violations.

## Project Structure

### Documentation (this feature)

```
specs/009-agent-api/
├── spec.md
├── checklists/requirements.md
├── plan.md              (this file)
├── research.md
├── data-model.md
├── quickstart.md
└── tasks.md
```

### Source Code

```
app/api/
├── __init__.py
├── store.py              (AgentStateStore: SQLite schema, thread-safe read/write)
└── server.py              (FastAPI app factory + route handlers)

app/app.py                 (start uvicorn thread, construct+wire AgentStateStore; DEBUG cleanup)
app/behaviour/core.py      (accept state_store, record at existing computation points; DEBUG cleanup)
app/conf.py                (DEBUG cleanup; add Configuration.to_sanitized_dict())
app/agent_state/           (new, gitignored — holds agent_state.db at runtime)
docker-compose.yml         (publish 127.0.0.1:8090:8090; mount ./app/agent_state)
app/requirements-step-2.txt (add fastapi==0.141.1, uvicorn==0.54.0)

tests/api/
├── __init__.py
├── test_store.py
└── test_server.py
```

**Structure Decision**: New `app/api/` package mirrors the existing per-concern package layout
(`app/data/`, `app/analysis/`, `app/notifications/`). The SQLite file lives in its own
`app/agent_state/` directory (not inside the existing `app/data/` Python package, to avoid confusing
a runtime data file with the `data` module).

## Complexity Tracking

*No entries — no constitution violations.*
