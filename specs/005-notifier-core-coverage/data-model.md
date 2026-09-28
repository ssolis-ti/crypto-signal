# Phase 1 Data Model: Test Coverage for notifications/core.py::Notifier

No new entities or persistent storage. One existing method's contract is corrected:

## `Notifier.notify_webhook(messages: list, chart_file: Optional[str]) -> None`

- **Before**: `chart_file` accepted but never forwarded; `self.webhook_clients[notifier].notify(message)`
  called with one argument against `WebhookNotifier.notify(self, messages, chart_file)`, which has no
  default for `chart_file` → unconditional `TypeError`.
- **After**: `self.webhook_clients[notifier].notify(message, chart_file)` — the webhook client
  receives the value the caller passed in, exactly as `notify_telegram`/`_send_smart_chart` already do
  for their own chart_file parameters.
- **Signature**: unchanged.

## Other methods under test (characterized only, no contract change)

- `Notifier._initialize_notifiers`: populates `telegram_clients`/`webhook_clients`/`stdout_clients`
  dicts and `telegram_configured`/`webhook_configured`/`stdout_configured` boolean attributes (the
  latter three only exist as attributes when at least one matching, validly-configured entry exists —
  characterized via `hasattr`, not changed).
- `Notifier.notify_telegram` / `_send_telegram_queued` / `_send_smart_text` / `_send_smart_chart`:
  existing template-render-then-send contracts, characterized as-is.
- `Notifier.notify_all`: existing per-channel dispatch contract, characterized as-is (stubbing
  `self.builder` and the client dicts).
