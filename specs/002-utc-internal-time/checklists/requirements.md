# Specification Quality Checklist: UTC-Consistent Internal Time Handling

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-28
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs (deployment robustness, alert correctness)
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified (explicitly protects the one correct existing local-time usage)
- [x] Scope is clearly bounded (two confirmed spots only; no other timezone code touched)
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

Grounded in confirmed current behavior: `analyzers/utils.py::convert_to_dataframe` (naive
`datetime.fromtimestamp` + locale `strftime('%c')` round trip) and
`notifications/builder.py::parse_alert_frequency`/`should_i_alert` (naive `datetime.datetime.now()`)
found by direct code search before writing this spec. `notifications/builder.py`'s `creation_date`
(line ~179) was confirmed to already do the *correct* thing and is explicitly excluded (FR-003).

## Addendum (post-implementation)

While writing tests, found that `convert_to_dataframe([])` already raised `ValueError` **before**
this slice's change (the pre-existing column-assignment line fails on a 0x0 DataFrame, unrelated to
the datetime conversion this slice touches). Empty input never reaches this function in practice —
`behaviour/strategies.py` already guards with `if historical_data_cache[candle_period]:` before
calling any indicator. Not fixed here (out of scope for a UTC-consistency slice); tracked as a
Convergence finding in `tasks.md` for a future slice.
