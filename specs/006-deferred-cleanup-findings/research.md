# Phase 0 Research: Clean Up Deferred Convergence Findings

## Decision: Demote, don't delete, get_top_pairs' diagnostic logging

**Rationale**: The two `self.logger.info(f"DEBUG: ...")` calls carry real diagnostic value (ticker
count, matched-pairs count) — the problem per Constitution Principle VII is the level/prefix
(`info` + redundant literal `"DEBUG:"` text), not the existence of the log line. Demoting to
`logger.debug(...)` without the prefix keeps the information available to an operator who raises
the log level, without permanently cluttering `info`-level output.

**Alternatives considered**: Deleting the log lines entirely — rejected; loses diagnostic signal
that isn't itself the problem. The two *commented-out* `# self.logger.debug(...)` lines are
different: genuinely dead code with no runtime effect either way, so those are simply removed
(FR-002), not demoted.

## Decision: Fix rendering/utils.py::convert_to_dataframe with the identical pattern as slice 002

**Rationale**: This is the exact same defect class already fixed twice (slices 002 and 003):
`pandas.to_datetime(dataframe['timestamp'], unit='ms', utc=True)` replaces the naive
`datetime.datetime.fromtimestamp(x / 1000.0)` lambda-apply. No new design decision needed; reusing
an already-validated pattern minimizes risk. `rendering/utils.py::convert_to_dataframe` is a
different function from `analyzers/utils.py::IndicatorUtils.convert_to_dataframe` (already fixed) —
this one is only called from `rendering/core.py::ChartRenderer.create_chart`, confirmed by grep
(single call site), so the blast radius is limited to chart-image generation.

**Alternatives considered**: Threading `settings.timezone` through to display chart timestamps in
the operator's configured local time (rather than UTC) — rejected as out of scope for this slice;
that would be a presentation *enhancement*, not fixing the identified correctness defect (Principle
V requires UTC internally; today's naive local time isn't even reliably that). Recorded as a
possible future enhancement, not a defect.

## Decision: Fix calibration.py's two naive-datetime call sites, leave the module unwired

**Rationale**: `CalibrationLogger` is confirmed dead code (no import anywhere outside its own file),
so this fix addresses correctness-in-waiting rather than an active bug — but it was an explicitly
tracked Convergence finding (002-F3) and the fix is a one-line change per call site. Wiring the
logger into the live pipeline is a separate, unrequested feature decision, explicitly out of scope
(FR-008).

**Alternatives considered**: Deleting the unused module — rejected; that's a design decision about
dead code the operator hasn't asked for, distinct from fixing the specific naive-datetime finding
that was tracked against it.
