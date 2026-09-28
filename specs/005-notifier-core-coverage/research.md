# Phase 0 Research: Test Coverage for notifications/core.py::Notifier

## Decision: Construct real notifier client objects, monkeypatch only their I/O methods

**Rationale**: `TelegramNotifier.__init__`/`WebhookNotifier.__init__`/`StdoutNotifier.__init__` only
assign attributes (confirmed by reading `app/notifiers/telegram_client.py`,
`app/notifiers/webhook_client.py`, `app/notifiers/stdout_client.py`) — no `Bot(token=...)` connection,
no HTTP call, happens at construction. Replacing `send_messages`/`send_chart_messages`/`notify` on the
instance (`client.send_messages = recorder`) is simpler and more faithful than reconstructing a fake
class that duplicates `Notifier`'s expectations of the client interface.

**Alternatives considered**: `unittest.mock.patch` on the `Bot` class inside `telegram_client.py` —
rejected as unnecessarily deep; the seam `Notifier` actually depends on is the client's public
`send_messages`/`send_chart_messages`/`notify` methods, not the Telegram SDK's `Bot`.

## Decision: `notify_all` tests stub `self.builder.build_indicator_messages` directly

**Rationale**: Constructing a real, schema-correct `new_analysis` structure (the nested
`exchange → market → indicator_type → indicator → [{config, result: DataFrame}]` shape consumed by
`MessageBuilder.build_indicator_messages`) is `MessageBuilder`'s own concern, deferred (FR-007) same
as slice 004 deferred indicator/informant TA modules. Monkeypatching
`notifier_instance.builder.build_indicator_messages = lambda *a, **kw: fixed_messages_by_pair`
isolates `notify_all`'s routing/gating logic (the actual subject of Story 4) from `MessageBuilder`'s
internals.

**Alternatives considered**: Building a full realistic `new_analysis` fixture — rejected as
substantial extra work belonging to a hypothetical future `MessageBuilder.build_indicator_messages`
coverage slice, not this one.

## Decision: Root-cause and fix the `notify_webhook` bug in this slice, not defer it

**Rationale**: The bug (`chart_file` dropped before calling `WebhookNotifier.notify(messages,
chart_file)`, which requires `chart_file`) lives inside the exact method (`notify_webhook`) this slice
exists to cover, and is unconditional — 100% of webhook-configured deployments hit it on the very
first message. Writing a correct, passing test for "webhook delivers the message" is impossible
without either fixing this or asserting the crash as "expected" — the former is the honest fix, is a
one-line change, and was directly encountered while doing this slice's own test design (distinct from
slice 002's deferred bug, which lived in an unrelated call path not touched by that slice's fix).

**Alternatives considered**: Recording it as a Convergence finding for a future slice, per slice 004's
default coverage-only posture — rejected here specifically because FR-002/SC-002 make the fix itself
the acceptance criterion for Story 2; deferring would mean shipping a slice that documents but does
not close a channel-breaking bug it discovered in its own primary subject.
