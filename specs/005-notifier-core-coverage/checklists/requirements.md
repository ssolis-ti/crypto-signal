# Specification Quality Checklist: Test Coverage for notifications/core.py::Notifier

**Created**: 2026-09-28 | **Feature**: `specs/005-notifier-core-coverage`

## Content Quality

- [X] No implementation details leak into requirements beyond naming the module/methods under test
- [X] Focused on operator-observable correctness (channels actually fire, webhook actually delivers)
- [X] Written for a reviewer who knows the codebase, consistent with slices 001-004
- [X] All mandatory sections completed

## Requirement Completeness

- [X] No `[NEEDS CLARIFICATION]` markers remain
- [X] Requirements are testable (each FR maps to specific Acceptance Scenarios)
- [X] Success criteria are measurable (pass/fail, regression-proof for the bug fix, zero-network)
- [X] Out-of-scope items explicitly named (FR-007: builder's message construction, TA modules)
- [X] Assumptions section justifies the one production-code change (notify_webhook fix) against
      slice 004's coverage-only precedent

## Feature Readiness

- [X] Each of the 4 user stories has a clear, independently runnable test
- [X] The discovered bug (webhook chart_file not forwarded) is documented with its exact failure mode
      and root-caused before being scheduled as a fix
- [X] Scope matches Constitution Principle VI while respecting bounded-slice discipline

## Notes

Bug found by reading source before writing tests (same discipline as prior slices): `notify_webhook`
in `app/notifications/core.py` drops its `chart_file` parameter instead of forwarding it to
`WebhookNotifier.notify(messages, chart_file)`, which has no default for that parameter — an
unconditional `TypeError` on every webhook send. Fixed inline per Assumptions.
