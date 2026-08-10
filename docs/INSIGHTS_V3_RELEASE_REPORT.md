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

## Real preview evidence

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

## Production cutover evidence

The production cutover was deliberately fail-closed, and the first run proved
that protection. [Run 31394652314](https://github.com/benr99/lighttowergroup/actions/runs/31394652314)
generated and cleared five articles, but the shared HTML renderer rejected a
missing human-readable `date` field. The workflow published nothing, preserved
the full diagnostic artifact, and left the live site untouched. Pull request
[#13](https://github.com/benr99/lighttowergroup/pull/13) repaired the renderer
contract and added a real-renderer regression test.

[Run 31396193104](https://github.com/benr99/lighttowergroup/actions/runs/31396193104)
then completed the entire production workflow and live verifier. It safely
published the cleared subset of one article and retained two held drafts for
diagnosis. The release commit was `4bddeecb2757d056579dad4f001e70764a3629a7`.
The held-draft evidence led to a bounded second correction/re-review cycle and
the installation of the missing OpenAI fallback secret; pull request
[#14](https://github.com/benr99/lighttowergroup/pull/14) shipped that recovery.

[Run 31398418734](https://github.com/benr99/lighttowergroup/actions/runs/31398418734)
was the second consecutive successful production run. It published three of
three requested articles with zero holds, zero generation failures, and zero
duplicate republishes. The live verifier confirmed the edition and all three
pages. Durable state carried the prior `$0.210` spend into the run, added
`$0.130`, and correctly recorded `$0.340` for the day. The production release
commit was `a18692d62fbedad4e2e64a1eb90cdb8988b10f31`.

Across the two successful production runs, four articles were published on
August 10. A final production inspection found that the article pages correctly
displayed one source each while the compact edition JSON displayed zero. The
edition builder now preserves the audited count, article assembly has a
source-list fallback, both public edition files were corrected in place, and
regression tests cover both paths.

## Final validation evidence

- 413 Python tests passed on the production-synchronized branch.
- The complete publication repository, including the corrected August 10
  edition, validated.
- All 11 configured JavaScript syntax checks passed.
- 24 Node tests passed.
- Deployment verification and rollback behavior have dedicated regression tests.
- A publication-package test proves memory, spend, provider log, source health,
  edition files, and public pages are carried in the release allowlist.
- Four live article URLs returned HTTP 200 with the expected title and a
  one-source label during final acceptance.

## Release configuration and recovery

- Pull request [#12](https://github.com/benr99/lighttowergroup/pull/12) delivered
  the v3 cutover; pull requests #13 and #14 delivered production-discovered
  hardening without bypassing review or deployment checks.
- Scheduled workflow invocations select v3. Operators can still select v2
  manually as the explicit rollback engine.
- GitHub Actions has write permission and may create/approve the release pull
  request used by the publication workflow.
- Both `DEEPSEEK_API_KEY` and `OPENAI_API_KEY` are installed. DeepSeek remains
  preferred and OpenAI remains the per-call fallback.
- Live verification checks the newest edition plus every published article.
- Automatic rollback uses a normal revert and proceeds only when both local
  `HEAD` and `origin/main` still match the exact failed release SHA; it never
  force-pushes or overwrites intervening work.
- There were no open pull requests at the final configuration audit.

## Acceptance

The release checklist is complete. v3 is shipped on `main`, is the scheduled
production engine, has completed two consecutive end-to-end production runs,
has proven durable memory and repeat safety, and has live output. What remains
is ordinary daily operation and monitoring, not release work.

The authoritative operator procedure is `docs/AGENT_OPERATIONS.md`.
