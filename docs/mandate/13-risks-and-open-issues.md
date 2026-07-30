# 13 — Risks and Open Issues

A candid assessment of remaining risks, uncertainties, and incomplete work for the Light Tower Group Insights Intelligence Engine expansion from single-sector CRE to a 7-sector institutional intelligence platform. This document is meant to be honest, not aspirational. Risks are rated by likelihood (Low/Medium/High) and impact (Low/Medium/High/Critical).

---

## Technical Risks

### Risk 1: LLM Classification Accuracy for New Sectors

**Likelihood:** High | **Impact:** High

The current system uses regex-based topic extraction fine-tuned for CRE. Expanding to PE, data centers, energy, banking, federal policy, and local government requires new regex patterns and entity lists that do not yet exist. The LLM classification fallback for ambiguous cases may produce inconsistent results for unfamiliar sectors with specialized vocabulary.

Specific concerns:
- PE and banking share significant vocabulary (capital deployment, deal financing, sponsor, LP). The classifier may confuse these sectors.
- Data center stories about power procurement may be misclassified as energy_infrastructure.
- Federal policy stories about CRE-relevant regulation (e.g., SEC rules affecting REITs) may be misclassified as federal_policy when the CRE audience needs them under CRE.
- Local government zoning stories may not trigger any classification patterns at all, defaulting to LLM fallback at higher cost.

**Mitigation:**
- Start with source-based priors — a story from PE Hub IS private equity, a story from Data Center Dynamics IS data centers. Trust the source when sector_weight is 1.0.
- Use LLM only for genuinely ambiguous cases (sector_weight < 0.7, multi-way regex ties, unknown entities).
- Run in shadow mode for 2 weeks before publishing non-CRE content. Compare LLM classifications against human judgment.
- Cache LLM classification results by content_hash to avoid duplicate calls.

**Status:** Classification pattern and entity lists need development. Classification accuracy will be measured in Phase 2. Currently no non-CRE classification has been tested. Target: >90% accuracy for source-based + regex, >75% for LLM fallback. If LLM accuracy is below 75%, the system will misclassify enough stories to corrupt sector feeds.

---

### Risk 2: Article Quality for Non-CRE Sectors

**Likelihood:** High | **Impact:** Critical

The writing prompts in `enhanced_prompts.py` were built for CRE capital markets. The narrative financial writing style may not transfer cleanly to all seven sectors. Each sector requires domain-specific vocabulary, structural conventions, and analytical framing.

Specific concerns:
- A data center power procurement story requires understanding of MW vs. MWh, PPA structures, interconnection queues, and hyperscale tenant dynamics — domain knowledge the current prompts don't have.
- Energy infrastructure stories need to distinguish between project finance, tax equity, regulatory approvals, and commodity market dynamics — very different from CRE deal analysis.
- Local government zoning stories need to explain planning processes, environmental review (NEPA/CEQA), and political dynamics — a fundamentally different voice from financial analysis.
- PE deal stories may read like CRE deal stories if the prompt doesn't adapt (substitute "cap rate" for "MOIC", "tenant" for "portfolio company").
- The system currently has no prompt version tracking, so prompt degradation cannot be detected automatically.

**Mitigation:**
- Develop sector-specific system prompts in Phase 4, each with domain-appropriate vocabulary, structure, and examples.
- Start with brief format for unfamiliar sectors; graduate to flagship as prompts mature.
- Test generated articles against human review before publishing.
- Maintain a "golden set" of 10 example articles per sector for regression testing.
- Version all prompts in config/prompts.json. Record which prompt version was used for each article.

**Status:** Sector prompts not yet written. The 6 new prompts are spec'd in Phase 4 but not drafted. Quality unknown until tested. This is the highest-impact risk because low article quality directly damages editorial credibility.

---

### Risk 3: Source Reliability at Scale

**Likelihood:** High | **Impact:** Medium

Of the current ~103 feeds, 48 returned empty on the latest run — a 46% failure rate. Adding 100+ new feeds from less-established sources will likely increase the absolute failure rate even if the percentage improves. Many proposed feeds for local government and energy infrastructure may not have stable or reliable RSS.

Specific concerns:
- PE Hub, Buyouts, and PitchBook may be fully or partially paywalled, producing summary-only RSS entries that lack sufficient content for enrichment.
- Data center trade publications (Data Center Dynamics, Data Center Frontier) may have RSS feeds but low update frequency (3-5 articles/week, not daily).
- Local government RSS feeds are notoriously unreliable or nonexistent. Many municipalities only publish meeting agendas as PDFs (unparseable) or on web pages without RSS.
- NewsAPI queries (proposed as fallback for local government) may not surface enough locality-specific stories with the correct institutional framing.
- The "long tail" of low-frequency feeds will be hardest to maintain. Feeds that produce 0 items for 7 consecutive days should be moved to weekly fetch only.

**Mitigation:**
- Mark all unverified feeds clearly with `"needs_verification": true` in sources.json.
- Implement aggressive source health monitoring with per-source metrics (fetch time, items per run, success rate, sector distribution).
- Auto-disable feeds after 3 consecutive failures with 24-hour cooldown (existing circuit breaker).
- Prioritize sources with proven RSS availability. De-prioritize sources that require custom scrapers.
- Use NewsAPI as a supplemental source, not a replacement for dedicated feeds.
- Accept that some sectors (local government) may produce fewer articles than others until source quality improves.

**Status:** Of the 115 proposed new feeds, approximately 60% are marked [NEEDS VERIFICATION]. Some may not exist, may have moved behind paywalls, or may have been discontinued since the source registry was compiled (document 05-source-registry.md). Actual available feed count is unknown until validation runs.

---

### Risk 4: Scale and Cost at 210 Articles Per Day

**Likelihood:** Medium | **Impact:** Medium

The cost model estimates ~$67/month at 210 articles/day. But this assumes efficient LLM usage: classification uses LLM for <15% of candidates, enrichment is limited, and generation produces concise articles (average 350 words). If actual usage patterns differ, costs could be 2-3x higher.

Specific concerns:
- If classification requires LLM calls for 40%+ of 2000 daily candidates, that's 800 LLM calls just for classification. At ~$0.00015/call (DeepSeek mini), daily classification cost = $0.12. But if OpenAI is used as fallback, cost is 5-10x.
- DeepSeek rate limits and API availability at this scale are unknown. If DeepSeek throttles or goes down, the OpenAI fallback at higher cost kicks in.
- Full-text enrichment (trafilatura) requires one HTTP request per source per article. At 210 articles × average 3 sources each = 630 web requests. Not a cost concern but a latency concern.
- Article generation cost per article: DeepSeek ~$0.008/article (input + output tokens), OpenAI fallback ~$0.04/article. Daily: $1.68 (DeepSeek) vs. $8.40 (OpenAI).

**Mitigation:**
- Maximize deterministic classification and scoring. Use LLM sparingly and only for ambiguous cases.
- Implement cost caps in config/cost_limits.json (daily: $3.00, monthly: $90.00).
- Test at increasing volumes over 2 weeks before full production.
- Track cost per article per sector. Identify cost outliers.
- Budget for OpenAI fallback costs as contingency (assume 10% of calls use fallback).

**Status:** Cost estimates are theoretical based on DeepSeek's public pricing (July 2026). Actual costs unknown until production runs at scale. The current pipeline (single-sector CRE, 0-5 articles/day) costs approximately $0.05-0.10/day in LLM calls. Extrapolating to 210 articles/day across 7 sectors with full pipeline is uncertain. Risk increases if DeepSeek pricing changes.

---

### Risk 5: GitHub Actions 6-Hour Timeout

**Likelihood:** Low | **Impact:** Critical

The current pipeline runs in ~3-5 minutes when it produces 0 articles (signal gate passes 0 stories). At 2000+ candidates with classification, scoring, generation for 210 articles, runtime could approach or exceed the 6-hour GitHub Actions timeout (the hard limit for public repositories on the free tier).

Specific concerns:
- Full-text enrichment (trafilatura) for 210 articles × average 3-5 sources each = 630-1050 web requests. At 2-5 seconds per request (conservative), that's 21-87 minutes just for enrichment.
- LLM generation for 210 articles at 5-15 seconds each (model latency + output generation) = 17-52 minutes.
- LLM classification for ambiguous cases: variable, but potentially 200-400 calls at 3-5 seconds each = 10-33 minutes.
- Ingestion of 200+ feeds: 10-30 minutes at MAX_WORKERS=10.
- Scoring, ranking, publishing overhead: 15-30 minutes.
- Total low estimate: 63 minutes. Total high estimate: 212 minutes (~3.5 hours). This is within the 6-hour limit but the high estimate plus unexpected delays (slow feeds, retries, API timeouts) could push close to the boundary.
- The OpenAI fallback adds latency (often 2-3x slower than DeepSeek for comparable output).
- GitHub Actions runners have 2 CPU cores and 7GB RAM. CPU-bound operations (regex across 2000 items, JSON serialization of 2000 Items at ~2KB each = 4MB) could become bottlenecks.

**Mitigation:**
- Concurrent phase execution where possible (ingestion + classification can run together).
- Skip full-text enrichment for Tier 3 (brief_format) and Tier 4 (deal_tape) stories. Use RSS description only. This eliminates ~70% of enrichment web requests.
- Implement per-phase timeouts using the existing checkpoint.py.
- Consider GitHub Actions larger runner (Ubuntu 4-core, $0.008/min) if latency exceeds 3 hours.
- Split into separate workflow jobs (Phase 6 migration plan) if latency consistently exceeds 4 hours.
- Implement early termination: if the pipeline is at 5.5 hours, stop generation and publish whatever is ready.

**Status:** Runtime unknown at scale. The pipeline has never processed more than ~100 candidates in a single run. May need architectural changes (separate jobs, larger runner, phased enrichment) if the 6-hour limit is approached.

---

### Risk 6: Local Government Source Availability

**Likelihood:** High | **Impact:** Medium

Local government RSS feeds are notoriously unreliable or nonexistent. Many municipalities only publish meeting agendas as PDFs or unparseable web pages. The proposed 30+ local government feeds may yield very few usable stories.

Specific concerns:
- Only a handful of major cities (NYC, SF, LA, Chicago, DC, Boston, Seattle, Austin) have dedicated planning department RSS feeds. Most mid-size cities do not.
- Even when RSS feeds exist, they often contain meeting notices and calendar items rather than substantive policy/permitting stories.
- Municipal bond issuance announcements often appear on financial terminals (Bloomberg, Refinitiv) before appearing in public RSS feeds.
- The NewsAPI fallback for "[city] zoning" or "[city] development approval" searches may surface local news stories that lack institutional depth.

**Mitigation:**
- Prioritize the 10 municipalities with known RSS feeds. Accept lower article counts for this sector initially.
- Use NewsAPI queries as supplemental fallback for local government keywords.
- Develop custom scrapers for 2-3 highest-priority jurisdictions only (NYC Department of City Planning, SF Planning, LA City Planning). Do not attempt to scrape all 30+ municipalities.
- Set per-sector article target for local government to 10-15 (lower than the standard 30) until source quality improves.
- Consider this sector a "Phase 6" ongoing improvement item rather than a Phase 2 requirement.

**Status:** Most local government feeds marked [NEEDS VERIFICATION]. Actual coverage is unknown. This sector may produce 5-10 articles/day rather than the target 30. Accept this as a known limitation and do not over-invest in scraping infrastructure.

---

### Risk 7: Content Duplication Across Sectors

**Likelihood:** Medium | **Impact:** Medium

A single story can legitimately belong to multiple sectors. Example: "Blackstone acquires $2B data center portfolio" is both a private_equity story (Blackstone PE deal) AND a data_centers story (data center portfolio). Without multi-label handling, the system must choose one primary sector, and the other sector misses a significant story.

Specific concerns:
- Cross-sector stories (PE firm buys energy infrastructure, bank arranges data center financing, federal policy affects CRE) will create classification ambiguity.
- If the system assigns only one primary sector, the other sector's output is incomplete.
- If the system assigns multiple sectors, stories may appear in multiple feeds — acceptable but requires deduplication in the main insights.html "All Sectors" view.
- Entity-driven cross-sector overlap: Blackstone is both CRE and PE. Brookfield is CRE, PE, and Energy. Equinix is Data Centers and CRE (REIT).

**Mitigation:**
- Allow multi-label classification (up to 3 secondary sectors per item).
- Cross-post stories to multiple sector feeds when multi-labeled.
- In the main "All Sectors" view, deduplicate by content_hash. Show the story once with all relevant sector tags.
- Use entity relationships in watchlists.json to identify when a story with entity X that spans sectors A and B should be considered for both.
- Event clustering (editorial_intelligence.py) must handle cross-sector clusters.

**Status:** Multi-label classification is spec'd (allow_multi_label in sectors.json) but not implemented. Deduplication logic not yet built.

---

### Risk 8: LLM Prompt Drift

**Likelihood:** Medium | **Impact:** Medium

LLM behavior changes over time as models are updated by providers. Prompts that produce excellent articles today may produce degraded output after a model update. The narrative financial writing style is particularly sensitive to model version and system prompt changes.

Specific concerns:
- DeepSeek updates its models periodically. A model version change can alter writing style, length, structure, or factuality without warning.
- The OpenAI fallback uses different models (gpt-4o-mini) which have different writing characteristics than DeepSeek. Fallback articles may be stylistically inconsistent with DeepSeek articles.
- Prompt "overfitting" — prompts optimized for a specific model version may perform poorly when that model is updated.
- Without version tracking, it's impossible to correlate a quality drop with a model update.

**Mitigation:**
- Version all prompts in config/prompts.json with a version number and last-modified date.
- Store the model version used for each article (in Item.llm_model_used).
- Run periodic quality spot-checks (weekly, sampling 5 articles per sector).
- Maintain a "golden set" of 50 article examples across sectors for automated regression testing. After any prompt or model change, regenerate these articles and compare against the golden set using automated metrics (ROUGE, BERTScore, or simpler heuristics like word count distribution).
- If a model update degrades quality, have the ability to switch to a pinned model version (if provider supports it) or temporarily switch all generation to the fallback provider.

**Status:** Prompts recently rewritten (July 2026). No mechanism for prompt version tracking exists yet. The golden set approach is specified but not implemented. Model versioning exists only in run logs, not in a queryable format.

---

## Operational Risks

### Risk 9: Single Point of Failure

**Likelihood:** Medium | **Impact:** Critical

The entire pipeline runs in one GitHub Actions job. If any phase fails unhandled, the entire day's output is lost — all 210 articles across all 7 sectors. The checkpoint/resume system mitigates this but has not been tested at scale.

Specific concerns:
- A single unhandled exception in generation.py (e.g., an unexpected LLM response format for one of 210 articles) could crash the entire pipeline.
- The pipeline has no partial-publish capability. Either all sectors publish or none do.
- If the pipeline fails at hour 5 of a 5.5-hour run, there is insufficient time to diagnose, fix, and re-run within the same day.
- The checkpoint system writes state to disk but restoring from checkpoint has not been tested with 2000+ partial items.

**Mitigation:**
- Per-item exception handling: a single article generation failure should not crash the pipeline. Catch and log per-item errors, continue to the next item.
- Checkpoint after each phase (already built) — verify that checkpoint/resume works at scale.
- Consider splitting into separate workflow jobs (Phase 6): ingest + classify → score + rank → write + publish. Each job can fail and be retried independently.
- Implement a "partial publish" mode: if 5 of 7 sectors generate successfully, publish those 5. Mark the other 2 as "missed" for the day.
- Add a watchdog timer: if the pipeline has been running for 5 hours, stop generation and publish whatever is ready.

**Status:** Checkpoint/resume tested in shadow mode only (small scale). The pipeline has never failed mid-run at production scale, so the recovery path is untested in realistic conditions.

---

### Risk 10: Content Policy and Moderation Failures

**Likelihood:** Low | **Impact:** Critical

LLMs occasionally generate content that violates acceptable use policies, includes hallucinated facts, or produces output with unintended biases. The system generates 210 articles/day with minimal human review, increasing the risk that a problematic article is published.

Specific concerns:
- Hallucinated deal values, wrong entity names, or invented quotes in generated articles.
- The LLM may generate content that inadvertently discloses material non-public information if it was present in source material.
- Tone inconsistency: an article about a bankruptcy or layoffs may be written inappropriately upbeat tone.
- Sector-specific risks: PE articles may inadvertently reveal LP identities or fund performance that sources intended as background. Banking articles may misstate regulatory actions. Local government articles may unintentionally take sides in political disputes.

**Mitigation:**
- Every article must include visible source attribution (source URLs, date accessed).
- Articles with insufficient evidence (evidence_level: insufficient) must only be published as deal tape with minimal interpretive content.
- Flag for human review: any article containing keywords related to litigation, criminal activity, bankruptcy, executive departures, or allegations.
- Implement a post-generation factuality check: compare entity names in the generated article against entity names in the source dossier. Flag discrepancies.
- Hold all flagship articles for human review before publishing (admin dashboard approval workflow, Phase 5).
- Publish a disclaimer prominently on all articles: "Generated by Light Tower Group's automated intelligence engine from publicly available sources. Not investment advice."

**Status:** Basic legal risk detection exists in editorial_intelligence.py. Enhanced factuality checking and approval workflow not yet implemented.

---

## Business and Credibility Risks

### Risk 11: Editorial Credibility at Scale

**Likelihood:** Medium | **Impact:** Critical

Publishing 210 articles per day risks the perception (and reality) of automated content rather than curated intelligence. Readers may dismiss the output as "AI-generated spam" rather than institutional-grade briefings.

Specific concerns:
- Volume overwhelms quality perception. Even if 80% of articles are good, the 20% that are mediocre will be the ones readers remember.
- The "uncanny valley" of AI writing — articles that are factually correct but stylistically hollow. Readers can detect the absence of genuine analytical judgment.
- Lack of editorial voice consistency across sectors. A CRE article written in "narrative financial" voice next to a local government article in "analytical regulatory" voice may feel like different publications.
- Over-reliance on source material. The LLM synthesizes, it does not investigate. Articles lack original reporting. Sophisticated readers will notice.
- No mechanism for corrections or updates. If a story develops after publication, the existing article is frozen.

**Mitigation:**
- Tiered output with clear visual distinction: flagship analyses (with "Editor's Analysis" badge) are clearly differentiated from briefs ("Market Brief") and deal tape ("Deal Tape").
- Every article has visible source attribution and a "Generated by Light Tower Insights" tag.
- Publish a daily "Editor's Note" explaining the selection criteria and acknowledging the automated nature of the output.
- Never publish flagship articles with insufficient evidence. The evidence_level gate must be strict.
- Maintain a consistent tone within each sector, even if tones differ across sectors.
- Consider a "corrections and updates" section on the site. Manually update articles when significant developments occur.
- Set reader expectations clearly on the About page: "Automated intelligence briefings from 200+ institutional sources."

**Status:** Tier system designed but not tested at scale. The perception risk is hard to measure before real readers engage with the content. This risk materializes over weeks/months of operation, not days.

---

### Risk 12: Legal and Compliance Exposure

**Likelihood:** Low | **Impact:** Critical

Reporting on private equity transactions, distressed assets, ongoing litigation, regulatory enforcement actions, and individual executives creates legal exposure. The system must not publish unverified allegations, defamatory content, or material non-public information (MNPI).

Specific concerns:
- PE deal reporting: deals are often confidential until closing. Publishing deal terms before official announcement could violate confidentiality agreements or securities laws.
- Distressed asset reporting: reporting that a company is "near bankruptcy" before a public filing could be defamatory and market-moving.
- Regulatory enforcement: reporting on SEC/CFPB enforcement actions before they are public could violate securities laws.
- Individual executives: naming individuals in connection with investigations, lawsuits, or terminations creates defamation risk.
- The "republication" risk: even if the source material is public, the system is republishing it in a new context. The original source's errors become the system's errors.
- Attribution: if the system summarizes a paywalled article, is that copyright infringement? Fair use doctrine is untested for automated summarization at this scale.

**Mitigation:**
- Existing legal/allegation risk detection in editorial_intelligence.py: flag stories with litigation, criminal, bankruptcy, investigation, enforcement, or individual executive keywords.
- Enhanced fact verification for high-risk categories: require multiple corroborating sources before publishing.
- Human review flag for all flagged content. Do not auto-publish flagged articles.
- "Hold for review" for all flagship articles.
- All articles attribute sources prominently. Do not claim original reporting.
- Consult legal counsel before publishing articles about litigation, enforcement, or individual executives.
- Publish a Terms of Use and Disclaimer that limits liability and clarifies that content is aggregated from public sources.

**Status:** Basic legal risk detection exists. Enhanced verification not yet implemented. No legal review of the automated publishing model has been conducted. This risk should be addressed with legal counsel before full production cutover.

---

### Risk 13: Audience and Distribution Uncertainty

**Likelihood:** Medium | **Impact:** Medium

The target audience for sector-specific intelligence is assumed but not validated. The current CRE audience may not care about PE, data centers, or local government. There may be no audience for the expanded content.

Specific concerns:
- The current Insights page receives unknown traffic. No analytics integration exists to measure readership.
- No email distribution, newsletter, or subscriber system exists. Readers must visit the site proactively.
- 210 articles/day on a single page is overwhelming. Without filtering and personalization, readers will bounce.
- The "Light Tower Group" brand is associated with CRE capital markets. Expanding to 6 new sectors may dilute brand identity.
- There's no mechanism to know which sectors readers actually want. The 7-sector expansion is a supply-side decision.

**Mitigation:**
- Add basic analytics (Netlify Analytics or similar) before the Phase 5 cutover to measure readership.
- Implement sector filtering and personalization on insights.html (Phase 4).
- Consider a daily email digest per sector for subscribers (open issue #7).
- Start with CRE + PE (highest overlap) and expand gradually. Do not go to all 7 sectors simultaneously if audience data is lacking.
- Run a reader survey (if possible) to validate interest in non-CRE coverage.

**Status:** No analytics exist. Audience size and preferences are completely unknown. The expansion assumes demand exists for sector-specific institutional intelligence across all 7 sectors.

---

## Open Issues

The following questions cannot be resolved through technical implementation and require external input or investigation:

1. **Do PE Hub, Buyouts, PitchBook, etc. have accessible RSS feeds or are they paywalled?** The source registry (05-source-registry.md) lists these as proposed feeds, but their actual accessibility is unknown. Paywalled feeds may produce RSS summaries without sufficient content for article generation. This affects Phase 2. **Action required:** Manual verification of each proposed feed before Phase 2 begins.

2. **Can the NewsAPI free tier (500 requests/day) handle 2000+ daily candidates across all sectors?** The NewsAPI fallback is proposed for local government and general coverage. At 500 requests/day, if each request returns 20 articles, that's 10,000 potential candidates — more than enough. But the free tier may not allow the query specificity needed (geographic + keyword filters). **Action required:** Test NewsAPI queries for each sector to verify result quality and volume.

3. **Will DeepSeek rate limits accommodate 210 article generations + classification calls per day?** DeepSeek's public rate limits (as of July 2026) are not published. The expected volume is ~400-600 API calls/day (210 generation + ~200 classification/enrichment). DeepSeek may throttle or reject requests at this volume. **Action required:** Contact DeepSeek or test at increasing volumes to determine practical rate limits.

4. **Are there copyright or licensing restrictions on summarizing paywalled content?** Many institutional sources (PitchBook, Preqin, PE Hub, Buyouts) are paywalled. Summarizing their content in generated articles may violate terms of service or copyright. Fair use for automated summarization at commercial scale is legally untested. **Action required:** Legal review. Consider only using publicly accessible sources.

5. **Should the system attribute articles to "Light Tower Group" or "Ben Rohr"?** The current pipeline has an author field. The multi-sector engine generates 210 articles/day — attributing them all to an individual may raise credibility and legal concerns. **Action required:** Editorial decision on attribution. "Light Tower Group Insights" or "LTG Intelligence Engine" are alternatives.

6. **How should the Insights page handle 210 new articles appearing daily?** Infinite scroll, daily digest format, archive pagination, and auto-archive for articles older than N days are all open design questions. The current insights.html is designed for 0-5 articles. **Action required:** UI/UX design for high-volume content display.

7. **Should there be a daily email digest per sector for subscribers?** An email newsletter would significantly increase distribution and engagement. But it requires: email infrastructure (Mailchimp, ConvertKit, or custom), subscriber management, CAN-SPAM compliance, and additional pipeline complexity (generate HTML email versions). **Action required:** Business decision on whether to invest in email distribution.

8. **How will the system handle weekends and holidays?** The pipeline currently runs daily. On weekends and holidays, news volume is lower. The system may produce fewer articles, or it may produce lower-quality articles (thin evidence). Should the pipeline reduce targets on weekends? Should Monday editions aggregate weekend news? **Action required:** Operational policy decision.

9. **What happens when a major news event (e.g., FOMC emergency meeting, Blackstone megadeal) generates 500+ valid candidates in one sector?** The per-sector cap (maximum_articles_per_sector: 45) will reject valid stories. The system needs a "breaking news" mode that temporarily raises caps. **Action required:** Design breaking news override mechanism.

10. **How should the system handle corrections and retractions?** If a source article contains an error that the system republishes, there's no mechanism to issue a correction. If a reader reports an error, there's no process for verification and correction. **Action required:** Define corrections policy and technical implementation.

11. **What are the SEO implications of 210 AI-generated articles per day?** Google's policies on AI-generated content are evolving. Publishing high volumes of automated content without significant human editorial oversight could be classified as "spam" and penalized in search rankings. **Action required:** SEO review. Consider noindex for deal tape articles.

12. **Should the system be open-sourced?** The codebase is currently in a private repository. Open-sourcing the engine could attract contributors, improve transparency, and build credibility. But it also exposes the competitive moat. **Action required:** Business decision on open-source strategy.

---

## Risk Matrix Summary

| Risk # | Risk | Likelihood | Impact | Status |
|--------|------|------------|--------|--------|
| 1 | LLM classification accuracy for new sectors | High | High | Needs testing |
| 2 | Article quality for non-CRE sectors | High | Critical | Prompts not written |
| 3 | Source reliability at scale | High | Medium | 60% unverified |
| 4 | Scale and cost at 210 articles/day | Medium | Medium | Theoretical estimates |
| 5 | GitHub Actions 6-hour timeout | Low | Critical | Untested at scale |
| 6 | Local government source availability | High | Medium | Most unverified |
| 7 | Content duplication across sectors | Medium | Medium | Not implemented |
| 8 | LLM prompt drift | Medium | Medium | No version tracking |
| 9 | Single point of failure | Medium | Critical | Checkpoint untested |
| 10 | Content policy/moderation failures | Low | Critical | Needs enhancement |
| 11 | Editorial credibility at scale | Medium | Critical | Long-term risk |
| 12 | Legal and compliance exposure | Low | Critical | Needs legal review |
| 13 | Audience and distribution uncertainty | Medium | Medium | No analytics |

---

*Last updated: July 30, 2026. This document should be reviewed at each phase gate (see 08-implementation-plan.md) and updated as risks are mitigated or new risks are discovered.*
