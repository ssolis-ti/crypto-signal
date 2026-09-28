# Specification Quality Checklist: Correct UTC Start-Date Calculation for Historical Data Fetch

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-28
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs (correct historical data window)
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded (one function; explicitly excludes time_unit format changes)
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

Directly traced to Convergence finding F1 from `specs/002-utc-internal-time/tasks.md`. Root cause
confirmed by reading `exchanges/driver.py::_calculate_start_date`: `datetime.now()` (naive local) is
combined with `.replace(tzinfo=timezone.utc)`, which relabels rather than converts — a classic
Python timezone pitfall. Single call site confirmed (`get_historical_data`, only when `start_date`
is not explicitly passed, which is always true in current usage via `DataManager.get_ohlcv`).
