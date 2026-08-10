# Insights Generator v3 release report

Date: August 10, 2026

## Outcome

The v3 implementation replaces the unbounded per-sector generation path with a
single daily editorial contract: target three useful pieces, research no more
than five, and never fill below the quality floor. It carries retrieved evidence
all the way into the writer and reviewers, preserves real source authority,
holds unsupported work, records provider/spend/memory diagnostics, builds a
complete release allowlist, verifies the live deployment, and can revert only
the exact failed release.

## What changed

- Added a capped global publication slate and runner-up audit.
- Excluded administrative notices, digests, marketing, consumer housing, and
  finance stories without a real Light Tower beat anchor.
- Removed source-tier shortcuts that mislabeled secondary reporting as primary.
- Preserved retrieved full text and attributable facts in the writing dossier.
- Restricted flagship depth to three independent sources and two full texts.
- Added DeepSeek-to-OpenAI per-call fallback, bounded retries, invalid-JSON
  retry, secret-free latency/token diagnostics, and log compaction.
- Added durable editorial memory and shared daily spend enforcement.
- Added exact post-review diagnostics to every held draft.
- Normalized equivalent dollar representations during deterministic fact audit.
- Completed v3 article, image, related metadata, archive, RSS, sitemap, edition,
  decision, run-summary, and generated-files packaging.
- Made v3 the scheduled workflow default while preserving v2 as an explicit
  manual rollback path.
- Added live edition/article verification and guarded revert-based rollback.

## Real canary evidence

The corrected model-backed preview on August 10 processed 416 discovered items
into 391 clustered intelligence objects. Thirty-nine passed eligibility, 39
were enriched, 13 entered sector scouting slates, and three entered the bounded
publication slate.

All three tier-B articles cleared:

1. Equity Residential and AvalonBay's $71 billion multifamily merger;
2. the $2.3 billion mixed-use development south of Salt Lake City;
3. the New York Fed's STRIPS trading analysis.

Result: three written of three requested, zero held, zero failed, 15 successful
DeepSeek calls, zero fallback calls, approximately 411 seconds of concurrent
generation, and an estimated `$0.210` of generation spend.

The earlier preview had cleared only one of three. Diagnosis found a truncated
reviewer dossier, one malformed reviewer JSON response, missing hold diagnostics,
and false amount mismatches between equivalent units. The fixes addressed those
causes without weakening the pass criteria.

## Validation evidence

- 409 Python tests passed.
- The existing publication repository validated.
- All configured JavaScript syntax checks passed.
- 24 Node tests passed.
- Deployment verification and rollback behavior have dedicated regression tests.
- A publication-package test proves memory, spend, provider log, source health,
  edition files, and public pages are carried in the release allowlist.

## Remaining release actions

At the time this report was written, the code had passed local and real-canary
validation. Final acceptance still requires the cutover commit to reach `main`,
the GitHub Actions pull-request permission to be enabled, a production v3
publish run to complete, the live verifier to confirm the edition and each page,
and a second production-equivalent run to prove durable memory and repeat safety.

The authoritative operator procedure is `docs/AGENT_OPERATIONS.md`.
