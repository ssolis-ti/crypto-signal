# Feature Specification: Clean Up Deferred Convergence Findings (Debug Logging + Presentation Timestamps)

**Feature Branch**: `main` (Spec Kit feature directory: `specs/006-deferred-cleanup-findings`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Avanza al slice 006, limpieza de los hallazgos menores pendientes."
Three LOW-severity findings were deferred by earlier slices' Convergence phases rather than fixed
inline, per the constitution's bounded-slice discipline:

- Slice 001 F3: leftover `DEBUG:`-prefixed `logger.info` calls and dead commented-out
  `logger.debug` lines in `app/data/manager.py::get_top_pairs` (Principle VII).
- Slice 002 F2: `app/rendering/utils.py:22`'s `convert_to_dataframe` uses naive
  `datetime.datetime.fromtimestamp()` for chart x-axis timestamps — host-timezone-dependent,
  same defect class already fixed elsewhere in slices 002/003 (Principle V).
- Slice 002 F3: `app/utils/calibration.py` (lines ~83, ~227) uses naive `datetime.fromtimestamp()`/
  `datetime.now()` in debug/calibration log output and anomaly records (Principle V, overlaps
  Principle VII since this whole module is diagnostic tooling).

This slice closes all three in one bounded pass since each is small, low-risk, and already fully
scoped by prior Convergence phases — no new investigation needed, only implementation and tests.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - get_top_pairs has no leftover debug-investigation logging (Priority: P2)

**Why this priority**: Cosmetic/hygiene — `DEBUG:`-prefixed `info`-level logs and dead commented
code don't affect correctness, but they violate Principle VII and add log noise at a level
(`info`) an operator can't filter out without losing real informational logs.

**Independent Test**: Call `get_top_pairs` against a fake driver and confirm it still returns the
correct filtered/sorted/truncated pair list (behavior unchanged), while the two `DEBUG:`-prefixed
`logger.info` calls are gone (demoted to `logger.debug` without the redundant prefix) and the two
dead commented-out lines are removed.

**Acceptance Scenarios**:

1. **Given** a fake driver returning a mixed set of tickers, **When** `get_top_pairs` runs, **Then**
   the returned list is unchanged from current behavior (correct quote filtering, min-volume
   filtering, descending-volume sort, `top_n` truncation).
2. **Given** the same call, **When** inspecting `app/data/manager.py::get_top_pairs` source,
   **Then** no `logger.info` call contains a literal `"DEBUG:"` string and no commented-out
   `# self.logger.debug(...)` line remains.

### User Story 2 - Chart timestamps are UTC-correct regardless of host timezone (Priority: P2)

**Why this priority**: Same defect class as the already-fixed indicator-DataFrame bug (slice 002)
and start-date bug (slice 003), just in the chart-rendering path — currently only "works" because
the deployment container's system timezone happens to be UTC.

**Independent Test**: Convert a known epoch-millisecond OHLCV batch through
`rendering/utils.py::convert_to_dataframe` and confirm the resulting index is UTC-aware and
numerically correct, independent of the process's system timezone — same test shape as slice 002's
`tests/analyzers/test_utils.py`.

**Acceptance Scenarios**:

1. **Given** a batch of OHLCV rows with known epoch-millisecond timestamps, **When** converted via
   `convert_to_dataframe`, **Then** the resulting `timestamp` column/index is timezone-aware UTC and
   numerically equal to each epoch value converted directly to UTC.
2. **Given** the same conversion, **When** run in principle under two different host system
   timezones, **Then** results are identical (verified the same way as slice 002: by asserting
   against a UTC-computed expectation rather than relying on process `TZ` switching, per that
   slice's established test-design decision).
3. **Given** unchanged column names/row count requirements, **When** converted, **Then** all
   original OHLCV columns (`open`, `high`, `low`, `close`, `volume`) and row count are preserved.

### User Story 3 - Calibration logger records UTC timestamps (Priority: P3)

**Why this priority**: Lowest priority — `CalibrationLogger` is currently dead code (confirmed: no
import of `utils.calibration` exists anywhere else in `app/`), so this fixes correctness-in-waiting
rather than an active production defect. Included for completeness since it was an explicitly
tracked finding and the fix is trivial.

**Independent Test**: Call `log_ohlcv` with a known-epoch candle and `_report_anomaly` (via a
triggering condition) and confirm both produce UTC-based timestamp strings, independent of host
timezone.

**Acceptance Scenarios**:

1. **Given** a candle with a known epoch-millisecond timestamp, **When** `log_ohlcv` logs it,
   **Then** the logged time string matches that timestamp converted to UTC (not host-local time).
2. **Given** a condition that triggers `_report_anomaly` (e.g. `high < low`), **When** the anomaly
   is recorded, **Then** its `timestamp` field is a UTC-aware ISO-8601 string (parseable, with a
   `+00:00` UTC offset).

### Edge Cases

- `get_top_pairs` with zero matching tickers: unchanged behavior — empty list, no exception (not
  modified by this slice, only characterized to prove no regression).
- `convert_to_dataframe` with an empty `historical_data` list: confirmed to raise `ValueError`
  (`pd.DataFrame([]).columns = [...]` length mismatch) both before and after this fix — the exact
  same pre-existing, out-of-scope bug already documented for `analyzers/utils.py`'s sibling function
  in slice 002 (Addendum). No caller passes an empty list today (`rendering/core.py::create_chart` is
  only invoked from `notifications/core.py::create_charts`, which skips empty candle periods), so
  this is characterized, not fixed, consistent with slice 002's precedent.
- `CalibrationLogger` remains unwired/dead code after this slice — this fix does not include wiring
  it into the live pipeline, which is out of scope (a design decision, not a defect).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `get_top_pairs` MUST NOT log any `"DEBUG:"`-prefixed string; any remaining diagnostic
  logging for this method MUST use `logger.debug`, not `logger.info`.
- **FR-002**: All dead, commented-out `logger.debug` lines in `get_top_pairs` MUST be removed.
- **FR-003**: `get_top_pairs`'s filtering, sorting, and truncation behavior MUST be unchanged and
  MUST gain test coverage (previously untested).
- **FR-004**: `rendering/utils.py::convert_to_dataframe` MUST construct its timestamp column/index
  directly as UTC-aware, without depending on the host process's system timezone (same fix pattern
  as slice 002's `analyzers/utils.py::convert_to_dataframe`: `pandas.to_datetime(..., unit='ms',
  utc=True)`).
- **FR-005**: `utils/calibration.py::CalibrationLogger.log_ohlcv`'s per-candle timestamp formatting
  MUST use UTC (`datetime.fromtimestamp(ts, tz=timezone.utc)`), not naive local time.
- **FR-006**: `utils/calibration.py::CalibrationLogger._report_anomaly`'s recorded timestamp MUST use
  UTC-aware `datetime.now(timezone.utc)`, not naive local time.
- **FR-007**: This feature MUST NOT change any public method signature, `config.yml` schema, or the
  chart image's visual content beyond the numerical correctness of its timestamp values (FR-004 is a
  correctness fix, not a display-format change).
- **FR-008**: Wiring `CalibrationLogger` into the live analysis/notification pipeline is explicitly
  OUT of scope for this feature (it remains available as an opt-in diagnostic utility, unchanged in
  that respect).

### Key Entities

- **`get_top_pairs` return value**: `List[str]` of market symbols, contract unchanged.
- **Chart DataFrame timestamp column/index**: gains the same UTC-aware guarantee already established
  for the indicator DataFrame in slice 002.
- **Calibration log line / anomaly record**: diagnostic-only output, gains UTC-aware timestamps.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All new tests pass, and the full existing suite (77 tests from slices 001-005)
  continues to pass unchanged — zero regressions, total test count strictly increases.
- **SC-002**: `grep -n "DEBUG:" app/data/manager.py` returns zero matches after this feature.
- **SC-003**: Every functional requirement (FR-001 through FR-006) is covered by at least one
  assertion that would fail if the corresponding change were reverted.
- **SC-004**: All three originating Convergence findings (001-F3, 002-F2, 002-F3) are marked
  resolved in their source `tasks.md` files, closing the loop opened by those slices.

## Assumptions

- No behavior change is intended for any code path beyond the six FRs above — this is a targeted
  cleanup of already-identified, already-scoped findings, not a new investigation.
- `CalibrationLogger` being dead/unwired code is noted as context (FR-008) but is not itself treated
  as a defect to fix in this slice — removing or wiring unused code is a separate design decision the
  operator has not asked for.
