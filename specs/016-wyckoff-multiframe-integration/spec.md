# Feature Specification: Multi-Timeframe Wyckoff Integration (Conditional)

**Feature Branch**: `main` (Spec Kit feature directory: `specs/016-wyckoff-multiframe-integration`)

**Created**: 2026-09-28

**Status**: Draft, CONDITIONAL — **awaiting operator decision.** `specs/015-wyckoff-historical-validation`
landed 2026-09-28 with a genuinely mixed result (see its `validation-report.md` and Convergence
Finding F1): a real, statistically significant win-rate edge exists (52.6%-54.8% across all four
horizons, unlike slices 007/011's null/negative results) — but the effect is small, doesn't sharpen
with volume-confirmation, and does not replicate the magnitude the operator specifically recalled
(+20-30% over 1-2 weeks). This is NOT a clean "validated, proceed" nor a clean "invalidated, stop" —
per Constitution Principle III, whether to build this integration on the smaller, real-but-modest
edge slice 015 actually found is an operator call, not something to proceed on unilaterally.

**Input**: Fourth and final slice of the roadmap in `specs/012-wyckoff-fractal-research/research.md`
— top-down multi-timeframe composition (1D/1W structural bias filtering 4h Spring/Upthrust triggers),
the "fractal" half of the original research question, gated behind validation succeeding first.

## Why this is written now but not built now

Slices 013 and 014 are pure, unwired, informational primitives (explicitly no alert impact).
Slice 015 is the validation gate. This slice (016) is the only one of the four that would actually
touch `SignalEnhancer`, `Behaviour`, or `notify_all` — i.e., the only one with real blast radius on
live Telegram alerts. Writing its spec now, before knowing slice 015's result, lets the operator see
the full shape of the roadmap end-to-end for planning purposes, while the CONDITIONAL status makes
explicit that "spec exists" is not "approved to build."

## User Scenarios & Testing *(mandatory, drafted provisionally)*

### User Story 1 - Higher-timeframe structural bias gates lower-timeframe Wyckoff triggers

**Independent Test** (provisional, to be finalized against whatever slice 015 actually validates):
Compute a `structural_bias` (accumulation-leaning / distribution-leaning / undefined) from 1D OHLCV
using the same `WyckoffPrimitives` range/climax primitives (slices 013/014) at that higher timeframe,
and confirm that 4h Spring/Upthrust events aligned with that bias perform differently (per slice 015's
own validated metric) than misaligned ones — i.e., this slice's job is to test the *composition*, not
to assume it works because the parts individually validated.

### Edge Cases

To be finalized once slice 015's actual event/outcome shape is known — provisionally: insufficient
1D history for a newly-listed pair (no bias available, treat as `undefined`, never block the 4h
signal outright since it's informational until this slice's own validation, per FR-001 below).

## Requirements *(mandatory, provisional)*

- **FR-001**: This feature MUST NOT change `notify_all`'s alert gating or `SignalEnhancer`'s scoring
  until its own composed (multi-timeframe) signal has been historically validated the same way as
  slice 015 validated the single-timeframe version — passing the individual pieces' validation does
  NOT imply the composition validates; composition effects MUST be tested, not assumed.
- **FR-002**: If slice 015 concludes no measurable predictive value for single-timeframe Spring/
  Upthrust events, this feature MUST be re-scoped or shelved — building a multi-timeframe filter on
  top of an already-invalidated single-timeframe signal is not a sound next step, per the same logic
  that stopped this project from layering more weights onto `SignalEnhancer` after slices 007/011.
- **FR-003** *(if slice 015 validates)*: `DataManager.get_ohlcv` (already supports arbitrary
  timeframes) MUST be reused for the higher-timeframe fetch — no new exchange/data-access layer.

## Success Criteria *(provisional)*

- **SC-001**: This spec is either (a) rewritten with concrete, validated requirements once slice 015
  lands with a positive result, or (b) formally closed/retired with a one-line note if slice 015 does
  not validate — in neither case does it silently sit as "TODO" forever.

## Assumptions

- Everything here is provisional and explicitly subject to revision once slice 015's actual findings
  exist — this document intentionally avoids over-specifying an integration whose premise (that the
  underlying signal has real predictive value) is not yet established.
