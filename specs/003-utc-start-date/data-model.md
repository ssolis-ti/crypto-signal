# Phase 1 Data Model: Correct UTC Start-Date Calculation

No new entities; no persistent storage. One existing pure function's internal correctness property
changes:

## `CCXTDriver._calculate_start_date(time_unit, max_periods) -> int`

- **Before**: returns an epoch-millisecond value computed from the host process's local wall-clock
  time, mislabeled as UTC via `.replace(tzinfo=...)`.
- **After**: returns an epoch-millisecond value computed directly from the current UTC instant —
  numerically correct regardless of host system timezone.
- **Signature**: unchanged (FR-004).
- **Error behavior**: unchanged — invalid `time_unit` still raises `ValueError` from the existing
  regex-match check (FR-003).
