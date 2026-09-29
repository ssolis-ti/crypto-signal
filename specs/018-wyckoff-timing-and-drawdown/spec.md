# Feature Specification: Timing and Drawdown Risk of the Extreme-Volume Wyckoff Signal

**Feature Branch**: `main` (Spec Kit feature directory: `specs/018-wyckoff-timing-and-drawdown`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Ojo acá viene el ajuste y la precisión del aviso, en qué momentos
desde que me notifica tengo tiempo para capturar una subida fuerte o bajada. Ya que con
apalancamiento podría tener ganancia solo en unos segundos o minutos." Slice 017 validated that a
Spring/Upthrust confirmed by extreme break-candle volume (≥2.5x average) shows a real, holdout-tested
~60% win rate and +2.36% mean return **measured only at a single point 14 days later** — it says
nothing about *when* within those 14 days the move actually happens, nor how much adverse movement
(drawdown) occurs first. For someone trading with leverage, both of those facts matter more than the
14-day endpoint: a position can be liquidated by an adverse move long before a favorable 14-day
average materializes, and "when is it safe/worth entering" is a completely different question from
"is the 14-day expected value positive."

## Why this is a distinct, necessary slice (not scope creep on 017)

Slice 017 answered "does a real edge exist." This slice answers "is that edge usable by someone
trading with leverage, and if so, on what time horizon and with what risk of being stopped out
first." These are genuinely different questions requiring different data (finer time resolution) and
different metrics (path-dependent: drawdown-before-profit, time-to-first-profit) rather than a
single end-of-window return.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Map how the price move actually unfolds after the alert, hour by hour (Priority: P1)

**Why this priority**: Directly answers "how much time do I have to act, and does the edge show up
fast or slow" — the operator's literal question.

**Independent Test**: For every slice 017 "confirmed filter" event (extreme break volume ≥2.5x,
combining in-sample and out-of-sample since this is a different question, not re-testing whether the
edge exists), fetch real 1-hour OHLCV covering the 14 days following the event's confirmation candle,
and compute the cumulative expected-direction return at a sequence of checkpoints: 1h, 2h, 4h, 8h,
12h, 24h, 48h, 72h, 7d, 14d.

**Acceptance Scenarios**:

1. **Given** the set of confirmed events, **When** the cumulative return is computed at each
   checkpoint, **Then** the report shows, per checkpoint, the mean/median return and win rate — a
   "growth curve" of the edge over time, not just its 14-day endpoint.
2. **Given** that curve, **When** the report concludes, **Then** it states plainly whether the edge
   is concentrated early (most of the 14-day gain already present within the first 24-48h) or
   develops slowly (little edge until much later) — this is the direct answer to "how much time do I
   have."

### User Story 2 - Measure drawdown risk before any profit, for leverage/stop-placement sizing (Priority: P1)

**Why this priority**: A leveraged position can be liquidated by an adverse move that happens before
the eventual favorable move — the 14-day mean return alone says nothing about whether the path there
would have wiped out a leveraged account first.

**Independent Test**: For each event, compute the Maximum Adverse Excursion (MAE — the worst
cumulative expected-direction return reached before each checkpoint) and Maximum Favorable Excursion
(MFE) using the same 1h path data.

**Acceptance Scenarios**:

1. **Given** the event set, **When** MAE is computed up to the 24h/48h/72h/7d/14d checkpoints,
   **Then** the report shows the distribution (median, and what fraction of events breached
   representative adverse thresholds — e.g., -2%, -5%, -10% — since with leverage even a small
   adverse move against an under-margined position can force liquidation).
2. **Given** the same events, **When** MFE is computed, **Then** the report shows how much of the
   eventual favorable move was available at its peak, and at what typical time offset that peak
   occurred (useful for a realistic take-profit expectation, distinct from the 14-day average).

### Edge Cases

- 1h OHLCV may not be available/complete for the full 14-day window for every event (exchange
  gaps, pair delisted mid-window) — such events are excluded from that specific checkpoint's
  aggregation (same `None`-if-insufficient-data pattern as every prior validation slice), not
  padded or estimated.
- This analysis explicitly CANNOT answer true second-or-minute-level execution timing (order
  fills, slippage, latency) — 1-hour candles are the finest resolution this slice fetches, chosen as
  a defensible, fetchable middle ground; the report MUST say plainly that genuine sub-hour timing
  requires live paper-trading or tick/order-book data, not a historical-candle backtest, so the
  operator doesn't read more precision into this than the data actually supports.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The analysis MUST use the real event set slice 017 identified as "confirmed" (extreme
  break-candle volume ≥2.5x), combining in-sample and out-of-sample subsets for maximum sample size
  — this slice is not re-testing whether the edge exists, only characterizing its timing/risk.
- **FR-002**: The analysis MUST use real 1-hour OHLCV (finer than the 4h resolution used to detect
  the events themselves) covering each event's 14-day forward window.
- **FR-003**: The analysis MUST report cumulative expected-direction return at a pre-declared sequence
  of checkpoints (1h through 14d, listed in User Story 1) — not cherry-picked after seeing the shape.
- **FR-004**: The analysis MUST report MAE and MFE per event, aggregated (median, and threshold-
  breach rates for MAE, since that is the leverage-relevant risk metric).
- **FR-005**: The report MUST explicitly state the resolution boundary (FR per Edge Cases): this
  characterizes hourly-scale timing, not second/minute-scale execution — and MUST NOT imply otherwise.
- **FR-006**: This feature MUST NOT wire anything into a live alert path — same discipline as every
  prior validation slice (Constitution Principle III). Its output feeds a go/no-go and
  risk-parameter decision for whatever follow-up implementation slice the operator approves.

### Key Entities

- **`EventPath`**: per event, a Series of cumulative expected-direction returns at each 1h step from
  the confirmation candle to +14 days, plus derived `MAE`/`MFE` and the checkpoint values.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The full checkpoint curve (mean/median/win-rate at each of the 10 pre-declared
  checkpoints) is reported with concrete numbers.
- **SC-002**: MAE/MFE distributions and threshold-breach rates are reported with concrete numbers.
- **SC-003**: The report states one clear conclusion about usable time horizon and leverage risk —
  e.g., "most of the edge is present by Xh, but typical adverse excursion before that point is Y%,
  implying leveraged positions need at least Z% margin/stop room" — not left as raw numbers without
  a stated takeaway.
- **SC-004**: The existing test suite is unaffected (research artifact, consistent with all prior
  validation slices).

## Assumptions

- "Expected-direction return" and "confirmation candle as t=0" carry over unchanged from slices
  007/011/015/017.
- 1-hour resolution is a deliberate, stated compromise (fetchable in reasonable time for ~200+
  events across multiple pairs, while being 4x finer than the 4h detection resolution) — not a claim
  that it resolves true intrabar/second-level timing (see FR-005).
