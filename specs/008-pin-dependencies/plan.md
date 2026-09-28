# Implementation Plan: Pin Direct Dependencies for Reproducible Builds

**Branch**: `main` | **Date**: 2026-09-28 | **Spec**: `specs/008-pin-dependencies/spec.md`

## Summary

Replace every `>=` pin on a direct dependency in `app/requirements-step-1.txt` and
`app/requirements-step-2.txt` with `==` at the exact version currently installed in
`crypto-signal:dev` (captured via `pip freeze`, cross-checked against each file's own package list).
Rebuild the image from scratch and re-run the full suite to confirm nothing shifts.

This slice skips `research.md`/`data-model.md` (no design decision to record — this is a mechanical
pin at status-quo versions, per FR-003) and `quickstart.md` (the validation steps are the two
Acceptance Scenarios, reproduced directly in `tasks.md`).

## Constitution Check

| Principle | Check | Result |
|---|---|---|
| VII. Dependencies Are Pinned | This slice's entire purpose | PASS |
| I / II / III / IV / V / VI | Not touched by a dependency-version-string-only change | PASS (N/A) |

No violations.

## Project Structure

```
app/requirements-step-1.txt   (pin numpy, Cython)
app/requirements-step-2.txt   (pin all 14 direct deps)
```
