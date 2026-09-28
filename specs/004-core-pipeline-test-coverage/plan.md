# Implementation Plan: Test Coverage for Untested Pure-Logic Core Modules

**Branch**: `main` | **Date**: 2026-09-28 | **Spec**: `specs/004-core-pipeline-test-coverage/spec.md`

## Summary

Add unit tests for five previously-untested modules across `analyzers/`, `data/`, and
`notifications/`: `CrossOver`, `PairResolver`, `NotificationQueue`, `SmartNotificationManager`, and
`ConfigValidator`. All five expose pure or dependency-injected logic (no direct network/exchange
calls at the tested layer), so no mocking framework beyond simple stub functions/objects is needed.
No production code changes are planned; this is a coverage-only slice.

## Technical Context

**Language/Version**: Python 3.11 (per Dockerfile base image, unchanged from slices 001-003)
**Primary Dependencies**: `pytest==8.3.4` (already in `requirements-dev.txt`), `pandas`/`numpy`
(already required by `analyzers/crossover.py`)
**Testing**: `pytest`, executed inside the `crypto-signal:dev` Docker image exactly as slices 001-003
**Target Platform**: Linux container (Docker), same as production
**Project Type**: single backend service
**Performance Goals**: N/A (test-only change)
**Constraints**: Tests must not require network, Telegram, or exchange credentials (FR-007)
**Scale/Scope**: 5 test files, ~20-25 test cases total

## Constitution Check

| Principle | Check | Result |
|---|---|---|
| I. Read-Only, No Custody | No new exchange/order code; tests use fake pair lists and fake OHLCV-shaped DataFrames only | PASS |
| II. No Repaint | Not touched by this slice (already covered by slices 001-003) | PASS (N/A) |
| III. Validate Heuristic Before Trust | Not applicable — no new scoring/heuristic introduced | PASS (N/A) |
| IV. Secrets Never in VCS/Image | Tests use dummy strings (`'fake-token'`) never real credentials, and `ConfigValidator` tests never touch `.env`/`config.yml` | PASS |
| V. UTC Internally | `NotificationQueue`/`SmartNotificationManager` tests use `time.time()`-based state incidentally; no new naive-datetime usage introduced | PASS |
| VI. Tests Guard the Core Pipeline | This slice's entire purpose — directly satisfies the principle for `analysis/`/`data/`/`notifications/` files not yet covered | PASS |
| VII. Pinned Deps, No Permanent Debug Logging | No new dependencies added (pytest already pinned); no debug logging added | PASS |

No violations. No Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```
specs/004-core-pipeline-test-coverage/
├── spec.md
├── checklists/requirements.md
├── plan.md          (this file)
├── research.md
├── data-model.md
├── quickstart.md
└── tasks.md
```

### Source Code (repository root is `app/`, tests live in sibling `tests/`)

```
tests/
├── analyzers/
│   └── test_crossover.py      (new)
├── data/
│   └── test_pair_resolver.py  (new)
└── notifications/
    ├── test_queue.py           (new)
    ├── test_smart.py           (new)
    └── test_validator.py       (new)
```

**Structure Decision**: Mirrors the existing `tests/<package>/test_<module>.py` convention
established in slices 001-003 (`tests/data/test_manager.py`, `tests/analyzers/test_utils.py`,
`tests/notifications/test_builder.py`, `tests/exchanges/test_driver.py`). `tests/analyzers/__init__.py`
and `tests/notifications/__init__.py` already exist; `tests/data/__init__.py` already exists.

## Complexity Tracking

*No entries — no constitution violations.*
