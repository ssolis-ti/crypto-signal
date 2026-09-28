# Implementation Plan: Eliminate Signal Repaint

**Branch**: `main` (feature dir `001-no-repaint-signals`) | **Date**: 2026-09-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-no-repaint-signals/spec.md`

## Summary

Every indicator/informant/crossover consumes raw OHLCV data that includes the currently-forming
(unclosed) candle as its last row, and every notification/output consumer reads that last row via
`iloc[-1]` as "the current signal." Fix is applied once at the data boundary: `DataManager.get_ohlcv`
(`app/data/manager.py`) trims any trailing candle whose close time (start timestamp + period
duration, both timezone-aware UTC) has not yet passed, before caching and returning the series.
Period duration comes from `ccxt.Exchange.parse_timeframe(timeframe)` (a static utility, requires no
API credentials — consistent with Constitution Principle I). No other module needs to change:
`StrategyExecutor`, all indicator classes, `outputs.py`, and `notifications/builder.py` already treat
"the last row" as authoritative, so once the last row is guaranteed closed, the existing `iloc[-1]`
reads become correct by construction (FR-003).

## Technical Context

**Language/Version**: Python 3.12+ (per README/Dockerfile; existing codebase)

**Primary Dependencies**: `ccxt>=4.0.0` (already a dependency; `Exchange.parse_timeframe` used, no
new package), `pandas>=2.0.0` (already used for the OHLCV → DataFrame conversion downstream)

**Storage**: N/A — in-memory only (`DataCache`, TTL-based, no persistence)

**Testing**: pytest — **NEW to this repo** (no test infrastructure exists today; see Constitution
Principle VI, which requires tests for `data/`, `analysis/`, `notifications/` starting with the
first change that touches any of them). Added as a dev-only dependency, not shipped in the runtime
image.

**Target Platform**: Linux container (Docker), Python 3.12-slim base image

**Project Type**: Single project — background worker (no CLI/web surface for this feature)

**Performance Goals**: No new performance requirement; trimming one row from an already-fetched,
already-cached series is O(1) relative to existing per-cycle exchange I/O (the dominant cost).

**Constraints**: Must not add exchange calls (no extra `fetch_time`/server-time round trip); must
use timestamps already present in the OHLCV response plus a pure, offline timeframe-duration lookup,
per FR-006 and the Assumptions section of the spec (current time = UTC wall clock at fetch time).

**Scale/Scope**: Touches one method (`DataManager.get_ohlcv`) and one new small pure helper; no
schema, API, or config changes (FR-004).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Read-Only, No Custody | `ccxt.Exchange.parse_timeframe` is a `@staticmethod`; no exchange instance, no API key, no order-capable call is introduced. | PASS |
| II. No Repaint | This *is* the fix for this principle. | PASS (feature purpose) |
| III. Validate Before You Trust a Heuristic | Not applicable — no scoring/weighting heuristic is introduced or changed by this slice. | N/A |
| IV. Secrets Never in VCS/Image | No credentials touched. | PASS |
| V. UTC Internally, Local Only at Presentation | The closed-candle determination explicitly uses UTC-aware timestamps derived from exchange data, independent of `settings.timezone`. | PASS |
| VI. Tests Guard the Core Pipeline | `data/manager.py` is directly modified → tests are mandatory for this change (new: `tests/data/test_manager.py`), covering normal trim, "already closed, no trim," short-history edge case, and a regression test for the exact repaint scenario from User Story 1. | PASS (addressed in Phase 1 / tasks) |
| VII. Pinned Deps, No Permanent Debug Logging | `pytest` added as a pinned dev dependency (`requirements-dev.txt`, new file, not installed in the production image); no debug prints introduced. | PASS |

No violations requiring Complexity Tracking justification beyond the test-infrastructure addition,
which the constitution itself mandates rather than forbids.

## Project Structure

### Documentation (this feature)

```text
specs/001-no-repaint-signals/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output (module-boundary contract, no network API here)
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── data/
│   └── manager.py       # MODIFIED: get_ohlcv trims unclosed trailing candle
├── exchanges/
│   └── driver.py        # UNCHANGED (reference: already imports ccxt, already timezone-aware
│                         # for _calculate_start_date; no new coupling needed there)
└── ...                  # all other modules UNCHANGED (fix is transparent to them)

tests/                    # NEW top-level directory (sibling to app/, matches Dockerfile's
├── __init__.py           # `COPY ./app /app` so tests are not baked into the runtime image)
└── data/
    └── test_manager.py   # NEW: unit tests for the closed-candle trim behavior

requirements-dev.txt       # NEW: pytest pin, not referenced by Dockerfile
```

**Structure Decision**: Single project, matching the existing repository layout exactly. `tests/`
is added at the repository root (outside `app/`) so the Dockerfile's `COPY ./app /app` continues to
produce a runtime image with no test code or dev dependency, with zero Dockerfile changes required
for this slice.

## Complexity Tracking

*No Constitution violations to justify. The only structural addition (test infrastructure) is
required by Principle VI, not an exception to it.*
