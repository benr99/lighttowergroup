# Light Tower Insights — 10X Upgrade Plan

## Target end-state

The system stops being a daily article factory and becomes an intelligence function that: monitors data sources for signals that map to client situations, publishes a scarce public edition only when evidence is deep and claims are original, distributes directly to subscribers who have told the system what they care about, learns from every read/share/conversation to sharpen its editorial judgment, and feeds Ben a weekly brief of actionable client signals — refinancing windows, distress events, capital events — he can act on in conversation. Public articles demonstrate capability. Private signals drive revenue.

---

## PHASE 0 — AUDIT & MEASURE (Week 1, no code changes)

Goal: Know what's actually happening before touching anything.

### 0.1 Instrument and measure the live pipeline
- Add a `cost` field to every LLM API call in `daily_news_agent.py` and `editorial_scoring.py`. Log tokens-in, tokens-out, estimated cost using DeepSeek's published pricing. Write to `data/editorial_runs/{date}-costs.json`.
- Run the pipeline in `shadow` mode (score only, no publish) for 5 consecutive days. Record: number of candidates gathered, number surviving triage, number clustered, deterministic scores, LLM scores, final blend scores, which candidates would have been selected, estimated total API cost.
- Output: a `data/pipeline-baseline.json` with per-day stats. This is your before picture.

### 0.2 Run the offline scoring evaluation
- Take 100 historically scored candidates from `data/editorial_runs/` that resulted in published articles.
- For each, record: deterministic-only score, LLM-only score, 40/60 blend score, article format, whether the article has a LinkedIn essay package, and any available engagement signal (even anecdotal — did Ben get a call about it?).
- Compute correlation matrix: deterministic vs. LLM scores. If correlation > 0.75, the LLM scoring pass is redundant. If < 0.50, the LLM is adding signal.
- Output: a one-page recommendation on whether to keep, modify, or kill the LLM scoring pass.

### 0.3 Catalog the archive
- Run `content_governance.py`'s `near_duplicate_matches()` against all 331 articles with a threshold of 0.72.
- List all article pairs that share ≥ 2 fact anchors within 5 days (same event, different article).
- Identify articles where the narrative ledger's central claim cannot be traced to a source URL whose trafilatura fetch is still available.
- Output: `data/archive-audit.json` — duplicates, thin-evidence articles, claims without sources. This is your cleanup backlog.

---

## PHASE 1 — KILL WHAT DOESN'T WORK (Weeks 1-2)

Goal: Remove waste. Every deleted component is API credits saved and complexity removed.

### 1.1 Delete the bucketed volume scorer
- Remove `scripts/bucketed_editorial.py` and its import in `daily_news_agent.py`.
- Replace the bucketed routing decision in `daily_news_agent.py` with a 5-line topic classifier:

```python
def route_story(event):
    topics = set(event.get("candidate", {}).get("topics", []))
    if topics & {"distress", "cmbs", "bank_credit", "fed_rates"}:
        return "cre_capital_markets"
    if topics & {"major_sale", "development_finance", "capital_expenditure"}:
        return "cre_transactions"
    if topics & {"private_credit", "private_equity"}:
        return "private_capital"
    if topics & {"policy", "government_action"}:
        return "policy_rates"
    return "general"
```

- This replaces ~200 lines of scoring code and 1 LLM call per candidate with 10 lines and zero API calls.

### 1.2 Collapse the 8-role editorial room to 3 LLM calls
- Replace the editorial room simulation in `daily_news_agent.py` (angle editor, skeptic, writer, copy editor, EIC) with three structured calls:

**Call 1 — Analysis (replaces angle editor + skeptic):**
```
System: You are an analytical editor. Given a research dossier, produce:
1. The strongest defensible thesis (1 paragraph)
2. The strongest counterargument (1 paragraph)
3. Missing evidence — what would change the thesis if we had it (3 bullet points)
Return as JSON: {thesis, counterargument, missing_evidence}
```

**Call 2 — Write (replaces writer):**
```
System: [Existing SYSTEM_PROMPT_ENHANCED]
Given: dossier + analysis_result + voice_mode + franchise + headline_shape
Produce: full article JSON
```

**Call 3 — Revise (replaces copy editor) ONLY IF quality gates fail:**
```
System: The following quality issues were found: [list from content_governance.py].
Revise the article to fix them. Do not change facts or sources.
```

- This cuts ~5 LLM calls per article to 2-3. The `content_governance.py` deterministic gates remain as the primary quality layer.

### 1.3 Replace hash-based voice selection with context mapping
- In `scripts/editorial_voice.py`, replace `select_editorial_brief()`:

```python
def select_editorial_brief(event):
    text = _event_full_text(event)
    topics = _event_topics(event)
    culture_dims = _culture_dimensions(text)

    if any(re.search(p, text) for p in _CONFLICT_PATTERNS):
        return VOICE_MODES["basis_autopsy"]
    if topics & {"major_sale", "capital_placement"} and _event_feature(event, "has_big_number"):
        return VOICE_MODES["underwriting_margin"]
    if topics & {"policy", "government_action"}:
        return VOICE_MODES["consensus_cross_exam"]
    if len(culture_dims) >= 3:
        return VOICE_MODES["capital_after_dark"]
    if _event_feature(event, "has_material_transaction") and len(_event_entity_values(event, "companies")) >= 3:
        return VOICE_MODES["counterparty_map"]
    if any(term in text for term in ("maturity", "refinance", "extension", "expiring")):
        return VOICE_MODES["time_as_cost"]
    return VOICE_MODES["operators_field_note"]
```

- Same approach for `select_headline_shape()` — map headline shapes to story characteristics, not hashes.

### 1.4 Add the signal-first triage gate
- Before running LLM scoring or any writing, after deterministic scoring (Phase 4A), count candidates with `must_read_score >= 40`.
- If count == 0: write `editions/{date}.json` with `status: "skipped"`, log reason, exit. Do not make any LLM calls.
- If count >= 1: run the LLM scoring phase for those candidates only (not the full pool).
- Log skip decisions to `.editorial-state/skip-log.json` for trend analysis.

---

## PHASE 2 — FIX THE FEEDBACK LOOP (Weeks 2-3)

Goal: The system learns from every reader interaction.

### 2.1 Wire the existing editorial-feedback Netlify function to audience signals
- Modify `netlify/functions/editorial-feedback.js`:
  - On every valid poll response, prompt submission, or save action, append to `.editorial-state/audience-signals-live.json`.
  - Record structure: `{timestamp, signal_type: "poll"|"prompt"|"save", story_slug, topic, option_selected, weight_delta: +1|-1}`.
  - If `comment` contains keywords matching a topic or culture dimension, add a +1 weight.
- Add a `--consume-signals` flag to `daily_news_agent.py` that reads this file, aggregates the last 30 days of signals, updates `audience-signals.json` weights, and truncates the live file.

### 2.2 Add passive read tracking
- Create `netlify/functions/track-read.js`:
  - Accepts POST `{slug, action: "view"|"scroll_50"|"scroll_100"|"share"|"copy_link"}`.
  - Writes to `.editorial-state/read-events.jsonl` (append-only JSON lines, no parsing overhead).
  - Rate limit: 60/minute. No auth required (it's anonymous read data).
- Add a 15-line inline script to every article template that fires `track-read` on: page load, 50% scroll, 100% scroll, share button click.
- This gives you: which articles are actually read vs. clicked-and-bounced, which get shared, average read depth by category.

### 2.3 Add LinkedIn engagement ingestion (weekly)
- Create `scripts/linkedin_engagement_scraper.py`:
  - Reads `linkedin_essay_queue.json` for essay slugs posted in the last 14 days.
  - For each, uses the LinkedIn API (or a headless browser if API access is limited) to pull impressions, reactions, comments, reposts.
  - Writes to `.editorial-state/linkedin-engagement.json`.
  - Aggregates by topic, category, and voice mode.
- Run this as a separate weekly GitHub Actions workflow (Sunday evening).
- Feed results into `audience-signals.json` with topic weights proportional to engagement.

### 2.4 Create the weekly retrospective report
- Create `scripts/weekly_retrospective.py`:
  - Reads the week's edition runs, audience signals, read events, and LinkedIn engagement.
  - Computes: publish rate, avg scores, top 3 topics by engagement, bottom 3 topics, cost per article, cost per engaged read.
  - Generates a markdown report at `data/weekly-reports/{date}.md`.
  - Sends via Resend email to Ben (the `mandate-submit.js` email infrastructure already exists).
- Schedule: Sunday 8 AM NY time, GitHub Actions.

---

## PHASE 3 — FIX THE EVIDENCE (Weeks 2-4)

Goal: No article publishes with an unverifiable central claim.

### 3.1 Add deterministic fact extraction from sources
- Create `scripts/fact_extractor.py`:
  - For each source URL in the dossier, if trafilatura full-text is available, extract:
    - Dollar amounts (regex: `\$\s*[\d,.]+(?:\s*(?:million|billion|trillion|mm|bn|m|b))?`)
    - Percentages and basis points (regex: `[\d.]+%\s*|[\d,]+\s*bps`)
    - Company/organization names (NER via simple capitalized-phrase heuristics + match against known institution list)
    - Property addresses (regex from `_street_addresses()` in `editorial_intelligence.py`)
    - Dates (ISO, "Month DD, YYYY", "Q1/Q2/Q3/Q4 YYYY")
  - Store as structured `{source_url: {amounts: [], percentages: [], companies: [], addresses: [], dates: []}}`.

### 3.2 Add claim-to-source tracing
- After the LLM generates an article, extract the same fact types from the generated body_html.
- Cross-reference: for every dollar amount in the article, is there a matching dollar amount in at least one source? For every company name, is it in a source?
- Flag mismatches. Store in `article["fact_audit"]`.
- If the central claim's dollar amount or company name cannot be traced to any source with source_tier ≤ 2: hold for review, do not auto-publish.
- This is NOT another LLM call. It's regex extraction + set comparison. Zero API cost.

### 3.3 Label inferences vs. reported facts
- Add to the narrative ledger schema: `claim_type: "reported_fact" | "bounded_inference" | "editorial_judgment"`.
- The LLM must label every claim in the ledger with its type.
- The quality gate checks: at least one `reported_fact` must exist. `editorial_judgment` claims without a supporting `reported_fact` are flagged.
- This forces the LLM to distinguish "Cerberus paid $1.3B" (reported fact) from "this signals bank capital costs are the real constraint" (bounded inference) from "the market has decided regional banks can't hold this paper" (editorial judgment — requires the strongest sourcing).

### 3.4 Build and populate the discovery watchlist
- Create `.editorial-state/discovery-watchlist.json`:

```json
{
  "newsapi_queries": [
    "commercial real estate loan sale",
    "CMBS delinquency",
    "multifamily refinancing",
    "office distress",
    "industrial cap rate",
    "data center power demand real estate",
    "stadium subsidy real estate",
    "climate insurance commercial property",
    "AI infrastructure data center",
    "regional bank CRE exposure"
  ],
  "google_alerts": [],
  "structured_sources": {
    "nyc_dob_permits": "https://a810-bisweb.nyc.gov/bisweb/...",
    "nyc_acris": "https://a836-acris.nyc.gov/...",
    "sec_edgar": "https://www.sec.gov/cgi-bin/browse-edgar?..."
  }
}
```

- Add a Phase 1.5 to the pipeline: after RSS feed gathering, run the watchlist queries. Merge results with RSS feed items before triage.
- Start with NewsAPI queries only (the infrastructure already exists). Add structured source scraping in Phase 5.

---

## PHASE 4 — REBUILD THE READER EXPERIENCE (Weeks 3-5)

Goal: The frontend stops being a static grid and becomes an intelligent delivery surface.

### 4.1 Add "Today's Edition" section to insights.html
- At page load, fetch `/latest-edition.json` in addition to `/insights.json`.
- If `latest-edition.json` has a flagship or briefs from today: render a distinct "Today's Edition" section above the filterable archive grid.
  - Flagship gets a hero-style card (full width, larger, labeled "Flagship Analysis").
  - Briefs get side-by-side cards below, labeled "Intelligence Brief."
  - Deal tape renders as a compact list: "Also in today's edition: [item one-liners]."
  - Reader poll from edition renders as an interactive widget.
- If no edition today: show "No edition today. Here's what you might have missed:" with the most recent edition's articles.

### 4.2 Add format badges and signals to archive cards
- Each card in the filterable grid gets a format badge: "Flagship," "Brief," "Building Profile," "Deal Tape."
- Badges have distinct visual treatments (color, border, icon).
- Add sort options: "Newest" (default), "Most-read this month" (requires read tracking from Phase 2.2), "Flagship Analyses only."
- The featured card (first position) is no longer always the most recent — it's the highest-scored article from the last 7 days.

### 4.3 Add newsletter signup to insights.html
- Add a one-field email input + "Get the Daily Capital Note" button to the insights hero section.
- On submit, POST to `/api/newsletter-subscribe` (the existing Netlify function).
- Store subscription in Resend contacts (already implemented).
- On successful subscription, show "You'll receive the next edition." with a link to the latest edition.

### 4.4 Add article recommendations to individual article pages
- On each article page (`/insights/{slug}.html`), at the bottom, render 3 related articles.
- Related = same category OR shared tags OR similar topics from the narrative ledger.
- This keeps readers on the site and feeds read-tracking data.
- Implementation: add a small JSON file per article (`/insights/{slug}_related.json`) generated at publish time, or compute client-side from `insights.json` tag overlap.

### 4.5 Separate building profiles from editorial content
- `buildings.html` becomes a proper searchable database, not an insights grid clone.
- Features: text search (address, neighborhood, lender), borough filter, loan maturity date range filter, sort by maturity date (default), sort by address.
- Building profile cards show: address, neighborhood, key numbers, loan maturity date (highlighted if within 6 months), link to full profile.
- Building profiles are excluded from the main `insights.html` grid (they're reference data, not editorial).
- Category filter "Built World" in insights.html shows only Market Analysis articles, not Architecture & Capital Markets profiles.

### 4.6 Trigger the daily edition email
- Add a step to `daily-insights-agent.yml` (or a separate workflow triggered on edition publication):
  - If edition status is "ready" and has articles: call Resend API to send the edition to all newsletter subscribers.
  - Email template: edition date, flagship title + excerpt + link, briefs titles + excerpts + links, deal tape as bullet list, reader poll.
  - Use the existing Resend integration from `newsletter-subscribe.js`.
- This closes the loop: produce → notify → read → engage.

---

## PHASE 5 — ADD THE ASSIGNMENT DESK (Week 4-5)

Goal: The system becomes proactive, not just reactive.

### 5.1 Add the weekly assignment run
- Create `scripts/weekly_assignment_desk.py`:
  - Runs Sunday 6 AM NY time (separate GitHub Actions workflow).
  - Reads the past week's deal tape entries and edition summaries.
  - Identifies patterns across multiple events: "3 regional banks sold loan books," "2 data center deals in Virginia," "4 office distress signals in SF."
  - Generates 3-5 investigation prompts using a single LLM call:
    ```
    System: You identify patterns across CRE capital markets events.
    Given: Last week's deal tape and edition summaries.
    Produce: 3-5 investigation prompts. Each prompt should identify a pattern,
    a specific question to investigate, and potential data sources.
    Return as JSON: [{pattern, question, potential_sources}]
    ```
  - For each prompt, runs targeted NewsAPI searches.
  - If evidence found: adds to a "commissioned" queue for Monday's edition with elevated priority.
  - If no evidence: stores the prompt for future runs (it may become relevant later).
  - Writes output to `.editorial-state/assignment-queue.json`.

### 5.2 Add structured public data scraping
- Create `scripts/structured_sources.py`:
  - **NYC DOB permits:** Scrape new building permit filings. Extract: address, owner, job type, estimated cost. Flag any > $10M estimated cost.
  - **SEC EDGAR:** RSS feed already exists but is underused. Add keyword filtering for tracked REITs, lenders, and "real estate" + "loan" or "mortgage."
  - **Federal Reserve:** RSS feed for stress test results, financial stability reports. Extract CRE exposure figures.
- These produce candidate stories that do not appear in any CRE publisher feed — original intelligence.
- Start with one source (SEC EDGAR — the RSS feed is already in the configuration). Add others incrementally.

---

## PHASE 6 — ATTRIBUTION & BUSINESS VALUE (Week 5-6)

Goal: Close the loop between published content and business outcomes.

### 6.1 Add lead source attribution
- Modify `netlify/functions/chat.js` and `netlify/functions/mandate-submit.js`:
  - Accept an optional `ref` parameter (article slug or page path).
  - Include `ref` in the Resend email to Ben.
- Modify the chat widget (`chat-widget.js`):
  - Capture `window.location.pathname` when chat opens.
  - Send as `ref` parameter with the conversation.
- Add a `?ref={slug}` parameter to the "Request a Deal Review" CTA button on every article page.
- Within 90 days: you know which articles drive qualified conversations.

### 6.2 Add per-article cost tracking
- In `daily_news_agent.py`, after each LLM call: record `{model, prompt_tokens, completion_tokens, estimated_cost_usd}`.
- At the end of each edition run: sum costs, write to edition JSON as `pipeline_cost_usd`.
- Track cumulative in `data/pipeline-costs.jsonl`.

### 6.3 Build the client signal digest
- Create `scripts/client_signal_digest.py`:
  - Runs Monday/Wednesday/Friday at 7 AM.
  - Monitors the same data sources but filters for signals relevant to *known client situations* (configured in `data/client-watchlist.json`):
    - "Brooklyn multifamily refinancing window opening"
    - "Regional bank CRE portfolio sale in [market]"
    - "Distress event in [asset class] in [market]"
    - "Policy change affecting [financing type]"
  - Produces a private markdown digest: one signal per line, with source, date, and a one-line implication.
  - Emails to Ben via Resend.
  - This is NOT published publicly. It's the bridge between the intelligence pipeline and Ben's client conversations.

---

## PHASE 7 — RESILIENCE & MONITORING (Week 6-7)

Goal: The pipeline doesn't break silently.

### 7.1 Add model provider fallback
- Create `scripts/model_router.py`:
  - Primary: DeepSeek (`deepseek-chat`).
  - Fallback: OpenAI (`gpt-4o-mini` for scoring, `gpt-4o` for writing) if `OPENAI_API_KEY` is configured.
  - Health check: before each pipeline run, call the primary model with a minimal prompt. If it fails (timeout, rate limit, auth error), switch to fallback for the entire run.
  - Log provider switches to `.editorial-state/provider-log.jsonl`.

### 7.2 Add per-phase timeouts and checkpointing
- In `daily_news_agent.py`, wrap each phase:
```python
PHASE_TIMEOUTS = {
    "gather": 120,   # seconds
    "triage": 60,
    "cluster": 30,
    "score_deterministic": 30,
    "score_llm": 120,
    "dossier": 60,
    "write": 180,
    "governance": 30,
    "publish": 60,
}
```
- After each phase, write `.editorial-state/checkpoint-{phase}.json` with phase output.
- If run fails: next run detects existing checkpoints and resumes from the last completed phase.
- If any phase exceeds its timeout: kill it, log the failure, and either skip to next phase or abort based on `PHASE_CRITICALITY` config.

### 7.3 Add archive rebuild capability
- Create `scripts/rebuild_articles.py`:
  - Reads all 331 entries from `insights.json`.
  - For each, reads the existing HTML file, extracts the article body.
  - Wraps it in the current site template (header, footer, navigation, styles, scripts).
  - Regenerates all 331 pages with current chrome.
- This ensures old articles don't rot when the site design changes.
- Run once to bring all articles to current template. Run again whenever the template changes.

### 7.4 Add pipeline health dashboard
- Create `scripts/health_report.py`:
  - Reads: source health log, skip log, provider log, cost log.
  - Produces a single `HEALTH.md` in the repo root with:
    - Feeds: healthy / degraded / quarantined counts.
    - Pipeline: last 7 days runs, success rate, avg candidates, avg articles.
    - Costs: last 30 days total, per-article average.
    - Model: primary uptime, fallback activations.
- Run after every pipeline execution. Commit to repo.
- This gives a one-glance view of whether the system is working.

---

## PHASE 8 — A/B TESTING & OPTIMIZATION (Ongoing, starting Week 4)

Goal: The system improves continuously, not in big-bang releases.

### 8.1 Article variant testing
- Add optional `variant` fields to the article generation prompt:
  - `headline_variant`: "control" (existing headline shape) or "question" (rephrase as a genuine question).
  - `cta_variant`: "control" (standard CTA) or "inline" (CTA in the middle of the article).
- Randomly assign 15% of articles to variant conditions.
- Track read depth, share rate, and lead attribution by variant.
- After 40 articles per variant: compute statistical significance. Apply winner to all future articles.

### 8.2 Scoring recalibration
- Monthly: run the offline scoring evaluation (Phase 0.2) with new data.
- If LLM scoring correlation with reader engagement drops below 0.5: recalibrate the scoring prompt.
- If deterministic scoring correlation is consistently higher: reduce LLM scoring weight or eliminate it.
- Document the decision and the data in `data/scoring-evaluations/`.

---

## IMPLEMENTATION ORDER

```
Week 1:  Phase 0 (audit, measure, baseline) + Phase 1.1 (delete bucketed scorer)
Week 2:  Phase 1.2-1.4 (collapse editorial room, fix voice selection, signal gate)
         Phase 2.1-2.2 (wire feedback, add read tracking)
Week 3:  Phase 2.3-2.4 (LinkedIn engagement, weekly retrospective)
         Phase 3.1-3.2 (fact extraction, claim-to-source tracing)
         Phase 4.1-4.2 (edition section, format badges)
Week 4:  Phase 3.3-3.4 (inference labeling, watchlist)
         Phase 4.3-4.5 (newsletter signup, recommendations, separate buildings page)
         Phase 5.1 (weekly assignment desk)
Week 5:  Phase 4.6 (edition email)
         Phase 5.2 (structured data scraping — SEC EDGAR first)
         Phase 6.1-6.2 (lead attribution, cost tracking)
Week 6:  Phase 6.3 (client signal digest)
         Phase 7.1-7.2 (model fallback, checkpointing)
Week 7:  Phase 7.3-7.4 (archive rebuild, health dashboard)
Ongoing: Phase 8 (A/B testing, scoring recalibration — monthly cadence)
```

---

## DO NOT DO (Anti-goals)

- Do not add another LLM call for anything that can be done with regex, set comparison, or a database lookup.
- Do not add "AI features" the reader didn't ask for (no chatbot on article pages unless it drives qualified leads — the existing chat widget stays but gets attribution tracking).
- Do not increase the publishing cadence. If the system publishes 2 articles a week after these changes, that's success — provided they're fact-verified, voice-matched, and driving engagement.
- Do not build a CMS. The system works from JSON manifests and static HTML. Keep it that way. The rebuild script (Phase 7.3) handles template changes.
- Do not add real-time anything. The pipeline runs on cron. The site is static. Latency is not a problem this system has.
- Do not touch the `enhanced_prompts.py` system prompt or narrative finance framework until Phase 8 data shows it's underperforming. The prompt architecture is good. The problems are in the pipeline around it.
