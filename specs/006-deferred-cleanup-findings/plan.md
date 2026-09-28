# Implementation Plan: Clean Up Deferred Convergence Findings

**Branch**: `main` | **Date**: 2026-09-28 | **Spec**: `specs/006-deferred-cleanup-findings/spec.md`

## Summary

Close three LOW-severity findings deferred by slices 001 and 002: leftover `DEBUG:`-prefixed logging
in `data/manager.py::get_top_pairs`, a naive-datetime bug in `rendering/utils.py::convert_to_dataframe`
(same class already fixed in `analyzers/utils.py` and `exchanges/driver.py`), and two naive-datetime
spots in the unwired `utils/calibration.py::CalibrationLogger`. All three fixes are small, mechanical,
and already fully scoped — no new research needed.

## Technical Context

**Language/Version**: Python 3.11 (unchanged)
**Primary Dependencies**: `pytest==8.3.4` (already pinned), `pandas` (already required)
**Testing**: `pytest`, executed inside `crypto-signal:dev` Docker image, same as prior slices
**Target Platform**: Linux container (Docker), same as production
**Constraints**: zero behavior change beyond the six FRs; zero new dependencies
**Scale/Scope**: 3 production files touched (small diffs each), 3 new/extended test files

## Constitution Check

| Principle | Check | Result |
|---|---|---|
| I. Read-Only, No Custody | No exchange/order code touched | PASS |
| II. No Repaint | Not touched | PASS (N/A) |
| III. Validate Heuristic Before Trust | Not applicable | PASS (N/A) |
| IV. Secrets Never in VCS/Image | Not touched | PASS (N/A) |
| V. UTC Internally | This slice's core purpose for US2/US3 — closes the last two known naive-datetime spots from slice 002's F2/F3 | PASS |
| VI. Tests Guard the Core Pipeline | Adds coverage for `get_top_pairs` (previously untested) and `rendering/utils.py::convert_to_dataframe` (previously untested) | PASS |
| VII. Pinned Deps, No Permanent Debug Logging | This slice's core purpose for US1 — removes leftover debug-investigation logging per the principle's own text | PASS |

No violations.

## Project Structure

### Documentation (this feature)

```
specs/006-deferred-cleanup-findings/
├── spec.md
├── checklists/requirements.md
├── plan.md          (this file)
├── research.md
├── data-model.md
├── quickstart.md
└── tasks.md
```

### Source Code

```
app/data/manager.py          (get_top_pairs: demote/remove debug logging)
app/rendering/utils.py       (convert_to_dataframe: UTC-aware timestamp)
app/utils/calibration.py     (log_ohlcv, _report_anomaly: UTC-aware timestamps)

tests/data/test_manager.py           (extended: TestGetTopPairs)
tests/rendering/__init__.py          (new)
tests/rendering/test_utils.py        (new)
tests/utils/__init__.py              (new)
tests/utils/test_calibration.py      (new)
```

**Structure Decision**: Extends the existing `tests/data/test_manager.py` for US1 (same module
already under test there); adds new `tests/rendering/` and `tests/utils/` packages mirroring the
`app/rendering/` and `app/utils/` packages, consistent with the established
`tests/<package>/test_<module>.py` convention.

## Complexity Tracking

*No entries — no constitution violations.*
