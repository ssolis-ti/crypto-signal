# Phase 0 Research: Test Coverage for Untested Pure-Logic Core Modules

## Decision: Test at the public-method boundary, with minimal stubs instead of a mocking library

**Rationale**: All five target classes accept their external effects as constructor args or function
parameters (`data_manager`, `send_func`, `send_chart_func`) rather than importing network clients
directly at the point of use. Plain Python stub objects/closures are sufficient; `unittest.mock` is
not needed, consistent with the lightweight style of the existing `tests/notifications/test_builder.py`.

**Alternatives considered**: `unittest.mock.MagicMock` for `data_manager`/`send_func` — rejected as
unnecessary indirection; a hand-written fake makes the test's exercised behavior (call count, call
args) more explicit and readable than mock-assertion syntax.

## Decision: Construct `CrossOver` DataFrames directly rather than running real TA-Lib indicators

**Rationale**: `CrossOver.analyze` only needs two single-column DataFrames with a shared/overlapping
index; the values' origin (a real RSI vs. a synthetic series) is irrelevant to the column-renaming and
comparison logic being tested. Using `pandas.DataFrame({'rsi': [...]}, index=pandas.date_range(...))`
keeps the test fast and independent of TA-Lib's exact numerical output.

**Alternatives considered**: Running a real indicator (e.g. `analyzers/indicators/rsi.py`) to produce
input — rejected: couples this slice's tests to indicator internals, adds TA-Lib as a hard dependency
of a test whose actual subject is the crossover/merge logic, not RSI math.

## Decision: `NotificationQueue`/`SmartNotificationManager` time-based tests avoid real `time.sleep`

**Rationale**: `process_all` and `finalize_cycle` call `time.sleep(delay)` between sends. Real sleeps
would make the suite slow without adding assertion value. Tests pass `delay_msg=0`/`delay_photo=0` (an
existing, already-supported parameter) for `NotificationQueue`, and for `SmartNotificationManager`
(whose `finalize_cycle` delays come from `self.config['delay_after_summary']`/
`delay_between_details`, not a parameter) tests pass `config={'delay_after_summary': 0,
'delay_between_details': 0, ...}` at construction — both are already-exposed, documented knobs, not
new code.

**Alternatives considered**: Monkeypatching `time.sleep` — rejected as unnecessary; both classes
already expose zero-delay configuration without needing to touch their internals.

## Decision: Duplicate-window test for `NotificationQueue` uses the real `time.time()` clock, not a fake

**Rationale**: The 300-second `DUPLICATE_WINDOW` is far larger than a unit test's execution time, so
asserting "added twice within the window marks it a duplicate" needs no clock manipulation — two
`add()` calls a few milliseconds apart are trivially "within window" against real time. Testing the
window's *expiry* (signatures older than 300s are forgotten) is explicitly out of scope for this
slice (would require either a real 300s sleep or refactoring `_is_duplicate`'s clock source, which is
a production-code change this coverage-only slice avoids per spec Assumptions).

**Alternatives considered**: Injecting a fake clock into `NotificationQueue` — rejected as a
production code change outside this slice's coverage-only scope; noted as a candidate Convergence
finding if judged valuable later.
