# Tasks: Pin Direct Dependencies for Reproducible Builds

## Phase 1: Implementation

- [X] T001 Pin `app/requirements-step-1.txt`'s `numpy`/`Cython` to their exact installed versions.
- [X] T002 Pin `app/requirements-step-2.txt`'s 14 direct deps to their exact installed versions.
- [X] T003 `grep ">=" app/requirements-step-1.txt app/requirements-step-2.txt` returns nothing (SC-001).

## Phase 2: Verification

- [X] T004 Rebuild `crypto-signal:dev` from scratch (`--no-cache`) (SC-002).
- [X] T005 Run the full test suite inside the freshly-rebuilt image; confirm 88/88 pass (SC-003).

## Phase 3: Convergence

Assessed 2026-09-28. 4/4 FR verified. SC-001/002/003 verified directly. 1/1 relevant constitution
principle (VII) satisfied. No new findings.

**Outcome**: `converged`.
