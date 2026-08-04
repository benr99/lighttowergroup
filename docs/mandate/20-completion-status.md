# 20 — Editorial Intelligence System: Running Completion Status

Living document. Updated as each milestone lands. **Status is claimed only for
working, tested code — never for a design document.**

Baseline: `143250a`. Production editorial selection is **unchanged**; everything
below is shadow-mode until Milestone 12 cutover.

---

## Milestone status

| # | Milestone | Status | Commit | Tests |
|---|---|---|---|---|
| 1 | Source foundation | **partial** | `c799de5`, `143250a` | probe tool, 41%→50% usable |
| 2 | Canonical intelligence object | **done** | `7674fb0` | 19 |
| 3 | Retrieval & enrichment layer | not started | — | — |
| 4 | Structured-data intelligence | not started | — | — |
| 5 | Event clustering | **done** | `7674fb0` | 13 |
| 6 | Classification & extraction | **done** | `6cf4b8b` | 17 |
| 7 | Scoring replacement | **partial** — eligibility done, importance scorer not started | `6cf4b8b` | 15 |
| 8 | Ranking & slate selection | not started | — | — |
| 9 | Benchmark | fixtures only | `38c87ca` | 9 |
| 10 | Article generation integration | not started | — | — |
| 11 | Observability & cost controls | **partial** — candidate audit done | `38c87ca` | 2 |
| 12 | Shadow validation & cutover | not started | — | — |
| 13 | Live verification | not started | — | — |
| 14 | Cleanup & documentation | not started | — | — |

Test baseline: **205 Python** (was 141), **24 Node**, `py_compile`,
`validate_publication`. **Zero expected-failure tests remain.**

---

## What is actually working

**Source registry (M1, partial).** 41% → 50% usable; 365 → 430 items/36h.
15 dead URLs repaired via autodiscovery, 85 unusable sources deactivated with
recorded reasons, 8 primary sources added. The hand-set `verified` boolean is
gone, replaced by a measured `health` block. `scripts/source_health_probe.py`
re-runs the diagnosis and can gate a workflow via `--min-healthy-pct`.

**Canonical intelligence object (M2).** `scripts/intelligence_object.py`.
The ranking unit is now an event/signal assembled from one or more documents,
not a URL. Evidence level is derived from what was actually retrieved, and
**recommended depth is capped by it** — validation rejects an object asking for
more analysis than its sources support. This is the direct fix for the
contradiction that produced two zero-article editions: the system was prompted
for an original thesis, then correctly refused to publish it for lack of
grounding. Facts carry provenance and must cite an evidence span or be flagged
as inference.

**Event clustering (M5).** `scripts/event_clustering.py`. Deterministic and
inspectable — no embeddings, no model call — so a merge can be explained and
regression-tested. Measured on the real 2026-08-03 corpus: 288 documents → 277
objects, 11 merges, all correct, zero false merges.

**Classification (M6).** `scripts/content_typing.py`. Populates the
`event_type` and `subsector` taxonomies that were fully specified in
`config/sectors.json` but hardcoded to `""` with a "TODO Phase 2" comment.

**Eligibility (M7, first half).** `scripts/eligibility.py`. Per-event-family
rules replace the single keyword gate. Both known false positives are rejected;
all true positives and the non-transaction macro story are retained.

---

## Verified outcomes against the live-run fixture

| item | old gate | new gate |
|---|---|---|
| Edge Computing explainer | eligible (matched `data center`) | **blocked** — `content_type=explainer` |
| Invesco interview | eligible (matched `investment` in a bio) | **blocked** — no material disclosure |
| Savills $1.1B acquisition | eligible | eligible |
| JPMorgan $750B commitment | eligible | eligible |
| Hamilton Lane $270m CV | eligible | eligible |
| Slate $1b SMA | eligible | eligible |
| ISM manufacturing (no $ amount) | eligible | eligible, typed `data_publication` |

---

## Remaining work, in dependency order

1. **M7 importance scorer** — 0–100 with documented band meanings, sector-relative
   magnitude, real novelty from event memory, restored routine/archive/promotional
   penalties. Blocked on nothing.
2. **M8 ranking and slate selection** — per-sector top ten, global top ten/thirty,
   soft diversity with a hard quality floor, "why rank 10 beat rank 11".
3. **M3 retrieval layer** — bounded, cached, per-domain limited, with explicit
   retrieval states. Needed before evidence levels can rise above
   `single_summary` for most objects.
4. **M4 structured data** — the only path to ten fed_macro items/day. See blocker.
5. **M9 benchmark** — build from the repaired universe once M3 raises evidence.
6. **M10–14** — generation integration, observability, cutover, live run, docs.

---

## Blockers and constraints

**`FRED_API_KEY` (M4).** Free, but an external credential. The mandate permits
optional keyed providers via environment variable; the provider must disable
itself cleanly when the key is absent and use deterministic fixtures in tests.
No code is blocked — activation is.

**fed_macro cannot reach ten items from feeds.** Measured: usable sources rose
6 → 14 while items rose only 5 → 7. Primary sources buy authority, not volume.
Ten fed_macro items per day requires the structured-data channel (M4), because
the events do not exist at that cadence in any news feed.

**26 blocked sources remain unreplaced.** CoStar, Colliers, Chief Investment
Officer and others return 403. Lawful substitutes need judgement about what
coverage is genuinely lost; this is the largest open source gap.

**Corroboration is rarer than the duplicate count suggested.** Ten of the eleven
clustering merges were the IREI / Institutional Real Estate pair, which share
canonical URLs — one document, not independent corroboration. Consolidation
alone will not raise evidence levels. That strengthens the case for M3 and M4.

---

## Rollback

Nothing to roll back yet: no production path imports any new module.
`v2_editorial.is_daily_article_candidate` and `select_daily_items` still decide
the edition. Cutover (M12) will add a versioned feature flag and retain the
legacy path until a live run is verified.
