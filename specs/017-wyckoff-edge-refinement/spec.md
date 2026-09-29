# Feature Specification: Search for a Trade-Worthy Wyckoff Edge (In-Sample/Out-of-Sample)

**Feature Branch**: `main` (Spec Kit feature directory: `specs/017-wyckoff-edge-refinement`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: User description: "Busca el edge entonces, se requieren buenas alertas potenciales a
subir, es decir si me avisa en Telegram que hay un indicio o probabilidad alta yo pueda operarla."
Slice 015 found a raw Spring/Upthrust win rate of 52.6%-54.8% — statistically significant, but too
small to responsibly send as a "trade this" Telegram alert. The operator wants a genuinely
higher-confidence signal before anything reaches Telegram, not the aggregate edge as-is. This slice
searches, honestly and without unilaterally shipping anything, for a filter or combination of filters
that sharpens the raw edge into something actually worth alerting on.

## Why this needs its own slice, not just "add filters and ship"

Testing many candidate filters against the same 2,839-event dataset and picking whichever one looks
best is a classic multiple-comparisons trap — with enough candidate cuts of the data, *something*
will look significant by chance. This slice's core discipline is an **in-sample / out-of-sample
split**: any candidate filter must show a real lift on data it wasn't chosen using, or it is reported
as likely noise, not as a finding — the same "don't trust an untested heuristic" posture as
Constitution Principle III, applied one level deeper (don't trust an untested *refinement* of an
already-validated-as-weak heuristic either).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Test specific, well-motivated candidate filters, not an unprincipled search (Priority: P1)

**Why this priority**: The operator wants alerts they can act on; shipping a filter that merely
overfit slice 015's specific 10-month sample would be worse than shipping nothing (false confidence).

**Independent Test**: Reuse slice 015's event dataset (same 2,839 Spring/Upthrust events, same
fetch). Split chronologically: first ~70% of events (in-sample) to evaluate each candidate filter,
last ~30% (out-of-sample, strictly later in time) to confirm any promising filter still holds — never
the reverse, and never re-splitting after seeing which split looks better.

**Acceptance Scenarios**:

1. **Given** the full event set, **When** split chronologically, **Then** the out-of-sample set
   contains only events with `timestamp` after every in-sample event's `timestamp` (no shuffling —
   this mirrors real deployment, where a filter is chosen from past data and applied to the future).
2. **Given** each candidate filter (below), **When** evaluated in-sample, **Then** its win rate,
   mean/median return, and sample size are reported.
3. **Given** a candidate filter that looks promising in-sample (e.g., win rate materially above
   slice 015's ~53-55% baseline, with adequate sample size), **When** evaluated out-of-sample,
   **Then** its out-of-sample performance is reported honestly alongside the in-sample number —
   including if it collapses back toward baseline (the expected behavior for an overfit filter).
4. **Given** a candidate filter that does NOT hold out-of-sample, **When** the report concludes,
   **Then** it is explicitly marked as "did not replicate," not quietly dropped from the report.

### User Story 2 - Candidate filters are Wyckoff-motivated, not arbitrary data mining (Priority: P1)

**Why this priority**: Per the research in `specs/012-.../research.md`, the whole premise of this
investigation is that Wyckoff's *specific* structural logic (cause-effect, higher-timeframe context)
might carry real signal where naive indicator scoring didn't — so the candidates tested should come
from that theory, not from blindly sweeping every column for the best-looking split.

**Independent Test**: Each candidate filter below is tied to a specific, pre-stated Wyckoff rationale
before it is tested, not chosen after peeking at results.

**Candidates**:

1. **Higher-timeframe trend alignment**: a Spring is more credible as genuine accumulation when the
   1D trend context is not actively bearish (and symmetrically for Upthrust/bearish). Computed via
   1D closes' relation to a 1D EMA (reusing `talib.EMA`, same library the codebase already uses
   everywhere).
2. **Range compression (Wyckoff's Cause-and-Effect law)**: a tighter trading range before the break
   (`range_width_pct` from `WyckoffPrimitives.detect_trading_range`, slice 014) implies more "cause"
   built up, and Wyckoff theory predicts a larger subsequent "effect." Tested as: does a below-median
   `range_width_pct` at the break correlate with a larger subsequent move?
3. **True climax at the break** (`WyckoffPrimitives.is_climax`, slice 013 — effort-without-result,
   stricter than slice 015's simple `relative_volume >= 1.5` cut) vs. a break with high volume but
   without the climax's low-result signature.
4. **BTC market regime alignment** (reusing `MarketContext`'s existing trend classification): does a
   Spring during a non-bearish BTC regime outperform one during a bearish regime (and the Upthrust
   mirror)?

### Edge Cases

- If a candidate filter's in-sample subset is too small (<30 events, given the out-of-sample split
  will roughly halve it again) to say anything useful, it is reported as "insufficient sample to
  evaluate," not force-fit to a conclusion.
- If NO candidate filter survives the out-of-sample check, the report MUST say so plainly — "no
  trade-worthy edge found in this investigation" is an acceptable, honest outcome, not a failure to
  hide.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The search MUST reuse slice 015's exact event-generation logic (same
  `detect_springs`/`detect_upthrusts`, same basket, same horizons) — not a new, incompatible dataset.
- **FR-002**: The evaluation MUST use a chronological in-sample/out-of-sample split (FR per User
  Story 1) for every candidate filter — no filter is reported as "working" based on in-sample
  performance alone.
- **FR-003**: Every candidate filter tested MUST be listed in the report whether or not it worked —
  no silent discarding of filters that didn't pan out (this is what separates honest research from
  cherry-picking).
- **FR-004**: This feature MUST NOT wire any filter into `SignalEnhancer`, `Behaviour`, or
  `notify_all` — even a filter that survives the out-of-sample check is a candidate for a follow-up
  implementation slice, not something this research slice ships directly (Constitution Principle III:
  validate, then build, as two separate, explicit steps).
- **FR-005**: The report MUST state a clear recommendation: if a filter survives with a genuinely
  actionable win rate/magnitude (operator's bar: something they'd actually feel comfortable acting on
  — materially better than a coin flip, not just statistically distinguishable from one), name it
  specifically as the candidate for a follow-up "wire it to Telegram" slice; if none survive, say so
  and suggest what (if anything) is worth trying next.

### Key Entities

- **`FilterEvaluation`**: `(filter_name, in_sample_n, in_sample_win_rate, in_sample_mean_return,
  out_of_sample_n, out_of_sample_win_rate, out_of_sample_mean_return, verdict)` where verdict is one
  of `confirmed` / `did_not_replicate` / `insufficient_sample`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All four candidate filters (or as many as data permits) are evaluated in-sample and
  out-of-sample, with concrete numbers for both.
- **SC-002**: The report's final recommendation is unambiguous: either a specific, named, validated
  filter + horizon is identified as ready for a follow-up implementation slice, or the report
  concludes none were found — never left ambiguous.
- **SC-003**: The existing test suite is unaffected (research artifact, consistent with slices 007/
  011/015).

## Assumptions

- "Actionable" is operationalized as: out-of-sample win rate materially above slice 015's baseline
  (e.g., >60%) AND out-of-sample sample size large enough (>=30) that the operator could plausibly
  see several qualifying alerts per month, not one every few months — both stated up front so the bar
  isn't quietly lowered if results come in weak.
- This slice answers "does a better filter exist in the data we already have," not "would this be
  profitable after real trading costs/slippage/execution" — that is a separate question for whenever
  (if ever) this becomes a real trading decision aid, not just an alert.
