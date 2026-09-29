# Tasks: Historical Validation of Wyckoff Spring/Upthrust Signals

**Status**: Done.

## Phase 1: Implementation

- [X] T001 Write `validate_wyckoff_springs.py`: reuse slices 007/011's fetch infrastructure; detect
      events via slice 014's real `detect_springs`/`detect_upthrusts`; compute forward returns at
      24h/72h/7d/14d (FR-001 through FR-003). Validates the raw pattern directly (no `SignalEnhancer`
      scoring involved — matches what the operator's recollection is actually about).
- [X] T002 Run against real Binance data. Sample size (2,839 events, 14 pairs) was more than
      adequate on the first run — no extension needed.

## Phase 2: Reporting

- [X] T003 Write `validation-report.md`: methodology, full results at all four horizons (including a
      win-rate-vs-50%-baseline significance test added specifically for this report), explicit
      fact-check of the operator's "+20-30% over 1-2 weeks" recollection (FR-004: does not replicate),
      explicit comparison to slices 007 and 011 (FR-005), one recommendation.
- [X] T004 Applied FR-006 discipline: no unilateral scoring/gate change. Recorded as a Convergence
      finding for operator sign-off (result is genuinely mixed: real significant win-rate edge, but
      small magnitude that doesn't match the operator's recollection).

## Phase 3: Verification

- [X] T005 Confirmed the existing 144-test suite is unaffected (SC-003).
- [X] T006 [P] Refreshed Graphify project graph.

## Phase 4: Convergence

Assessed 2026-09-28. 6/6 functional requirements verified. SC-001 exceeded (2,839 events, largest
sample of the three validation slices). SC-002 met (concrete numbers at all 4 horizons + explicit
fact-check). SC-003 confirmed (144/144 tests unaffected). SC-004 met (one clear, nuanced
recommendation recorded).

**Result**: genuinely different from slices 007/011 — the raw Spring/Upthrust pattern shows a
statistically significant win-rate edge (52.6%-54.8%, p ranging 0.0001-0.0059) at every one of the
four horizons, the first real directional edge found in this project's three validation slices.
However: (1) `break_relative_volume`-based "confirmation" does not significantly sharpen this edge
(correlation p=0.40-0.87 at every horizon); (2) the operator's specific recollection (+20-30% over
1-2 weeks) does **not** replicate — actual mean/median moves at 7d/14d are well under 1%, with only
~3-4% of individual events landing anywhere near that range.

## Convergence Findings

| ID | Gap Type | Severity | Source | Evidence | Remaining Work |
|----|----------|----------|--------|----------|----------------|
| F1 | unrequested | MEDIUM | This slice's own result | A real, statistically significant win-rate edge exists (unlike 007/011), but it is small and doesn't match the operator's recalled magnitude; `specs/016-.../spec.md`'s conditional gate is ambiguously met (win-rate criterion: yes; "worth building on" in the spirit the operator recalled: not really) | **Operator decision needed**: (a) proceed to slice 016 using the modest validated edge (not the recalled magnitude) as the real basis; (b) hold slice 016 and look for a sharper signal/refinement first; (c) something else. See `validation-report.md` Recommendation. |

**Outcome**: `tasks_appended` — F1 is a decision for the operator, consistent with slices 007/011's
same discipline of not unilaterally acting on a validation result that would change real behavior.
