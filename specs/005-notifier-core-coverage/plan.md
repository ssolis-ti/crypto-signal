# Implementation Plan: Test Coverage for notifications/core.py::Notifier

**Branch**: `main` | **Date**: 2026-09-28 | **Spec**: `specs/005-notifier-core-coverage/spec.md`

## Summary

Add unit tests for `Notifier` (`app/notifications/core.py`), the one module slice 004 explicitly
deferred. Real `TelegramNotifier`/`WebhookNotifier`/`StdoutNotifier` instances are constructed (their
`__init__` does no I/O), and only their outbound-call methods are monkeypatched with recording stubs
— no mocking framework needed. Fixes one real, trivial, test-blocking bug found while designing the
tests: `notify_webhook` was silently dropping its `chart_file` argument, causing every webhook send to
raise `TypeError`.

## Technical Context

**Language/Version**: Python 3.11 (Dockerfile base image, unchanged)
**Primary Dependencies**: `pytest==8.3.4` (already pinned), `jinja2` (already required by `core.py`)
**Testing**: `pytest`, executed inside `crypto-signal:dev` Docker image, same as prior slices
**Target Platform**: Linux container (Docker), same as production
**Project Type**: single backend service
**Constraints**: zero real network/Telegram/webhook I/O (FR-005)
**Scale/Scope**: 1 test file (`tests/notifications/test_core.py`), ~15-18 test cases; 1-line
production fix in `app/notifications/core.py::notify_webhook`

## Constitution Check

| Principle | Check | Result |
|---|---|---|
| I. Read-Only, No Custody | No exchange/order code touched; tests never hit a real Telegram/webhook endpoint | PASS |
| II. No Repaint | Not touched | PASS (N/A) |
| III. Validate Heuristic Before Trust | Not applicable — no new scoring/heuristic | PASS (N/A) |
| IV. Secrets Never in VCS/Image | Tests use dummy strings (`'fake-token'`, `'http://example.invalid'`) | PASS |
| V. UTC Internally | No new datetime usage introduced by this slice | PASS |
| VI. Tests Guard the Core Pipeline | Closes the last major gap in `notifications/` coverage | PASS |
| VII. Pinned Deps, No Permanent Debug Logging | No new dependencies; no debug logging added | PASS |

No violations. The one production change (`notify_webhook` fix) is a correctness fix directly within
this slice's own tested surface, not scope creep into an unrelated file.

## Project Structure

### Documentation (this feature)

```
specs/005-notifier-core-coverage/
├── spec.md
├── checklists/requirements.md
├── plan.md          (this file)
├── research.md
├── data-model.md
├── quickstart.md
└── tasks.md
```

### Source Code

```
app/notifications/core.py          (1-line fix: notify_webhook forwards chart_file)
tests/notifications/test_core.py   (new)
```

**Structure Decision**: Single new test file mirroring the existing `tests/notifications/` layout.

## Complexity Tracking

*No entries — no constitution violations.*
