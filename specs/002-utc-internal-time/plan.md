# Implementation Plan: UTC-Consistent Internal Time Handling

**Branch**: `main` (feature dir `002-utc-internal-time`) | **Date**: 2026-09-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-utc-internal-time/spec.md`

## Summary

Two confirmed spots use naive (timezone-unaware) local `datetime.now()`/`fromtimestamp()`:
`analyzers/utils.py::convert_to_dataframe` (indicator DataFrame index, via a fragile
`strftime('%c')`/`to_datetime` round trip) and `notifications/builder.py`'s anti-spam alert window
(`parse_alert_frequency`/`should_i_alert`). Both are replaced with explicit UTC-aware
construction/comparison. `notifications/builder.py`'s `creation_date` (already correctly
local-at-presentation) is untouched.

## Technical Context

**Language/Version**: Python 3.12+ (existing)

**Primary Dependencies**: `pandas>=2.0.0` (`pandas.to_datetime(..., unit='ms', utc=True)` replaces
the manual conversion — no new package); stdlib `datetime.timezone.utc` replaces naive
`datetime.now()` in `notifications/builder.py` (no new package)

**Storage**: N/A

**Testing**: pytest (introduced in slice 001; `requirements-dev.txt` already exists)

**Target Platform**: Linux container (Docker), Python 3.12-slim

**Project Type**: Single project

**Performance Goals**: No new requirement; `pandas.to_datetime(..., utc=True)` is the vectorized,
faster replacement for the current per-row Python `.apply()` + string round trip.

**Constraints**: Must not change the displayed `creation_date` behavior (FR-003); must not require
`config.yml` changes (FR-004).

**Scale/Scope**: Two files, two focused functions; no schema/API changes.

## Constitution Check

| Principle | Check | Result |
|---|---|---|
| I. Read-Only, No Custody | No exchange/credential code touched. | PASS |
| II. No Repaint | Unrelated to this slice; slice 001's fix is untouched. | N/A |
| III. Validate Before You Trust a Heuristic | No scoring/heuristic changed. | N/A |
| IV. Secrets Never in VCS/Image | Unaffected. | PASS |
| V. UTC Internally, Local Only at Presentation | This *is* the fix for this principle. | PASS (feature purpose) |
| VI. Tests Guard the Core Pipeline | `analyzers/utils.py` (used by every indicator, part of the `IndicatorUtils` god node) and `notifications/builder.py` are both constitution-covered; tests added for both. | PASS |
| VII. Pinned Deps, No Permanent Debug Logging | No new dependency; no debug logging added. | PASS |

No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/002-utc-internal-time/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── tasks.md
```

### Source Code (repository root)

```text
app/
├── analyzers/
│   └── utils.py            # MODIFIED: convert_to_dataframe uses pandas.to_datetime(utc=True)
└── notifications/
    └── builder.py           # MODIFIED: parse_alert_frequency/should_i_alert use UTC;
                              #           creation_date (local-at-presentation) UNCHANGED

tests/
├── analyzers/
│   └── test_utils.py        # NEW
└── notifications/
    └── test_builder.py      # NEW
```

**Structure Decision**: Same single-project layout as slice 001; two new test files mirror the two
modified source files, one level deeper (`tests/<package>/test_<module>.py`), matching the
`tests/data/test_manager.py` precedent set in slice 001.

## Complexity Tracking

*No violations to justify.*
