# Feature Specification: Twitter/X Attention-Spike Pilot (BTC only)

**Feature Branch**: `main` (Spec Kit feature directory: `specs/022-twitter-attention-pilot`)

**Created**: 2026-09-28

**Status**: Draft

**Input**: `specs/020-orderflow-and-social-data-research/research.md` item #2: pilot Twitter/X
attention as a Wyckoff refinement signal, scoped narrowly (BTC only, confirmed events only) before
any wider/costlier rollout, using `getxapi`'s confirmed-working historical search
(`since:`/`until:` verified to return real historical tweets, not just recent ones).

## Methodology (pre-declared before querying)

For each of BTC/USDT's 22 confirmed extreme-volume Wyckoff events (slice 017's filter, BTC-only
subset, ~10 months): query `$BTC` tweet count for two 1-day windows —

- **Signal window**: the calendar date (UTC) of the event.
- **Baseline window**: the same calendar date 7 days earlier (same weekday, controls for
  day-of-week posting patterns).

`attention_ratio = signal_day_tweet_count / max(baseline_day_tweet_count, 1)`. A ratio > 1 means more
`$BTC` chatter on the event's day than a comparable day a week prior.

**This is explicitly a pilot, not a powered validation**: n=22 is far below the ≥30 minimum this
project has used everywhere else (slices 017/019/021) — no in-sample/out-of-sample split, no
significance claims. The goal is to see whether the signal is even directionally interesting enough
to justify the cost of a properly-powered follow-up (more pairs, more history, or finer time
resolution), not to declare a validated edge from 22 data points.

## Requirements

- **FR-001**: MUST use `getxapi`'s real historical search (`advanced_search_tweets` with
  `since:`/`until:`), not a live/recent-only query.
- **FR-002**: MUST reuse the exact same 22 BTC/USDT events slice 017's methodology already
  identifies — not a new event search.
- **FR-003**: MUST report `attention_ratio` alongside each event's already-computed
  `expected_dir_return`, descriptively (correlation direction, simple high/low split) — explicitly
  NOT as a significance-tested claim, given n=22.
- **FR-004**: MUST NOT wire anything into any live path — same Principle III discipline as every
  prior validation slice.
- **FR-005**: The report MUST recommend, based on whether the descriptive pattern looks worth
  pursuing, whether a properly-powered follow-up (more pairs/history) is worth the added API cost —
  or whether it doesn't look promising enough to justify that spend.

## Success Criteria

- **SC-001**: All 22 events queried, `attention_ratio` computed and reported for each.
- **SC-002**: One clear go/no-go recommendation on a larger-scale follow-up.
- **SC-003**: Existing test suite unaffected.
