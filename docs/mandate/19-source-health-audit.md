# 19 — Phase 2, Workstream 1: Source Health Audit

**Status:** Workstream 1 deliverable. No source config changed yet.
**Date:** 2026-08-03
**Tool:** `scripts/source_health_probe.py` (reproducible; writes `.editorial-state/source-probe.json`)

---

## Headline

**Only 82 of 198 configured sources (41%) are usable.** The entire daily news
universe reaching the pipeline is **365 items per 36 hours**, before
deduplication, eligibility or scoring.

The Phase 1 audit assumed the ranker was choosing badly from an adequate pool.
It is not. It is choosing from a pool roughly 60% of which never arrives.

This is the difference the mandate asked us to draw, and the answer is
unambiguous:

> It is not that no stories existed. It is that **no stories were discovered**,
> because the pipes are broken.

---

## Why the previous "158 verified feeds" figure was wrong

`config/sources.json` marks 164 sources `"verified": true`. **87 of those 164 —
53% of every "verified" source — are not usable today.** The `verified`
flag records a one-time manual check that has since rotted and is never
revalidated. Nothing in the pipeline tests it.

The production ingester reports a single undifferentiated `empty` for any feed
that yields nothing, which is why 404s, bot blocks, HTML pages and genuinely
quiet publications all looked identical and none looked urgent.

---

## Failure breakdown

| status | count | meaning | action |
|---|---|---|---|
| healthy | 66 | items inside the 36h window | keep |
| quiet_but_healthy | 15 | valid feed, nothing new today | keep |
| **not_found (404)** | **48** | dead feed URL | replace URL |
| **blocked (403)** | **26** | publisher refuses automated fetch | respect; find licensed/primary alternative |
| html_not_feed | 11 | URL returns a web page, not a feed | wrong URL |
| not_a_feed | 7 | NewsAPI discovery pseudo-entries | not RSS; excluded from feed math |
| stale | 7 | newest item 7–30 days old | keep, do not rely on |
| abandoned | 6 | newest item >30 days old | remove/replace |
| empty_feed | 4 | parses, zero entries | verify still published |
| dns_or_connection_error | 3 | host does not resolve | replace |
| http_490 | 2 | nyc.gov bot rejection | replace |
| server_error / read_timeout / tls_error | 3 | transient or misconfigured | recheck |

Notable dead or blocked names: Reuters Business (host does not resolve —
Reuters retired public RSS), Wall Street Journal, CoStar News, Colliers
Insights, American Banker, Moody's CRE, NAREIT, Axios Pro Rata, Bisnow, SEC
Testimony, Chief Investment Officer.

---

## Sector coverage matrix — the critical result

Target: **ten ranked stories per sector per day.**

| sector | sources | usable | usable % | items / 36h | tier-1 sources | tier-1 usable | verdict vs target |
|---|---|---|---|---|---|---|---|
| commercial_real_estate | 95 | 38 | 40% | 186 | 14 | 8 | plausible |
| private_equity | 35 | 18 | 51% | 97 | 2 | 2 | plausible |
| energy | 24 | 13 | 54% | 81 | 0 | 0 | tight, no tier-1 |
| banking_credit | 45 | 18 | 40% | 61 | 16 | **8** | tight |
| data_centers | 10 | 3 | 30% | 25 | 0 | 0 | **cannot support 10** |
| local_government | 13 | 4 | 31% | 17 | 3 | 3 | **cannot support 10** |
| **fed_macro** | 24 | **6** | **25%** | **5** | 11 | **3** | **impossible** |

**fed_macro yields five items per 36 hours.** Ten ranked Fed and macro stories
per day cannot be produced from five items. No amount of ranking, enrichment or
rubric design changes that. Eleven of its sources are tier-1 and only three
work.

Those raw counts are also *pre-dedup*. Phase 1 measured ~5% near-duplicate rate
in the corpus, and the true figure after event clustering will be lower still.

---

## What this means for the mandate

The instruction was: if the system returns zero, assume discovery failed rather
than that the world was quiet. That instinct was exactly right, and this is the
proof.

It also reorders the plan. Workstreams 2–10 — enrichment, event clustering,
taxonomy, benchmark, shadow scorer, calibration — are all still needed and the
Phase 1 findings all still stand. But **none of them can be validated against a
corpus that is missing 60% of its inputs.** Building a benchmark on today's pool
would calibrate the new ranker against an unrepresentative universe and bake the
deficiency into the thresholds.

Source repair is now the critical path.

---

## Recommended sequence for source repair

1. **Fix the 48 dead URLs.** Most publications still ship feeds at a moved path.
   Mechanical, high yield: potentially the single largest recovery available.
2. **Replace the 26 blocked sources with lawful equivalents.** Do not attempt to
   bypass a 403. Where a publisher blocks automation, substitute primary
   sources covering the same events.
3. **Fix fed_macro with primary data, not trade press.** The Federal Reserve,
   Treasury, BLS, BEA, FRED and SEC all publish structured, free, automation-
   friendly releases. The probe already shows federalreserve.gov speeches, H.8
   and testimony feeds resolving — they are classified `stale` only because they
   are legitimately low-frequency. They are exactly the primary sources the
   editorial mandate calls for and they are currently near-unused.
4. **Build out data_centers and local_government**, which have no working tier-1
   source at all.
5. **Replace the `verified` flag with probe output.** A boolean set by hand once
   is worse than no signal, because it is trusted. Schedule the probe and gate
   on `--min-healthy-pct`.
6. **Then** proceed to enrichment and clustering against a repaired universe.

---

## Tooling delivered

`scripts/source_health_probe.py`

- Probes every configured source concurrently with explicit connect/read
  timeouts (8s/15s) and bounded workers — directly addressing the Phase 1
  finding that `feedparser.parse` has no timeout and can hang a run.
- Classifies each source into an actionable status rather than a generic
  "empty", and records HTTP status, redirect target, content type, latency,
  entry counts, in-window counts and newest-item age.
- Emits a sector coverage rollup.
- Exits non-zero when usable coverage falls below `--min-healthy-pct`, so it can
  gate the weekly health check (acceptance criterion 15: alert when coverage is
  too weak to support the intended slate).
- Never edits `config/sources.json`. Repair remains a reviewed change.

Output is gitignored; retain it via workflow artifacts as with the candidate
audit.

---

## Open question this raises for the product

The ten-per-sector target is achievable for commercial real estate and private
equity on today's inputs. It is not achievable for fed_macro, data centers or
local government without new sources, and for fed_macro it will likely never be
achievable from news feeds alone — the Fed simply does not generate ten
consequential distinct events per day.

For fed_macro the honest unit may not be ten stories but a smaller number of
genuine events plus structured data releases. Worth deciding before the ranker
is calibrated to a target its sector cannot supply.
