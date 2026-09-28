# Phase 0 Research: Read-Only Agent Integration API

## Decision: Run FastAPI/uvicorn in a daemon thread inside the same process, not a separate container

**Rationale**: The analysis workers, `Behaviour`, and everything they compute already live in one
Python process (`app.py`'s `main()`). Running the API in-process lets it share the same
`AgentStateStore` instance directly (or via the same SQLite file) with zero IPC. `uvicorn.Server`
supports being driven manually (`server.run()` in a thread, or `asyncio.run(server.serve())` on a
dedicated event loop in a thread) without needing its own process. A separate container/process would
require a network or file-based handoff for no real benefit here, since both share one host anyway.

**Alternatives considered**: A second container in `docker-compose.yml` reading the same SQLite file
via a shared volume — rejected: adds a second image/process to build, deploy, and monitor for a
feature whose entire value is "cheap observability," not a separately-scalable service.

## Decision: SQLite with a single global write lock, not per-thread connections

**Rationale**: Writes happen at most once per worker per `update_interval` (default 300s) — orders of
magnitude below any real contention concern. A single `threading.Lock` guarding a short-lived
`sqlite3.connect(...)` per write (open, write, commit, close) avoids `sqlite3.ProgrammingError:
SQLiteObjects created in a thread can only be used in that same thread` without needing a
connection-pool library. Reads (from the FastAPI handler thread) open their own short-lived read
connection — SQLite's default rollback-journal mode allows concurrent readers alongside the
occasional writer without special configuration at this write frequency.

**Alternatives considered**: WAL mode for higher write concurrency — unnecessary at this write
frequency; adds a mode-specific journal file to explain/gitignore for no measurable benefit here.

## Decision: Indicator/informant snapshots are "latest value only" (upsert), not append-only history

**Rationale**: Per spec Assumptions — an unbounded per-cycle, per-pair, per-indicator history table
would grow linearly forever (e.g., 20 pairs × ~10 indicators × 1 write/5min = ~57,600 rows/day) for a
stated use case ("what does the bot see right now") that only needs current state. Signals and market
context, by contrast, are explicitly valuable as history (a signal is a discrete decision-relevant
event; market context has a natural "how has BTC trended today" query shape) — those two are
append-only.

**Alternatives considered**: Also making indicator snapshots append-only with periodic pruning —
rejected as unneeded complexity (a pruning job, a retention policy) for a use case the operator never
asked for; can be added later if a real need for indicator history surfaces.

## Decision: `Configuration.to_sanitized_dict()` explicitly allow-lists what's exposed, not deny-lists

**Rationale**: For `GET /config` (FR-008), building the response by starting from the full config and
trying to delete every secret field is fragile — a future notifier type with a differently-named
secret field would leak by default. Instead, the sanitized dict is built by explicitly copying
`settings`, `indicators`, `informants`, `crossovers`, plus (for `notifiers` and `exchanges`) only the
non-`required` structure and the list of which notifier/exchange keys are enabled — never touching any
`required` block's contents at all, so nothing there can ever leak regardless of its field names.

**Alternatives considered**: A recursive "mask any key named token/password/chat_id/url" scrubber —
rejected: pattern-matching key names is exactly the kind of thing that silently stops working when a
new secret field doesn't match the pattern (e.g., a future notifier's `api_secret`).

## Decision: Publish the port as `127.0.0.1:8090:8090`, not `8090:8090`

**Rationale**: Docker's port-publishing syntax `HOST_IP:HOST_PORT:CONTAINER_PORT` — specifying
`127.0.0.1` as the host IP makes Docker bind the published port only to the host's loopback interface,
so it is unreachable from the LAN or internet even though the container's own internal listener is on
`0.0.0.0` (required for Docker's internal proxy to reach it at all). This directly implements the
operator's "no auth, host-only" decision at the network layer, which is more robust than an
application-level check.

**Alternatives considered**: Binding uvicorn itself to `127.0.0.1` inside the container — rejected: a
container's own loopback is not reachable through Docker's port-forwarding from the host at all, so
the API would be completely unreachable even from the host; the host-only restriction must be applied
at the `docker-compose.yml` port-publishing level, not inside the container.
