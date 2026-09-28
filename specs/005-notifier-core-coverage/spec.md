# Feature Specification: Test Coverage for notifications/core.py::Notifier

**Feature Branch**: `main` (Spec Kit feature directory: `specs/005-notifier-core-coverage`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Avanza al slice 005, cobertura de notifications/core.py, se eficaz,
avanza de forma autonoma." `Notifier` is the orchestration class left explicitly out of scope by
slice 004 (FR-008) because its constructor builds real `TelegramNotifier`/`WebhookNotifier` network
clients. Investigation shows those clients are safe to construct directly in tests (their
`__init__` methods only store attributes — no network call happens until `.notify()`/`.send_messages()`
is invoked), so this slice constructs real `Notifier`/client objects and only stubs the actual
send methods, rather than needing a mocking framework.

While reading `Notifier` to design its tests, a real defect was found: `notify_webhook` accepts a
`chart_file` parameter but never forwards it to `WebhookNotifier.notify(messages, chart_file)`, which
has no default for `chart_file` — calling `self.webhook_clients[notifier].notify(message)` with one
argument raises `TypeError: notify() missing 1 required positional argument: 'chart_file'` every
single time, unconditionally, whenever a webhook notifier is configured. This is a total, permanent
breakage of the webhook channel, not a latent edge case — the fix is a trivial one-line change
directly in the method this slice is testing, so it is fixed here rather than deferred (see spec
004's Assumptions precedent: trivial fixes that directly block writing a correct test are made
inline).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Notifier initializes only the configured, validly-configured channels (Priority: P1)

`_initialize_notifiers` decides which of Telegram/Webhook/Stdout clients actually get constructed,
based on key-name prefix matching and `ConfigValidator`. A bug here means a channel silently never
fires (channel skipped) or crashes at startup.

**Why this priority**: Startup wiring — if this is wrong, an operator's entire configured channel is
silently dead with zero user-visible signal until they notice no alerts ever arrive.

**Independent Test**: Construct `Notifier` with various `notifier_config` combinations and assert
which of `telegram_clients`/`webhook_clients`/`stdout_clients`/the `*_configured` flags end up set.

**Acceptance Scenarios**:

1. **Given** a `notifier_config` with a fully-populated `telegram` entry, **When** `Notifier` is
   constructed, **Then** `telegram_clients` contains one client and `telegram_configured` is `True`.
2. **Given** a `telegram` entry missing a required field (e.g. empty `token`), **When** `Notifier` is
   constructed, **Then** no telegram client is created and `telegram_configured` is not set.
3. **Given** entries for `telegram`, `webhook`, and `stdout` all validly configured, **When**
   `Notifier` is constructed, **Then** all three `*_configured` flags are set and each client dict has
   exactly one entry.
4. **Given** an empty `notifier_config`, **When** `Notifier` is constructed, **Then** all three client
   dicts are empty and none of the `*_configured` flags exist.

### User Story 2 - Webhook channel actually delivers the chart file it receives (Priority: P1, bug fix)

**Why this priority**: Real, currently-total breakage of the webhook channel (see Input). Any
operator using webhook notifications gets zero working notifications today.

**Independent Test**: Call `notify_webhook(messages, chart_file)` with a stub webhook client
recording its call arguments; confirm the stub receives both `messages` and `chart_file` and no
exception propagates.

**Acceptance Scenarios**:

1. **Given** a configured webhook client, **When** `notify_webhook(msgs, None)` runs (the actual call
   shape used by `notify_all`), **Then** the client's `notify` is called once per message with
   `chart_file=None` and no exception is raised.
2. **Given** a configured webhook client and a non-`None` chart_file, **When** `notify_webhook` runs,
   **Then** the client receives that exact chart_file value (regression guard for the fix).

### User Story 3 - Telegram send paths render templates and handle chart-send failure gracefully (Priority: P1)

`notify_telegram`, `_send_telegram_queued`, `_send_smart_text`, and `_send_smart_chart` all render a
Jinja2 template per configured telegram client and call the client's `send_messages`/
`send_chart_messages`. Each has its own fallback-on-exception behavior that has never been exercised.

**Why this priority**: These are the methods actually wired into the live `SmartNotificationManager`
flow (`notify_all` passes `_send_smart_text`/`_send_smart_chart` as its `send_func`/`send_chart_func`)
— the most-used send path in production today.

**Independent Test**: Construct a `Notifier` with a real `TelegramNotifier` client object, but replace
its `send_messages`/`send_chart_messages` methods with recording stubs (no real `Bot`/network call),
then invoke each send method and assert on the stub's recorded calls and on error-path fallback.

**Acceptance Scenarios**:

1. **Given** a string message (a pre-formatted summary), **When** `_send_smart_text` runs, **Then**
   `send_messages` is called with that exact string, with no template rendering applied.
2. **Given** a dict message (needs template rendering), **When** `_send_smart_text` runs, **Then** the
   configured Jinja2 template is rendered and `send_messages` is called with the rendered string.
3. **Given** a chart_file and a dict message, **When** `_send_smart_chart` runs, **Then**
   `send_chart_messages` is called with the chart_file and the rendered message.
4. **Given** `send_chart_messages` raises, **When** `_send_smart_chart` runs, **Then** it falls back
   to `send_messages` with the rendered text (no exception propagates).
5. **Given** both `send_chart_messages` and the fallback `send_messages` raise, **When**
   `_send_smart_chart` runs, **Then** the exception is caught and logged, not propagated.
6. **Given** `is_update=True`, **When** `_send_telegram_queued` runs, **Then** the rendered message is
   prefixed with the UPDATE marker before being sent.
7. **Given** `notify_telegram` is called with a `chart_file` and the client's `send_chart_messages`
   raises, **When** it runs, **Then** it falls back to `send_messages` with the rendered messages
   (existing documented behavior, characterized not changed).

### User Story 4 - notify_all routes signals to exactly the configured channels (Priority: P2)

`notify_all` is the single entry point used by the rest of the application. It must call the smart
manager for Telegram, `notify_webhook` for webhook, and `notify_stdout` for stdout — and only for
channels that are actually configured.

**Why this priority**: Integration-level check that the wiring done by Stories 1-3 is actually
invoked correctly end-to-end; lower priority than the individual units because each piece is already
covered on its own.

**Independent Test**: Construct a `Notifier` with a stubbed `self.builder.build_indicator_messages`
(returning a small fixed `messages_by_pair` structure) and fake client dicts; call `notify_all` and
assert exactly the expected stub methods were invoked, using `SmartNotificationManager`'s
already-tested behavior (slice 004) as a black box.

**Acceptance Scenarios**:

1. **Given** only `stdout_configured`, **When** `notify_all` runs, **Then** `notify_stdout` fires for
   each non-empty message group and neither Telegram nor webhook paths are touched.
2. **Given** only `telegram_configured`, **When** `notify_all` runs, **Then** the smart-notification
   flow fires (`_send_smart_text`/`_send_smart_chart` stubs receive at least one call for a non-empty
   analysis) and webhook/stdout paths are not touched.
3. **Given** `enable_charts=False`, **When** `notify_all` runs, **Then** `create_charts` is never
   invoked (existing documented gating behavior).

### Edge Cases

- `notify_telegram`/`_send_telegram_queued`/`_send_smart_text`/`_send_smart_chart` with zero
  configured telegram clients: loop bodies simply don't execute; no exception.
- `_initialize_notifiers` with a notifier key that matches none of the three prefixes (e.g. a typo'd
  key): silently ignored, same as today (not a new requirement, just characterized).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `Notifier._initialize_notifiers` MUST have test coverage proving correct client
  construction and `*_configured` flag-setting for telegram/webhook/stdout, individually and
  combined, and for the all-missing case.
- **FR-002**: `notify_webhook` MUST forward its `chart_file` argument to the underlying webhook
  client's `notify(messages, chart_file)` call (bug fix), and MUST have a regression test proving
  this.
- **FR-003**: `notify_telegram`, `_send_telegram_queued`, `_send_smart_text`, and `_send_smart_chart`
  MUST have test coverage proving correct template rendering, correct client method selection
  (chart vs. text), the UPDATE-prefix behavior, and the documented exception-fallback behavior of
  each method.
- **FR-004**: `notify_all` MUST have test coverage proving it invokes only the configured channels'
  send paths, using stubbed collaborators (`builder`, client dicts) rather than re-deriving
  `MessageBuilder`'s or `SmartNotificationManager`'s already-tested internal logic.
- **FR-005**: Tests MUST NOT perform any real network call, Telegram Bot API call, or webhook HTTP
  request — `TelegramNotifier`/`WebhookNotifier` instances used in tests MUST have their
  network-calling methods (`send_messages`, `send_chart_messages`, `notify`) replaced with recording
  stubs before being exercised.
- **FR-006**: This feature MUST NOT change behavior of any method other than the one-line
  `notify_webhook` fix required by FR-002.
- **FR-007**: `notifications/builder.py::MessageBuilder.build_indicator_messages` and the
  `analyzers/indicators/*`/`analyzers/informants/*` TA-calculation modules remain OUT of scope
  (unchanged from slice 004's FR-008) — `notify_all` tests stub `self.builder` rather than exercising
  real indicator analysis data.

### Key Entities

- **`Notifier`**: the class under test; orchestrates client construction and message dispatch.
- **Client stub**: a lightweight object standing in for `TelegramNotifier`/`WebhookNotifier`/
  `StdoutNotifier`, recording calls without performing I/O.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All new tests pass, and the full existing suite (58 tests from slices 001-004) continues
  to pass unchanged — zero regressions, total test count strictly increases.
- **SC-002**: A test exists that fails against the pre-fix `notify_webhook` (i.e. would have caught
  the `TypeError` bug) and passes after the fix.
- **SC-003**: Zero tests perform real network I/O or require a live Telegram/webhook credential.

## Assumptions

- `TelegramNotifier`, `WebhookNotifier`, and `StdoutNotifier` are safe to instantiate directly in
  tests (verified by reading their `__init__` methods — none perform I/O), so tests construct real
  instances and monkeypatch only their outbound-call methods, rather than needing a full mock
  replacement of the class.
- The `notify_webhook` fix (forwarding `chart_file`) is in scope despite the "coverage-only, no
  production changes" default established in slice 004, because it is trivial, was discovered while
  designing this slice's own tests, and directly concerns the method this slice exists to cover —
  consistent with slice 004's own stated exception for trivial, test-blocking fixes.
