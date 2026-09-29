# Feature Specification: 1D/4h Structural Confluence and Existing-TA Confirmation

**Feature Branch**: `main` (Spec Kit feature directory: `specs/019-wyckoff-confluence-and-ta-confirmation`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "¿Qué mejoras habría al usar fractales en una misma moneda con
diferentes temporalidades? ¿Se ve algún detalle o correlación entre 1M/1W/1D/8h/4h/2h/1h/30m/15m?" →
agreed to test one bounded hypothesis instead of sweeping all nine timeframes (avoids the
multiple-comparisons trap this project has consistently guarded against), plus: "apoyate con las
diversas herramientas de análisis técnico incluidas si nos sirven" — use the project's own existing
indicators (RSI, ADX, etc.) as candidate confirming factors, same discipline as slice 017.

## Why one bounded hypothesis, not a 9-timeframe sweep

A full sweep across 9 timeframes and their pairwise combinations would multiply the
multiple-comparisons risk that slice 017 was specifically designed to guard against (that slice
already found that a related, simpler idea — 1D EMA trend alignment — added almost nothing once
compared against period-relative baseline). This slice tests one specific, theoretically-motivated
hypothesis (true structural confluence: the same Spring/Upthrust pattern recurring on 1D near the
same time as the already-validated 4h event) plus two indicators the codebase already computes
elsewhere (RSI, ADX) as confirming context — not a blind grid search.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Does a same-direction 1D Spring/Upthrust near the same time strengthen the 4h edge? (Priority: P1)

**Why this priority**: This is the actual "fractal" hypothesis from the original research
(`specs/012-.../research.md`): the same structural event recurring at multiple scales is what Wyckoff
practice treats as high-confidence confluence — distinct from (and more specific than) slice 017's
already-tested "is the 1D trend generally up" filter.

**Independent Test**: Reuse slice 017's confirmed extreme-volume 4h event set (330 events). For each,
detect real `WyckoffPrimitives.detect_springs`/`detect_upthrusts` on that pair's 1D OHLCV, and check
whether a same-direction 1D event confirmed within a ±3-day window of the 4h event's confirmation
timestamp exists. Evaluate the "confluence" bucket vs. the rest using the same chronological 70/30
in-sample/out-of-sample split methodology as slice 017.

**Acceptance Scenarios**:

1. **Given** the 330 confirmed 4h events, **When** checked against real 1D Spring/Upthrust detection,
   **Then** each is labeled `confluence=True/False` based on a same-direction 1D event within the
   ±3-day window.
2. **Given** that label, **When** evaluated in-sample and out-of-sample, **Then** the confluence
   bucket's win rate/mean return (and lift over that period's own baseline, per slice 017's
   methodology) is reported honestly whether or not it holds up.

### User Story 2 - Do existing RSI/ADX readings at the event add confirming power? (Priority: P2)

**Why this priority**: The operator asked to use the project's existing TA tools if they help. RSI
extremity was already shown (slice 007) not to work *alone*; testing it *in combination* with the
already-validated volume-confirmed Wyckoff signal is a different, legitimate question — same logic
as slice 017 testing volume/HTF/BTC-regime as refinements on top of the base signal, not from
scratch.

**Independent Test**: For each of the same 330 events, compute RSI(14) and ADX(14) (both already used
elsewhere in this codebase, via `talib`, same library/periods the live indicators use) at the
confirmation candle, and test two candidate filters: RSI extremity aligned with direction
(RSI<35 for hot / RSI>65 for cold — a slightly looser band than the live bot's 30/70 to keep sample
size usable) and ADX(14) >= 25 (a standard "trending, not choppy" threshold) — same in-sample/
out-of-sample evaluation as User Story 1.

**Acceptance Scenarios**:

1. **Given** the event set, **When** RSI-extremity-aligned and ADX-strong-trend filters are each
   evaluated in-sample and out-of-sample, **Then** each is reported with the same lift-over-baseline
   framing as slice 017, regardless of outcome.

### Edge Cases

- A pair with insufficient 1D history for the ±3-day confluence check around an early 4h event: that
  event is labeled `confluence=False` (absence of evidence, not treated as an error) — consistent
  with every prior slice's "insufficient data degrades safely" pattern.
- Same in-sample/out-of-sample minimum-sample-size (30) and actionable-bar (out-of-sample win rate
  ≥60%, p<0.05) as slice 017 — no lowering the bar because fewer filters are being tested this time.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 1D Spring/Upthrust detection MUST use the real, unmodified
  `WyckoffPrimitives.detect_springs`/`detect_upthrusts` (slice 014) run on real 1D OHLCV — not a
  reimplementation.
- **FR-002**: The confluence window (±3 days) MUST be pre-declared before evaluating results (no
  adjusting the window after seeing which one looks best).
- **FR-003**: RSI(14) and ADX(14) MUST be computed via `talib`, the same library every existing
  indicator in this codebase already uses, at the 4h confirmation candle.
- **FR-004**: All three candidate filters (1D confluence, RSI extremity, ADX strength) MUST be
  evaluated with the same chronological 70/30 in-sample/out-of-sample split and reported whether or
  not they hold up (same discipline as slice 017's FR-002/FR-003).
- **FR-005**: This feature MUST NOT wire anything into `SignalEnhancer`, `Behaviour`, or `notify_all`
  — same Principle III discipline as every prior validation slice.
- **FR-006**: The report MUST give one clear recommendation combining this slice's findings with
  slices 017/018's still-pending operator decision — not a separate, disconnected conclusion.

### Key Entities

- Extends slice 017's `FilterEvaluation` shape with three new candidates: `confluence_1d`,
  `rsi_extreme`, `adx_strong`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All three candidates evaluated in-sample and out-of-sample with concrete numbers.
- **SC-002**: One unambiguous recommendation: either a specific validated combination is named as
  ready for the still-pending Telegram-alert decision, or the report states none of these three added
  anything beyond what slice 017 already found.
- **SC-003**: The existing test suite is unaffected (research artifact, consistent with all prior
  validation slices).

## Assumptions

- RSI/ADX thresholds (35/65 for RSI, 25 for ADX) are standard, commonly-cited values chosen before
  running — not tuned after seeing results.
- "1D near the same time" (±3 days) is a reasonable window given 1D events are naturally less
  frequent than 4h events (a 1D range takes longer to build/break) — not swept/optimized.
