# Feature Specification: Live Wyckoff Spring/Upthrust Telegram Alerts

**Feature Branch**: `main` (Spec Kit feature directory: `specs/023-wyckoff-live-alerts`)

**Created**: 2026-09-29

**Status**: Draft

**Input**: Operator decision (2026-09-29), following `specs/017-wyckoff-edge-refinement/` (validated
edge: Spring/Upthrust with break-candle volume ≥2.5x average, holdout-tested) and
`specs/018-wyckoff-timing-and-drawdown/` (timing/risk profile): ship a real Telegram alert for this
signal, sending **both** framings clearly labeled in one message — "Rápida" (act within 1-2h,
72-78% historical win rate, <1% typical move, implicitly for leveraged use) and "Sostenida" (hold
toward 14 days, 64% win rate, +2.84% median move, explicit warning that ~26% of historical events saw
a ≥10% adverse excursion first) — so the operator decides per-alert which horizon to act on, with
honest numbers, not a single flattering statistic.

## Why this is the first non-research slice in the Wyckoff arc

Slices 012-022 were exclusively research/validation (no `config.yml` wiring, no alert generation,
explicitly per each slice's own FR). This is the first slice whose entire purpose is a real,
live-wired behavior change — Constitution Principle III's gate ("validate, then build, as two
separate, explicit steps") has now been satisfied by slice 017's holdout-tested result, and the
operator has now made the explicit sign-off decision that discipline was waiting for.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A confirmed Spring/Upthrust with extreme break volume sends one honest, dual-framed Telegram alert (Priority: P1)

**Why this priority**: This is the entire feature — everything else is guarding against it firing
wrong, twice, or silently.

**Independent Test**: Given real 4h OHLCV for a configured pair where the last candle confirms a
Spring or Upthrust (per `WyckoffPrimitives.detect_springs`/`detect_upthrusts`, slice 014) with
`break_relative_volume >= 2.5` (slice 017's exact validated threshold), a Telegram message is sent
containing both the "Rápida" and "Sostenida" sections with the validated historical numbers, sent via
a path independent of `SignalEnhancer`/`SmartNotificationManager` (Constitution discipline: this
heuristic validated on its own terms, not blended into the already-invalidated 0-100 score).

**Acceptance Scenarios**:

1. **Given** the last closed 4h candle for a pair confirms a Spring with `break_relative_volume >=
   2.5`, **When** the cycle runs, **Then** exactly one Telegram message is sent containing both
   framing sections and the pair/direction/volume-multiple.
2. **Given** the mirror Upthrust condition, **When** the cycle runs, **Then** the same happens with
   cold/sell framing.
3. **Given** the same confirmed event is still the last candle on a subsequent cycle (no new candle
   closed yet), **When** the cycle re-runs, **Then** NO duplicate alert is sent (dedup keyed on
   exchange+pair+direction+candle timestamp).
4. **Given** a pair/period with insufficient history for the lookback window, **When** checked,
   **Then** no alert fires and no exception propagates.
5. **Given** the feature is disabled in `config.yml` (`settings.wyckoff_alerts.enabled: false`,
   the default), **When** any cycle runs, **Then** no Wyckoff alert is ever sent, regardless of what
   the data shows.

### Edge Cases

- Only the `4h` candle period is checked (the only period slice 017's validation actually covers) —
  a pair whose configured indicators use a different period is simply not checked by this feature,
  not an error.
- If no Telegram client is configured, the alert attempt logs and is silently skipped (mirrors
  `Notifier`'s existing behavior when `telegram_clients` is empty — no crash).
- Dedup state is in-memory only (resets on container restart) — accepted: a restart could in theory
  re-fire an alert for an event whose confirming candle is still the most recent one, which is a
  rare, low-cost edge case (one possible duplicate message after a restart) not worth persisting
  state for.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST detect, once per cycle per configured pair, whether the most recently
  closed `4h` candle confirms a Spring or Upthrust via the real, unmodified
  `WyckoffPrimitives.detect_springs`/`detect_upthrusts` (slice 014), with `break_relative_volume >=
  2.5` (slice 017's exact validated threshold — not a different, untested number).
- **FR-002**: On a confirmed event, the system MUST send exactly one Telegram message containing
  BOTH the "Rápida" framing (1-2h horizon, ~72-78% historical win rate, <1% typical move) and the
  "Sostenida" framing (14d horizon, ~64% win rate, +2.84% median move, explicit ≥10%-drawdown-risk
  disclosure) — the exact numbers from `specs/017` and `specs/018`'s validation reports, not
  rounded-up or softened marketing copy.
- **FR-003**: This alert path MUST be independent of `SignalEnhancer`/`SmartNotificationManager`
  scoring/gating — it is sent directly via the Telegram client(s), never subject to the already-
  invalidated 0-100 score or `detail_min_quality` gate.
- **FR-004**: The same confirmed event (same exchange, pair, direction, and candle timestamp) MUST
  NOT be alerted more than once.
- **FR-005**: This feature MUST be controlled by a `config.yml` toggle
  (`settings.wyckoff_alerts.enabled`), defaulting to `false` in `app/defaults.yml` (so existing
  deployments and fresh clones of this open-source project do not suddenly start receiving a new
  alert type without explicit opt-in) — the operator's own `config.yml` sets it to `true`.
- **FR-006**: Any error in detection (insufficient data, malformed OHLCV, exchange hiccup) MUST
  degrade to "no alert this cycle," logged, never crashing the analysis cycle it runs alongside.
- **FR-007**: This feature MUST have test coverage (Constitution Principle VI: `analysis/` requires
  tests) covering: normal Spring detection/alert, normal Upthrust detection/alert, dedup on repeated
  cycles, disabled-config no-op, insufficient-history no-op, and an injected exception not
  propagating.

### Key Entities

- **`WyckoffAlerter`** (new, `app/analysis/wyckoff_alerts.py`): holds in-memory dedup state, checks
  one pair/period per call, sends the dual-framed message via the existing `Notifier`'s Telegram
  client(s) directly (new small `Notifier.send_direct_text` method, bypassing the scored path).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All new tests pass; the full existing suite (144 tests through slice 013/014) continues
  to pass unchanged.
- **SC-002**: A live cycle against real Binance data, run with the feature enabled, either sends a
  correctly-formatted dual-framed message when a qualifying event exists, or sends nothing when none
  does — verified by inspecting live container logs/Telegram.
- **SC-003**: `grep` of the message-building code shows the exact validated numbers from slices
  017/018 (72-78%, 64%, +2.84%, ≥10%) — not placeholder or rounded-differently values.

## Assumptions

- "Once per confirmed candle" is the correct alerting cadence (matches the live bot's existing
  `alert_frequency: once` pattern for RSI/MACD) — not once per cycle regardless of whether the
  candle changed.
- The dual-framing message format (one message, two clearly labeled sections) was the operator's
  explicit choice over "fast-only," "sustained-only," or "hold for further study."
