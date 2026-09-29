# Tasks: Twitter/X Attention-Spike Pilot (BTC only)

## Phase 1: Implementation

- [X] T001 Compute BTC/USDT's 22 confirmed extreme-volume events (slice 017's filter) and their
      signal/baseline date windows (FR-002).
- [X] T002 Query `getxapi`'s `advanced_search_tweets` with `since:`/`until:` for signal/baseline
      windows (FR-001).
- [X] T003 **Halted after 10/41 queries**: `tweet_count` returned ~19 for every query regardless of
      date, with `has_more: false` — the metric is capped/uninformative, not a real daily count.
      Continuing would not change the conclusion (see validation-report.md).

## Phase 2: Reporting

- [X] T004 Write `validation-report.md`: documented the capped-count finding, what it means for the
      underlying idea, and a concrete recommendation (check for a dedicated counts endpoint before
      retrying) (FR-005, SC-002).

## Phase 3: Verification

- [X] T005 Confirm FR-004: no code wired into any live path.
- [X] T006 Confirm the existing test suite is unaffected (SC-003) — no `app/` code touched.
- [X] T007 [P] Refresh Graphify project graph.

## Phase 4: Convergence

Assessed 2026-09-28. 4/5 functional requirements verified (FR-002 through FR-005); FR-001 partially
met (real historical search confirmed working, per specs/020, but the specific `tweet_count`-based
volume metric proved unusable). SC-001 not fully met by design (10/22 events queried, not all 22 —
justified stop, not an oversight). SC-002 met (clear recommendation: don't proceed with this method,
check for a dedicated counts endpoint first). SC-003 confirmed (no code touched).

**Result**: `advanced_search_tweets`'s `tweet_count` field returns a capped (~19) result count
regardless of actual date/query, making the pilot's core "attention spike" measurement infeasible as
designed. This is a genuine, disqualifying finding, not inconclusive noise — implausible for a highly-
discussed asset like BTC to show flat ~19 tweets/day across random historical dates. Stopped
collection early (10/41 queries) once the pattern was unambiguous, avoiding further API spend on an
already-falsified method.

## Convergence Findings

| ID | Gap Type | Severity | Source | Evidence | Remaining Work |
|----|----------|----------|--------|----------|----------------|
| F1 | unrequested | LOW | This slice's own result | `advanced_search_tweets` caps results (~19) regardless of query date; not suitable for volume/count-based signals as used here | Future (optional, low priority): check `docs.getxapi.com` for a dedicated tweet-volume/counts endpoint (distinct from the tweet-object search used here) before attempting a Twitter-based signal again. Not blocking any pending decision. |

**Outcome**: `tasks_appended` — F1 is a method note for any future attempt, not a pending decision.
The extreme-volume Wyckoff filter (slice 017) remains the project's sole validated edge.
