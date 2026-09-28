# Specification Quality Checklist: Correct btc_change_1h to a Real 1-Hour Percentage Change

**Created**: 2026-09-28 | **Feature**: `specs/010-btc-change-1h-fix`

## Content Quality

- [X] No implementation details leak into requirements beyond the data source change (ticker field
      → real OHLCV) that IS the fix
- [X] Focused on the observable outcome (the field means what its name says)
- [X] Written for a reviewer who knows the codebase, consistent with slices 001-009
- [X] All mandatory sections completed

## Requirement Completeness

- [X] No `[NEEDS CLARIFICATION]` markers — root cause and fix already fully scoped by slice 009's
      Convergence finding F1
- [X] Requirements are testable (each FR maps to an Acceptance Scenario)
- [X] Success criteria are measurable (test pass/fail, regression-proof, live-value sanity bound)
- [X] Out-of-scope explicitly named (FR-004: no other MarketContextData field touched)
- [X] Assumptions state the exact 1h-window definition and the one new cached network call

## Feature Readiness

- [X] User Story 1 covers normal operation, both failure modes, and the specific regression
- [X] Edge cases (single candle, zero-price) enumerated
- [X] Scope matches Constitution Principle VI (`analysis/` requires tests; `MarketContext` had zero
      before this slice) and Principle II (no repaint — reuses `DataManager`'s existing guarantee
      rather than reimplementing it)

## Notes

Root cause already fully diagnosed in `specs/009-agent-api/tasks.md` Convergence Finding F1 — this
slice is implementation + tests against an already-understood bug, not new investigation.
