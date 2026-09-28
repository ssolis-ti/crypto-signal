# Feature Specification: Trading Range, Spring, and Upthrust Detection

**Feature Branch**: `main` (Spec Kit feature directory: `specs/014-wyckoff-range-spring-upthrust`)

**Created**: 2026-09-28

**Status**: Draft — **blocked on `specs/013-wyckoff-effort-result` landing** (this slice consumes
`WyckoffPrimitives.effort_result_ratio`/`is_climax` as inputs to the test-volume confirmation logic
below).

**Input**: Second buildable slice of the roadmap in
`specs/012-wyckoff-fractal-research/research.md`: trading-range detection and the two most
citable, rules-expressible Wyckoff chart patterns — the **Spring** (false breakdown below range
support that reverses back inside) and the **Upthrust** (false breakout above range resistance that
reverses back inside). The research explicitly flagged these as "high objectivity" candidates
(unlike full A-E phase labeling, which stays out of scope per that document's honesty section).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detect the currently active trading range (Priority: P1)

**Why this priority**: A spring/upthrust is only meaningful relative to an established range; without
first identifying "what is the range," any breakout/breakdown detection is arbitrary.

**Independent Test**: Given an OHLCV series with a visually obvious horizontal consolidation followed
by a breakout, the range-detection function returns a `(support, resistance)` pair matching the
consolidation's actual low/high, and a `range_width_pct` (width relative to price) that narrows as
the consolidation tightens.

**Acceptance Scenarios**:

1. **Given** N candles whose closes stay within a horizontal band, **When** range detection runs,
   **Then** `support` and `resistance` equal (within tolerance) the rolling min/max of that band over
   the lookback window.
2. **Given** a lookback window shorter than the available history, **When** range detection runs,
   **Then** it uses only that window (no lookahead into future candles — Constitution Principle II
   discipline extended to this new analytical surface, even though it isn't live-candle repaint in
   the original sense).
3. **Given** insufficient history for the lookback window, **When** range detection runs, **Then** it
   returns `None`/`NaN` rather than a misleading partial range.

### User Story 2 - Detect Spring and Upthrust events against that range (Priority: P1)

**Why this priority**: This is the actual pattern the research identifies as rules-expressible and
worth testing; it is the direct input to slice 015's validation.

**Independent Test**: Given a synthetic OHLCV fixture engineered to contain an unambiguous spring
(a candle piercing below the established support, followed within K candles by a close back above
support) and an unambiguous upthrust (the mirror above resistance), the detector flags exactly those
candles and no others in a fixture with no such pattern.

**Acceptance Scenarios**:

1. **Given** a candle whose low breaks below the established `support` by at least a configurable
   margin, **When**, within a configurable number of subsequent candles, the close returns above
   `support`, **Then** that return candle is flagged `is_spring`.
2. **Given** the mirror condition above `resistance`, **When** the close returns below `resistance`
   within the window, **Then** that candle is flagged `is_upthrust`.
3. **Given** a breakdown that does NOT return inside the range within the configured window (a real
   breakdown, not a spring), **When** evaluated, **Then** no `is_spring` flag is raised for it.
4. **Given** a spring candidate, **When** `WyckoffPrimitives.relative_volume` (slice 013) at the
   breakdown candle is available, **Then** it is attached to the event record as context (higher
   breakdown volume followed by a low-volume return is the classic "confirmed" spring per the
   research; this slice records the data point, it does NOT yet decide what counts as "confirmed" —
   that threshold-setting is slice 015's job, informed by validation, not asserted here as truth).

### Edge Cases

- Overlapping spring and upthrust conditions on the same candle (should not happen given the
  mutually-exclusive break-direction definitions, but MUST NOT raise if it somehow does — both flags
  can independently be `True`/`False`, the function does not assume exclusivity).
- A range so wide/noisy that `support`/`resistance` are far from any candle's close for the entire
  lookback (a trending market, not a range) — the detector still returns *a* range (rolling min/max
  is always defined), and simply produces zero spring/upthrust events; this slice does not attempt to
  distinguish "trending" from "ranging" markets (a `range_width_pct`/ATR-relative "is this actually a
  range" judgment is a candidate refinement, not required for this slice's acceptance criteria).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a pure function detecting the current trading range
  (`support`, `resistance`) as the rolling min/max of closes (or lows/highs) over a configurable
  lookback window (default aligned with slice 013's conventions).
- **FR-002**: The system MUST provide a pure function detecting Spring events: a low breaking below
  `support` by a configurable margin, followed by a close back above `support` within a configurable
  number of candles.
- **FR-003**: The system MUST provide the mirror function for Upthrust events (breaking above
  `resistance`, closing back below within the window).
- **FR-004**: Both detectors MUST use only data available up to and including the candle being
  evaluated — no lookahead beyond the explicit "did it return within K candles" check, which by
  definition only confirms an event K candles after it started (the event is timestamped at the
  breakdown/breakout candle, not the confirmation candle, but is only knowable as "confirmed" once
  the confirmation candle exists — this MUST be documented plainly in the returned data, not hidden).
- **FR-005**: Detected events MUST carry `WyckoffPrimitives.relative_volume` (slice 013) at both the
  break candle and the confirmation candle as contextual data, without this slice imposing any
  volume-based accept/reject threshold (that calibration belongs to slice 015).
- **FR-006**: This feature MUST NOT wire into `config.yml` or generate alerts (same discipline as
  slice 013's FR-005) and MUST have full test coverage (normal detection, both directions, the
  no-return-within-window negative case, insufficient-history edge case).

### Key Entities

- **`TradingRange`**: `(support, resistance, range_width_pct)` for a given lookback window ending at
  a given candle.
- **`SpringEvent` / `UpthrustEvent`**: `(break_index, confirm_index, break_low_or_high,
  break_relative_volume, confirm_relative_volume)`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All new tests pass; the full suite through slice 013 continues to pass unchanged.
- **SC-002**: Both detectors correctly identify engineered spring/upthrust fixtures and correctly
  produce zero false positives on an engineered pure-trend (no range) fixture.
- **SC-003**: No code path raises on short/degenerate input.

## Assumptions

- "Confirmed within K candles" is a parameter to calibrate, not a fixed law — the research notes
  Wyckoff practice doesn't specify an exact bar count; this slice exposes it as a configurable
  argument (default a small number, e.g. 3, revisited by slice 015's validation, not treated as
  gospel here).
- Full phase labeling (A-E) remains explicitly out of scope, per `specs/012-.../research.md`'s
  honesty section — this slice only builds the two named, rules-expressible event types.
