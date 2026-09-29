# Validation Report: Twitter/X Attention-Spike Pilot (BTC only)

**Date**: 2026-09-28 | **Feature**: `specs/022-twitter-attention-pilot`

## Result: the pilot's core measurement method does not work — stopped early, honestly

The plan was to use `advanced_search_tweets`'s `tweet_count` field as a same-day mention-volume
metric, comparing each event's day against a baseline day 7 days prior. After querying 10 of the 41
planned date windows (5 of 22 events), a clear, disqualifying pattern emerged:

| Query (date) | `tweet_count` | `has_more` |
|---|---|---|
| 2025-12-09 | 19 | false |
| 2025-12-02 | 19 | false |
| 2025-12-17 | 18 | false |
| 2025-12-10 | 19 | false |
| 2025-12-18 | 19 | false |
| 2025-12-11 | 19 | false |
| 2026-01-12 | 19 | false |
| 2026-01-05 | 19 | false |
| 2026-01-29 | 19 | false |
| 2026-01-22 | 19 | false |

**Every single query returned ~19 tweets, regardless of the actual date, with `has_more: false`
(the API asserting there is nothing more to fetch).** `$BTC` realistically generates many thousands
of tweets per day — a real day-to-day mention count varying between 18 and 19 across ten
essentially random days is not plausible as a genuine total. The correct read is that
`advanced_search_tweets` returns a capped result set (roughly one page, ~19 tweets) for a broad
query like this, and `tweet_count`/`has_more` describe that capped response, not the true volume of
matching tweets in the exchange's full corpus for that window.

**This invalidates the pilot's core assumption** (that `tweet_count` for a `since:`/`until:` 1-day
window is a usable proxy for daily mention volume). Continuing to query the remaining 31 date windows
would have produced the same uninformative, ~19-flat series for every window — no attention spike
could ever be detected this way, since the ceiling is reached almost immediately regardless of actual
activity. Per this project's standing discipline (stop early and report honestly rather than run a
method already shown not to work), data collection was halted here rather than completing all 22
events against a metric already demonstrated to be flat/uninformative.

## What this means for the underlying idea

The idea itself (Twitter/X attention as a Wyckoff refinement signal) is not disproven — only this
specific, cheap measurement approach is. A genuine mention-volume time series would require one of:

1. **Exhaustive pagination**: follow `next_cursor` until the API itself reports no more results for
   real (if the true corpus is larger than one page, sustained pagination should eventually reveal
   that — this pilot didn't test whether pagination unlocks more results, since `has_more: false`
   was returned immediately each time, suggesting pagination would not help either without a
   narrower or differently-scoped query).
2. **A narrower query** (e.g., restricting to verified/high-follower accounts, or a specific
   sub-topic) small enough that the true count is genuinely at or below the page cap — trading
   coverage for a metric that actually varies.
3. **A different endpoint/parameter** in `getxapi` specifically designed for volume/counts rather
   than returning individual tweet objects (not explored in this pilot — worth checking
   `docs.getxapi.com` for a dedicated counts/volume endpoint before trying this again).

## Recommendation

**Do not proceed with the count-based version of this pilot.** Before spending further API calls on
Twitter/X data, check `docs.getxapi.com` for a purpose-built tweet-volume/counts endpoint (distinct
from `advanced_search_tweets`, which is built for returning tweet objects, not exhaustive counts).
If no such endpoint exists, the Twitter/X attention-signal idea from `specs/020-.../research.md`
should be deprioritized relative to the other candidates in that research (order-flow/taker-volume
work, already completed in slice 021) rather than re-attempted with a more expensive but
equally-flawed method.

This does not change the pending operator decision from slices 017-019: the extreme-volume Wyckoff
filter remains the only validated edge; this pilot neither adds to nor detracts from that.

## Assumptions and limitations

- Only 10 of 41 planned queries were run (halted early per the finding above) — this is intentional,
  not an oversight; running the remaining 31 would not have changed the conclusion.
- It remains possible that a differently-scoped query (narrower keyword, verified-only, etc.) would
  return a genuinely-varying count — not tested here.
