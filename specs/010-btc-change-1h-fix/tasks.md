# Tasks: Correct btc_change_1h to a Real 1-Hour Percentage Change

## Phase 1: Tests first

- [X] T001 [P] Create `tests/analysis/__init__.py`.
- [X] T002 `tests/analysis/test_market_context.py`: normal computation (two known closed 1h candles
      → correct percentage), insufficient-data edge case (0/1 candles → 0.0), exchange-error edge
      case (`get_ohlcv` raises → 0.0, rest of context unaffected), and the specific regression
      (large 24h absolute ticker delta no longer produces an implausible percentage) (FR-001 through
      FR-005).

## Phase 2: Implementation

- [X] T003 `app/analysis/market_context.py`: add `_compute_change_1h(exchange)` using
      `self.dm.get_ohlcv(exchange, self.reference_pair, '1h')`; wire into `_get_btc_data` (now takes
      `exchange`) in place of the ticker's `change` field.
- [X] T004 Confirm T002 passes.

## Phase 3: Verification

- [X] T005 Run full suite inside `crypto-signal:dev` Docker image; confirm 115 existing + new tests
      pass (SC-001).
- [X] T006 Rebuild image, redeploy (`docker compose up -d --build`), confirm live
      `GET /market-context` shows a realistic `btc_change_1h` (SC-003).
- [X] T007 [P] Refresh Graphify project graph.
- [X] T008 Mark Convergence finding F1 (`specs/009-agent-api/tasks.md`) resolved.

## Phase 4: Convergence

Assessed 2026-09-28. 5/5 functional requirements verified by code + tests. 6 new tests added; full
suite now 121/121 passing (115 prior + 6 new), zero regressions. SC-002 directly verified: reverted
the fix via `git stash`, confirmed 2 of the 6 new tests failed exactly as predicted
(`test_normal_computation_uses_real_ohlcv`, `test_regression_...`), restored the fix, confirmed all
pass. SC-003 verified live: redeployed (`docker compose up -d --build`), `GET /market-context`
showed `btc_change_1h: 0.39` (plausible) vs. the pre-fix `-630.06`. 3/3 relevant constitution
principles checked (I, II, VI), no violations. Convergence finding F1 from
`specs/009-agent-api/tasks.md` marked resolved.

**Outcome**: `converged` — no additional tasks appended.
