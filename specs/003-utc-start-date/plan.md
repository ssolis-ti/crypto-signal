# Implementation Plan: Correct UTC Start-Date Calculation for Historical Data Fetch

**Branch**: `main` (feature dir `003-utc-start-date`) | **Date**: 2026-09-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-utc-start-date/spec.md`

## Summary

`CCXTDriver._calculate_start_date` (`app/exchanges/driver.py`) computes
`datetime.now() - (max_periods * delta)` then `.replace(tzinfo=timezone.utc)`. `.replace(tzinfo=...)`
relabels a naive value without converting it, so if `datetime.now()` is ever not already numerically
equal to UTC (i.e., host system timezone isn't UTC), the result is silently wrong by the host's UTC
offset. Fix: read "now" as UTC-aware from the start —
`datetime.now(timezone.utc) - (max_periods * delta)` — and drop the now-unnecessary `.replace(...)`.
`timezone` is already imported in this file (used correctly elsewhere is not the case, but the
import already exists), so no new import is needed.

## Technical Context

**Language/Version**: Python 3.12+ (existing)

**Primary Dependencies**: stdlib `datetime` only; no new package.

**Storage**: N/A

**Testing**: pytest (existing `requirements-dev.txt`)

**Target Platform**: Linux container (Docker), Python 3.12-slim

**Project Type**: Single project

**Performance Goals**: No change; identical arithmetic cost.

**Constraints**: Must not change `time_unit` parsing, the period map, or the `ValueError` path
(FR-003); must not change the function signature or caller (FR-004).

**Scale/Scope**: One function, `app/exchanges/driver.py::_calculate_start_date`.

## Constitution Check

| Principle | Check | Result |
|---|---|---|
| I. Read-Only, No Custody | Pure arithmetic; no exchange instance or credential involved. | PASS |
| II. No Repaint | Unrelated; not touched. | N/A |
| III. Validate Heuristic | No heuristic changed. | N/A |
| IV. Secrets | Unaffected. | PASS |
| V. UTC Internally | This is the fix (closes slice 002's F1 finding). | PASS (feature purpose) |
| VI. Tests Guard Core Pipeline | `exchanges/driver.py` isn't in the constitution's explicit list (`analysis/`, `data/`, `notifications/`), but it is directly upstream of `data/manager.py`'s `get_ohlcv` (already tested in slice 001) and is exactly the kind of correctness bug Principle V exists to prevent — tests are added anyway, consistent with the spirit of Principle VI. | PASS |
| VII. Pinned Deps / No Debug Logging | No new dependency; no debug logging added. | PASS |

No violations.

## Project Structure

### Documentation (this feature)
```text
specs/003-utc-start-date/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── tasks.md
```

### Source Code (repository root)
```text
app/
└── exchanges/
    └── driver.py             # MODIFIED: _calculate_start_date uses UTC-aware "now"

tests/
└── exchanges/
    ├── __init__.py            # NEW
    └── test_driver.py         # NEW
```

**Structure Decision**: Same pattern as slices 001/002 — `tests/<package>/test_<module>.py` mirrors
the modified source file.

## Complexity Tracking

*No violations to justify.*
