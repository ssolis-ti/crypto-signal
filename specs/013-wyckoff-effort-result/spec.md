# Feature Specification: Wyckoff Effort-vs-Result Primitives

**Feature Branch**: `main` (Spec Kit feature directory: `specs/013-wyckoff-effort-result`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "En base de esta investigación desarrolla e implementa las specs
formales para su buen desarrollo" — first buildable slice of the roadmap in
`specs/012-wyckoff-fractal-research/research.md`. That research identified Wyckoff's Law of
Effort vs. Result (volume vs. price-range proportionality) as the method's most objectively
computable primitive from raw OHLCV — the natural starting point before attempting anything as
subjective as phase labeling or spring/upthrust detection (those come in slice 014).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute an objective effort/result ratio per candle (Priority: P1)

**Why this priority**: Every later Wyckoff-derived feature (climax detection, spring/upthrust
confirmation, phase bias) needs this ratio as an input. It is also, on its own, immediately useful
as an additional informational signal (surfaced via the Agent API, not yet gating any alert).

**Independent Test**: Given a historical OHLCV series, compute per-candle `relative_volume`
(volume vs. its rolling average) and `relative_range` (true range vs. ATR), then
`effort_result_ratio = relative_volume / relative_range`, and confirm it matches hand-computed
values on a small fixture.

**Acceptance Scenarios**:

1. **Given** a candle with volume at 2x its rolling average and a price range at 1x its rolling ATR,
   **When** the ratio is computed, **Then** it equals 2.0 (high effort, normal result).
2. **Given** a candle with volume at 1x average and range at 2x ATR, **When** computed, **Then** the
   ratio equals 0.5 (normal effort, high result — a "thin"/low-conviction move).
3. **Given** insufficient history for the rolling window (warm-up period), **When** computed,
   **Then** the value is `NaN` for those candles — never a fabricated number, never a crash.
4. **Given** a candle with `ATR == 0` (degenerate/flat data), **When** computed, **Then** the ratio
   is `NaN` for that candle (division-by-zero guarded), not `inf` or an exception.

### User Story 2 - Flag climax and "no-result" candles using configurable thresholds (Priority: P2)

**Why this priority**: A raw ratio is hard to eyeball; the two named Wyckoff patterns this primitive
is meant to surface (effort-without-result "climax"/absorption, and result-without-effort "thin"
moves) need explicit boolean flags so later slices (and a human reviewing the Agent API) can query
them directly.

**Independent Test**: With configurable `relative_volume` / `relative_range` thresholds, confirm a
candle is flagged `is_climax` exactly when relative_volume is high AND relative_range is low, and
`is_thin_move` exactly when the reverse holds.

**Acceptance Scenarios**:

1. **Given** `relative_volume >= climax_volume_threshold` and `relative_range <= climax_range_threshold`,
   **When** flagged, **Then** `is_climax` is `True`.
2. **Given** `relative_range >= thin_range_threshold` and `relative_volume <= thin_volume_threshold`,
   **When** flagged, **Then** `is_thin_move` is `True`.
3. **Given** neither condition holds, **When** flagged, **Then** both flags are `False`.
4. **Given** NaN inputs (warm-up period), **When** flagged, **Then** both flags are `False` (not NaN,
   not an exception) — a flag is a boolean question ("is this a climax candle?"), and "we don't have
   enough data yet" answers `False`, not "unknown".

### Edge Cases

- All-zero-volume input (e.g. an illiquid pair with gaps): `relative_volume` is `NaN` via the
  rolling-average guard, propagating safely to `NaN` flags-as-False, not a crash.
- A single-candle or very short input (shorter than the rolling window): the whole series is `NaN`,
  same as the constitution's existing precedent for other indicators' warm-up behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a pure function computing `relative_volume` (current volume /
  rolling SMA of volume over a configurable period, default 20) from an OHLCV series.
- **FR-002**: The system MUST provide a pure function computing `relative_range` (current true range
  / rolling ATR over a configurable period, default 14 — reusing `talib.ATR`, the same library every
  other indicator in this codebase already uses) from an OHLCV series.
- **FR-003**: The system MUST provide `effort_result_ratio = relative_volume / relative_range`,
  guarded against division by zero and NaN propagation (FR results in `NaN`, never `inf`/exception).
- **FR-004**: The system MUST provide `is_climax` and `is_thin_move` boolean flags derived from
  `effort_result_ratio`'s two components, with independently configurable thresholds (not hardcoded
  magic numbers — mirrors how `indicators.rsi.hot`/`cold` are configurable in `config.yml`).
- **FR-005**: This feature MUST NOT wire itself into `config.yml`'s `indicators`/`informants` sections
  or generate any hot/cold alert — it is a pure computational primitive for later slices (014, 015)
  and for informational exposure via the Agent API, consistent with the roadmap's validate-before-
  trust discipline (Constitution Principle III).
- **FR-006**: This feature MUST have test coverage proving the acceptance scenarios above (normal
  computation, both edge directions, NaN/zero-guard behavior) — required regardless of package,
  and doubly so since this is new, unvalidated analytical surface per the constitution's Principle
  VI spirit.

### Key Entities

- **`WyckoffPrimitives`** (new, `app/analyzers/indicators/wyckoff.py`): static-method class mirroring
  `DerivedIndicators`' existing pattern (`app/analyzers/indicators/derived.py`) — pure functions, no
  state, no config.yml wiring, consumed by future slices and (read-only) by the Agent API.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All new tests pass; the full existing suite (121 tests through slice 011) continues to
  pass unchanged.
- **SC-002**: `effort_result_ratio`, `is_climax`, and `is_thin_move` are computable from a plain
  OHLCV list with no dependency beyond `pandas`/`talib`/`numpy` (already-pinned project dependencies
  — no new dependency added).
- **SC-003**: No code path in this feature can raise on malformed/degenerate input (all-zero volume,
  flat price, short series) — every such case is covered by a test.

## Assumptions

- Default rolling windows (20 for volume, 14 for ATR) mirror common technical-analysis convention
  (same ATR period the project's own `talib` usage elsewhere implicitly assumes) — these are
  starting defaults, not yet calibrated by historical validation (that calibration, if needed, is
  slice 015's job, not this one's).
- This slice produces informational primitives only; no `SignalEnhancer` scoring weight, no
  `notify_all` gate, and no `config.yml` schema change happens here (see FR-005).
