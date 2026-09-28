# Tasks: Historical Validation of the SignalEnhancer Score/Quality Heuristic

**Input**: Design documents from `specs/007-signal-enhancer-validation/`

**Tests**: N/A (SC-003) — this is a one-time research script, not application code.

## Phase 1: User Story 1 - Measure real predictive value (P1)

- [X] T001 [US1] Write `validate_signal_enhancer.py`: fetch historical 4h OHLCV for the 15-pair
      basket (paginated, ~10 months) via real CCXT `fetch_ohlcv` (FR-002).
- [X] T002 [US1] Compute RSI(14), EMA(99), MACD histogram per pair via `talib`, matching what the
      real indicator classes compute internally.
- [X] T003 [US1] Detect signal events (RSI crosses below 30 = hot, above 70 = cold), one event per
      crossing, no lookahead (FR-003).
- [X] T004 [US1] Reconstruct `MarketContextData`/`AltStrengthData` per event using
      `app/analysis/market_context.py`'s exact formulas against historical closes, with the
      documented basket-as-market-proxy simplification for sentiment (FR-004).
- [X] T005 [US1] Score each event via the real, imported `SignalEnhancer._calculate_score` /
      `_score_to_quality` — no reimplementation (FR-001).
- [X] T006 [US1] Compute realized forward returns at the two pre-declared horizons (24h/72h) and the
      direction-normalized `expected_dir_return` (FR-005).
- [X] T007 [US1] Aggregate by quality tier: sample size, mean/median, win rate, both horizons
      (FR-006).
- [X] T008 [US1] Compute the permutation-test correlation p-value across all events (FR-006).
- [X] T009 [US1] Run the script against real Binance data; capture full output.

## Phase 2: User Story 2 - Record methodology and results (P1)

- [X] T010 [US2] Write `validation-report.md` with data source/range/pairs, full methodology,
      every simplifying assumption, complete results, and one explicit recommendation (FR-007).
- [X] T011 [US2] Apply FR-009: based on the recommendation, either adjust the
      `notify_all` detail/chart quality gate, or record a Convergence finding requiring operator
      sign-off — not both silently skipped.

## Phase 3: Polish

- [X] T012 Confirm the existing 88-test suite is unaffected (SC-003).
- [X] T013 [P] Refresh Graphify project graph.

## Dependencies & Execution Order

T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012 → T013.

## Phase 4: Convergence

Assessed 2026-09-28. 9/9 functional requirements verified. SC-001 exceeded (642 events, target
~60). SC-002 met (`validation-report.md` has concrete numbers and one explicit recommendation).
SC-003 confirmed (88/88 existing tests still pass, unaffected). 7/7 constitution principles
checked, no violations.

**Result**: the score shows no measurable predictive value (permutation p=0.87 at 24h, p=0.36 at
72h; the one tier reaching `A`, n=12, performed worse than B/C, not better). This triggers
Principle III's explicit fallback.

**SC-004 / FR-009 disposition**: recorded as a Convergence finding requiring operator sign-off
(FR-009's second branch), NOT applied as a unilateral code change — loosening
`notify_all`'s hardcoded `detail_min_quality`/`chart_min_quality` from `'A'` to informational-only
would materially increase live Telegram message volume and chart-rendering load for an active
deployment, which is a real operational cost the operator should decide on, not this session
alone.

## Convergence Findings

| ID | Gap Type | Severity | Source | Evidence | Remaining Work |
|----|----------|----------|--------|----------|----------------|
| F1 | unrequested | HIGH | Principle III | `validation-report.md`: SignalEnhancer's score/quality tier shows no measurable correlation with realized forward returns (642 events, 13 pairs, 10 months); the `A` tier (n=12) performed *worse* (8.3% win rate) than B/C (~52-61%) | **Operator decision (2026-09-28): option (b)** — leave `notify_all`'s `detail_min_quality`/`chart_min_quality` gate as `'A'` unchanged for now, pending a redesigned/recalibrated `SignalEnhancer` scoring heuristic and a fresh run of this same validation methodology against it. No code changed. Tracked here so the next slice that touches `SignalEnhancer`'s scoring weights knows a re-validation is the acceptance bar before restoring confidence in the gate, not just a new set of hand-tuned numbers. |
| F2 | unrequested | LOW | Scope boundary (this slice) | Only the RSI-based signal trigger was validated; `macd_cross` (also enabled in production) was not, since faithfully replaying historical crossover detection was judged out of scope | Future slice: extend this validation methodology to `macd_cross` signals |

**Outcome**: `tasks_appended` — F1 is a decision for the operator, not a defect to autonomously fix;
F2 is a natural scope extension for a future slice.
