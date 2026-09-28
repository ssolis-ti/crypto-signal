# Feature Specification: Test Coverage for Untested Pure-Logic Core Modules

**Feature Branch**: `main` (Spec Kit feature directory: `specs/004-core-pipeline-test-coverage`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Continue with tests for analysis/, data/, and notifications/, proceed
autonomously." Slices 001-003 fixed and tested the OHLCV/timestamp pipeline
(`data/manager.py`, `analyzers/utils.py`, `notifications/builder.py`, `exchanges/driver.py`). Several
other modules in these same three packages carry real decision logic (crossover detection, pair
selection, notification prioritization/deduplication, and message-formatting logic) and have zero
test coverage today. This feature closes that gap for the modules whose logic is pure/injectable
(no live exchange or Telegram network calls required to exercise it), per Constitution Principle VI.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Crossover detection is verified for both directions and edge alignment (Priority: P1)

`analyzers/crossover.py::CrossOver.analyze` is used by every crossover-based indicator
(MA crossover, MACD cross, StochRSI cross) to detect when one indicator line crosses another. It has
no test today, so a regression in its column-indexing or hot/cold comparison logic would silently
change every crossover signal in the bot.

**Why this priority**: Directly gates trading-relevant hot/cold signals; highest blast radius of the
untested modules in this slice.

**Independent Test**: Build two small synthetic single-column DataFrames with known crossing values
and confirm `analyze` reports `is_hot`/`is_cold` on exactly the expected rows, with NaN rows dropped.

**Acceptance Scenarios**:

1. **Given** a key indicator series that starts below and ends above a crossed indicator series,
   **When** `analyze` runs, **Then** rows after the cross have `is_hot=True`, `is_cold=False`.
2. **Given** the reverse (key starts above, ends below), **When** `analyze` runs, **Then** rows after
   the cross have `is_cold=True`, `is_hot=False`.
3. **Given** input series of different lengths (misaligned indices producing NaN on concat),
   **When** `analyze` runs, **Then** those misaligned rows are dropped from the result (no NaN
   comparisons silently evaluating to `False`/`False`).
4. **Given** multiple configuration indices for the same signal name (e.g. two RSI configs),
   **When** `analyze` runs, **Then** output columns are suffixed by each side's index so they don't
   collide.

### User Story 2 - Pair resolution picks the correct mode and respects exclusions (Priority: P1)

`data/pair_resolver.py::PairResolver.resolve` decides which market pairs the bot analyzes each
cycle. Wrong mode selection or a broken exclusion filter means the bot silently analyzes the wrong
markets (or none).

**Why this priority**: A silent wrong-pairs bug is hard to notice operationally (the bot keeps
running, just on the wrong assets) — exactly the class of bug tests should catch immediately.

**Independent Test**: Exercise `resolve` with each config combination (manual list present; dynamic
enabled with a fake `data_manager.get_top_pairs`; neither set) and confirm the mode chosen and the
exact pair list returned, including exclusion filtering and the `top_n` truncation.

**Acceptance Scenarios**:

1. **Given** `market_pairs` is a non-empty list in settings, **When** `resolve` runs, **Then** it
   returns exactly that list without consulting `data_manager` (manual mode takes precedence).
2. **Given** `market_pairs` is empty/None and `dynamic_pairs.enabled=True` with `source='volume'`,
   **When** `resolve` runs, **Then** it calls `data_manager.get_top_pairs` and returns up to `top_n`
   pairs with `exclude` entries removed.
3. **Given** dynamic mode is enabled but `data_manager` is `None`, **When** `resolve` runs, **Then**
   it returns `[]` without raising.
4. **Given** neither manual pairs nor dynamic mode is configured, **When** `resolve` runs, **Then**
   it returns `[]`.
5. **Given** dynamic mode with an unsupported `source` (e.g. `'coingecko'`), **When** `resolve` runs,
   **Then** it returns `[]` without calling `data_manager`.

### User Story 3 - Notification queue prioritizes, dedupes, and filters by quality (Priority: P1)

`notifications/queue.py::NotificationQueue` decides send order, marks duplicate signals as
"update", and filters below a configured minimum quality. This is pure in-memory logic (the actual
Telegram call is an injected `send_func`), so it is fully testable without network access.

**Why this priority**: Ordering/deduplication bugs directly affect what an operator sees and in what
order during a burst of signals — a correctness-critical, previously unverified path.

**Independent Test**: Add several notifications of mixed quality/priority/symbol to a queue and
verify: filtering, sort order, duplicate-window detection, and `process_all`'s call sequence via a
recording `send_func` stub (no real sleep/network).

**Acceptance Scenarios**:

1. **Given** `min_quality='B'`, **When** a `quality='C'` message is added, **Then** `add` returns
   `False` and the item is not queued.
2. **Given** three queued notifications with priorities 10, 90, 50, **When** `sort_by_priority` runs,
   **Then** `get_next` returns them in the order 90, 50, 10.
3. **Given** the same `symbol`/`indicator`/`status` combination is added twice within the duplicate
   window, **When** the second `add` runs, **Then** the resulting notification has `is_update=True`.
4. **Given** a populated queue, **When** `process_all` runs with a stub `send_func`, **Then** it is
   called once per queued item in priority order, the queue ends empty, and the returned count
   matches the number sent.
5. **Given** `send_func` raises for one item, **When** `process_all` runs, **Then** it logs and
   continues processing the remaining items rather than aborting the whole batch.

### User Story 4 - Smart notification summary formatting reflects quality/market-context rules (Priority: P2)

`notifications/smart.py::SmartNotificationManager` builds the consolidated summary message and
decides which signals get a full detail/chart send. Its quality-gating and market-scan-mode branches
have no test today.

**Why this priority**: Lower blast radius than P1 items (formatting/UX, not a wrong-market or
wrong-direction signal), but still core to what an operator actually reads in the current
architecture (`SmartNotificationManager` has, per Graphify, replaced `NotificationQueue` in the live
flow: `notifications/core.py` invokes `SmartNotificationManager`, not `NotificationQueue`, at
runtime).

**Independent Test**: Feed `add_signal` a mix of qualities and BTC market context, then check
`build_summary_message`'s header/branching and `finalize_cycle`'s call counts to stub
send/send-chart functions (no real `time.sleep` delay — patched or measured only for call counts).

**Acceptance Scenarios**:

1. **Given** all added signals are quality `C` and BTC context trend is `bearish`, **When**
   `build_summary_message` runs, **Then** the header is the "MARKET SCAN / sin señales operables"
   branch.
2. **Given** at least one `A`/`A+` signal, **When** `build_summary_message` runs, **Then** the header
   is the "SEÑALES OPERABLES" branch and low-quality signals are reported as "en watchlist".
3. **Given** more `C`-quality signals than `max_c_signals`, **When** `build_summary_message` runs,
   **Then** only `max_c_signals` are listed and the remainder are reported as truncated.
4. **Given** a mix of qualities, **When** `finalize_cycle` runs with stub `send_func`/
   `send_chart_func`, **Then** only signals at/above `detail_min_quality` receive a detail send, and
   only signals at/above `chart_min_quality` (with a chart file present) receive the chart-send path.
5. **Given** `finalize_cycle` completes, **When** `get_cycle_stats`/a further `add_signal` is called,
   **Then** the cycle state (`summaries`, `current_cycle`, `btc_context`) has been reset by
   `clear_cycle`.

### User Story 5 - Notifier config validation correctly reports missing required fields (Priority: P3)

`notifications/validator.py::ConfigValidator.validate_required_config` gates whether a notifier
client is constructed at all (`notifications/core.py`). Small, but a silent `True` on incomplete
config would attempt to construct a client with an empty token/URL.

**Why this priority**: Small, isolated, low-complexity — included for completeness at lowest
priority/effort.

**Independent Test**: Call it with a `required` block that is fully populated, partially empty, and
absent entirely.

**Acceptance Scenarios**:

1. **Given** all `required` values are truthy, **When** validated, **Then** it returns `True`.
2. **Given** any one `required` value is empty/falsy, **When** validated, **Then** it returns `False`.
3. **Given** the notifier config has no `'required'` key at all, **When** validated, **Then** it
   returns `True` (matches current behavior: nothing to check means nothing fails) — documented as
   existing behavior, not changed by this feature.

### Edge Cases

- `CrossOver.analyze` with completely non-overlapping indices (no rows survive `dropna`): must return
  an empty DataFrame without raising.
- `PairResolver.resolve` with `market_pairs` present but an empty list `[]` (falsy): must fall through
  to dynamic/fallback logic exactly like `None`, per the existing `if self.market_pairs:` truthiness
  check (documented as existing behavior).
- `NotificationQueue.add` with a `quality` value not in `quality_order` (unknown string): treated as
  priority `0`, filtered out unless `min_quality` is also unrecognized.
- `SmartNotificationManager.build_summary_message` with zero signals added: returns `""` without
  raising.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `CrossOver.analyze` MUST have test coverage proving both hot and cold cross detection,
  NaN-row dropping, and per-index column-suffix disambiguation.
- **FR-002**: `PairResolver.resolve` MUST have test coverage proving manual-mode precedence,
  dynamic-mode volume resolution with exclusion/top_n handling, the `data_manager=None` guard, the
  unconfigured fallback, and the unsupported-`source` fallback.
- **FR-003**: `NotificationQueue` MUST have test coverage proving quality filtering, priority
  ordering, duplicate-window detection/`is_update` marking, and `process_all`'s send-loop behavior
  including per-item exception isolation.
- **FR-004**: `SmartNotificationManager` MUST have test coverage proving the market-scan-mode header
  branch, the actionable-signals header branch, the `max_c_signals` truncation, and
  `finalize_cycle`'s detail/chart gating and cycle-state reset.
- **FR-005**: `ConfigValidator.validate_required_config` MUST have test coverage proving the
  all-present, one-missing, and no-`required`-key cases.
- **FR-006**: This feature MUST NOT change the behavior of any module under test — it is
  coverage-only, following the same "characterize then guard" approach as prior slices' regression
  tests, except where a test directly exercises a documented existing-behavior edge case (no code
  change implied).
- **FR-007**: Tests MUST NOT require live network access, a real Telegram bot, or a real exchange
  connection — all external effects (`send_func`, `send_chart_func`, `data_manager`) MUST be
  lightweight stubs/fakes defined in the test module.
- **FR-008**: `notifications/core.py::Notifier` (which constructs real `TelegramNotifier`/
  `WebhookNotifier` clients in its constructor) and the `analyzers/indicators/*` /
  `analyzers/informants/*` TA-calculation modules are explicitly OUT of scope for this feature — they
  require either network-client mocking or per-indicator TA-Lib output fixtures, each substantial
  enough to warrant its own future slice rather than being folded into this one.

### Key Entities

- **Crossover result DataFrame**: per-row `is_hot`/`is_cold` booleans keyed by two suffixed
  indicator-value columns.
- **Resolved pair list**: the `List[str]` of market symbols a given exchange will be analyzed with
  for one cycle.
- **Queued notification** / **duplicate signature**: existing `QueuedNotification` dataclass and its
  MD5-based dedup signature.
- **Signal summary**: existing `SignalSummary` dataclass consumed by `build_summary_message`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All new tests pass, and the full existing suite (31 tests from slices 001-003) continues
  to pass unchanged — total test count strictly increases, zero regressions.
- **SC-002**: Every functional requirement (FR-001 through FR-005) is covered by at least one
  assertion that would fail if the corresponding logic branch were reverted or broken.
- **SC-003**: Zero tests depend on wall-clock sleep duration, real network I/O, or a real Telegram/
  exchange credential.

## Assumptions

- No source file in `analyzers/crossover.py`, `data/pair_resolver.py`, `notifications/queue.py`,
  `notifications/smart.py`, or `notifications/validator.py` needs a behavior change to pass these
  tests — this is a pure coverage slice, consistent with the user's instruction to "continue with
  tests" (not "continue fixing bugs"). If a test reveals an actual bug, it will be recorded as a
  Convergence finding for a future slice rather than fixed inline, per the constitution's
  bounded-slice discipline — unless it is trivial and directly blocks writing a correct test.
