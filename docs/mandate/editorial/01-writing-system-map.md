# 01 — Writing System Map: Complete Current Workflow

**Purpose:** Map every stage, data flow, and LLM interaction in the Light Tower Group article generation pipeline. This document serves as the authoritative reference for understanding how articles are currently produced before any architectural changes are proposed.

**Date:** July 2026  
**Scope:** Production pipeline (`daily_news_agent.py`), edition mode, legacy mode, self-repair, quality gates

---

## 1. System Overview Diagram

```
                                             LEGACY MODE (no dossier)
                                             ─────────────────────
SOURCE STORIES                                    │
  │                                                │
  ▼                                                │
┌─────────────────┐                                │
│  PHASE 1: GATHER │                               │
│  RSS + NewsAPI   │                               │
│  200+ stories/day│                               │
└────────┬────────┘                                │
         │                                         │
         ▼                                         │
┌─────────────────┐                                │
│  PHASE 2: TRIAGE │                               │
│  CRE relevance   │                               │
│  deduplication   │                               │
│  20-60 candidates│                               │
└────────┬────────┘                                │
         │                                         │
         ▼                                         │
┌─────────────────┐                                │
│  PHASE 3: SCORE  │  ◄── 1 LLM call               │
│  DeepSeek ranks  │      (score_stories)           │
│  0-100 per story │                                │
└────────┬────────┘                                │
         │                                         │
    ┌────┴────┐                                    │
    ▼         ▼                                    │
EDITION    LEGACY                                   │
 MODE       MODE                                    │
    │         │                                     │
    ▼         │                                     │
┌───────────────────────┐                           │
│ PHASE 3.5: ENRICH     │                           │
│ Full text fetch       │                           │
│ (trafilatura)         │                           │
│ Story normalization   │                           │
│ Entity extraction     │                           │
└──────────┬────────────┘                           │
           │                                        │
           ▼                                        │
┌──────────────────────────────────────┐            │
│ EDITION SELECTION                    │            │
│ (editorial_intelligence.py)          │            │
│ Cluster stories → events             │            │
│ Score must-read value                │            │
│ Assign franchises                    │            │
│ Assign provisional formats           │            │
└──────────┬───────────────────────────┘            │
           │                                        │
           ▼                                        │
┌──────────────────────────────────────┐            │
│ RESEARCH DOSSIER                     │            │
│ (research_dossier.py)                │            │
│ Multi-source evidence ledger          │            │
│ Facts, quotes, counterquestions       │            │
│ Evidence classification               │            │
│ (deep/adequate/thin/insufficient)     │            │
└──────────┬───────────────────────────┘            │
           │                                        │
           ▼                                        │
┌──────────────────────────────────────┐            │
│ EDITORIAL ROOM — 1 LLM CALL          │            │
│ (editorial_room.py)                  │            │
│ MODEL: deepseek-chat                 │            │
│ TEMP: 0.15, max_tokens: 1800         │            │
│                                      │            │
│ Angle editor + Skeptic +             │            │
│ Assigning editor                     │            │
│ ── ALL IN ONE PROMPT ──             │            │
│                                      │            │
│ Outputs:                             │            │
│  - decision (write/shorten/kill...)  │            │
│  - final_format                       │            │
│  - angle/why_now/favored_thesis      │            │
│  - skeptic_objections                │            │
│  - human_stakes                      │            │
│  - concrete_detail                   │            │
│  - reporting_gaps                    │            │
└──────────┬───────────────────────────┘            │
           │                                        │
           ▼                                        ▼
┌──────────────────────────────────────────────────────┐
│              PROMPT ASSEMBLY                          │
│                                                       │
│  System prompt:                                       │
│    EDITION: EDITION_SYSTEM_PROMPT (33 lines)          │
│             + VOICE_SYSTEM_ADDENDUM                   │
│    LEGACY:  SYSTEM_PROMPT_ENHANCED (~200 lines)       │
│             + VOICE_SYSTEM_ADDENDUM                   │
│             + NARRATIVE_FINANCE_ADDENDUM              │
│                                                       │
│  User prompt:                                         │
│    EDITION: EDITION_USER_PROMPT_TEMPLATE               │
│             {format, franchise, room_plan,             │
│              dossier, voice_brief, headline_shape}     │
│    LEGACY:  USER_PROMPT_TEMPLATE                       │
│             {title, source, url, summary,              │
│              full_text, voice_brief, headline_shape}   │
│                                                       │
│  Voice mode (editorial_voice.py):                     │
│    8 modes, context-selected, attached as JSON         │
│                                                       │
│  Headline shape (editorial_voice.py):                 │
│    9 shapes, context-selected, attached as JSON        │
│                                                       │
│  Model parameters:                                     │
│    MODEL: deepseek-chat                               │
│    TEMP: 0.2                                           │
│    MAX_TOKENS: 3000-5200 (format-dependent)            │
│    TIMEOUT: 120s                                       │
└──────────┬───────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│           ARTICLE GENERATION — 1 LLM CALL            │
│                                                       │
│  THE CRITICAL ARCHITECTURAL FACT:                     │
│  ─────────────────────────────────                   │
│  Reasoning + Writing happen in ONE API call.          │
│  The model receives:                                  │
│   - System prompt (~2,000 words)                      │
│   - User prompt (dossier, room plan, voice, shape)    │
│  And must simultaneously:                             │
│   - Analyze the financial meaning                     │
│   - Build the narrative ledger                        │
│   - Structure the argument                            │
│   - Execute the assigned voice                        │
│   - Hit the assigned word count                       │
│   - Follow headline shape                             │
│   - Produce valid JSON                                │
│  ── ALL IN ONE FORWARD PASS ──                       │
│                                                       │
│  No separate reasoning model.                         │
│  No chain-of-thought.                                 │
│  No multi-step analytical decomposition.              │
└──────────┬───────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│           SELF-REPAIR LOOP (max 2 iterations)        │
│                                                       │
│  For each iteration:                                  │
│   1. Run all quality gates:                           │
│      - independent_quality_issues (content_governance)│
│      - narrative_finance_issues (editorial_voice)     │
│      - title_quality_issues (editorial_voice)         │
│      - excellence_issues (editorial_room)             │
│                                                       │
│   2. If findings exist:                               │
│      - Send revision prompt to LLM                    │
│      - TEMP: 0.15, MAX_TOKENS: 5200                   │
│      - Model gets: system prompt + original user      │
│        prompt + revision prompt (with findings +      │
│        current article JSON)                          │
│      - Model must produce corrected JSON              │
│                                                       │
│   3. If ALL gates pass → exit loop                    │
│      If 2 iterations exhausted with issues →           │
│      raise ValueError, article discarded              │
└──────────┬───────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│           QUALITY GATES (final pass)                  │
│                                                       │
│  Content governance (content_governance.py):          │
│    - Word count floor/ceiling                         │
│    - Source URLs present and valid                    │
│    - No fixture sources (example.com)                 │
│    - No generic boilerplate                           │
│    - No prompt injection                              │
│    - Duplicate paragraph detection                    │
│    - AI language tells (editorial_quality_issues)     │
│    - Mojibake detection                               │
│    - Fact audit (claim-to-source verification)        │
│    - Semantic claim audit                             │
│                                                       │
│  Narrative finance (editorial_voice.py):              │
│    - Anchor, tension, cast, mechanism, claim,         │
│      reader_consequence all present                   │
│    - Scene provenance verified                        │
│                                                       │
│  Title quality (editorial_voice.py):                 │
│    - Overused "Shows"/"Tests" in recent titles        │
│    - Overused ", Not X" contrast tail                 │
│                                                       │
│  Excellence (editorial_room.py):                     │
│    - Format-specific word counts                      │
│    - Independent source minimums                      │
│    - Claim-evidence URL verification                  │
│    - Memorable line in article                        │
│    - Counterargument present                          │
│    - Redevelopment not mislabeled as supply           │
│    - No house abstraction repetition                  │
└──────────┬───────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│              PUBLICATION                              │
│                                                       │
│  - Sanitize HTML                                      │
│  - Generate social image                              │
│  - Write .html file to /insights/                     │
│  - Update insights.json                               │
│  - Update feed.xml                                    │
│  - Update sitemap.xml                                 │
│  - Generate LinkedIn essay (if essay queue enabled)   │
│  - Save editorial run record                          │
│  - Build edition document                             │
│  - Save publication decision                          │
│  - Update event memory                                │
└──────────────────────────────────────────────────────┘
```

---

## 2. Detailed Stage-by-Stage Data Flow

### 2.1 PHASE 1: GATHER

**Module:** `daily_news_agent.py` — `fetch_rss_stories()` (line 211), `fetch_newsapi_stories()` (line 295)

**Inputs:**
- `ALL_RSS_FEEDS` = `RSS_FEEDS` (NYC/national CRE feeds) + `FEDERAL_RSS_FEEDS` (FOMC, FDIC, OCC, Treasury, etc.)
- `NEWSAPI_QUERIES` — keyword-based queries to NewsAPI

**Processing:**
- `feedparser` parses all RSS feeds with 36-hour recency window
- Source health tracking via `SourceHealthLedger` — quarantined feeds are skipped
- NewsAPI supplements with keyword searches (up to 40 queries)
- Shared outage detection: if ≥50% feeds fail, quarantines are released

**Output:** 200+ raw story dicts, each with `title`, `url`, `summary`, `source`, `published`

### 2.2 PHASE 2: TRIAGE

**Module:** `daily_news_agent.py` — `triage()` (line 385), `triage_daily_top_news()` (line 499)

**Processing:**
1. CRE relevance filter: keywords in `CRE_KEYWORDS`, minus `EXCLUDE_KEYWORDS`
2. Recency filter: published within 36 hours
3. Deduplication: `SequenceMatcher` ratio > 0.72 between titles
4. Government intake path: separate `_is_federal_or_msa_government_relevant()` to admit federal/MSA government stories with CRE/finance transmission paths
5. Transaction intake path: `_is_material_cre_transaction()` to admit $10M+ or institutional CRE transactions

**Output:** 20-60 unique, relevant candidates

### 2.3 PHASE 3: SCORE

**Module:** `daily_news_agent.py` — `score_stories()` (line 545)

**LLM Call 1:** DeepSeek (`deepseek-chat`), temperature 0.2, max_tokens 3500

**Prompt:** Senior editor ranks each story 0-100 on:
- Capital markets impact: 30 pts
- NYC/Brooklyn/Manhattan relevance: 25 pts
- Deal size or policy scale: 20 pts
- Originality: 15 pts
- Timeliness: 10 pts

**Output:** Stories sorted by descending score

### 2.4 EDITION MODE — PHASE 3.5: ENRICH

**Module:** `daily_news_agent.py` — `pre_enrich_selection_candidates()` (line 640), `enrich_story()` (line 698)

**Processing:**
- Full text fetch via `trafilatura` (up to 5,000 chars)
- Prompt injection scrubbing via `PROMPT_INJECTION_RE`
- NYC address extraction via regex pattern matching
- Story normalization via `enrich_normalized_story()` from `story_normalizer.py`
- Entity extraction (companies, amounts, locations, asset classes, topics, attention features)

**Output:** Enriched candidate stories ready for edition selection

### 2.5 EDITION MODE — EDITION SELECTION

**Module:** `editorial_intelligence.py` — `select_edition()`

**Processing:**
- Clusters stories into editorial events via `event_similarity()` (title token overlap, content overlap, entity overlap)
- Scores each event on: consequence, novelty, conflict, explanatory value, culture, human stakes, evidence, Light Tower right to add value
- Assigns franchises (6 options) via context matching
- Assigns provisional formats (flagship/brief/culture_signal/data_note/deal_tape) based on score thresholds

**Key thresholds:**
- `MUST_READ_THRESHOLD = 56`
- `FLAGSHIP_CANDIDATE_THRESHOLD = 72`
- `DEAL_TAPE_THRESHOLD = 34`
- `DAILY_RESEARCH_FLOOR = 24`
- `DEFAULT_DAILY_ARTICLE_TARGET = 3`

### 2.6 EDITION MODE — RESEARCH DOSSIER

**Module:** `research_dossier.py` — `build_research_dossier()` (line 73)

**Processing:**
- Iterates all independent source URLs in the editorial event
- Extracts fact candidates (sentences with dollar amounts, percentages, dates, attribution verbs)
- Extracts direct quotations (regex `"..."` pattern)
- Tracks independent domains for source diversity
- Checks Light Tower archive for prior related coverage
- Assigns evidence level: `deep` (3+ independent, 2+ full text), `adequate` (2+ independent or primary), `thin` (some sources), `insufficient` (no extractable facts)
- Generates counterquestions for skeptical editing
- Recommends format based on evidence level

**Output:** Structured dossier dict with `sources`, `reported_facts`, `quote_ledger`, `evidence_level`, `reporting_gaps`, `counterquestions`, `prior_light_tower_context`

### 2.7 EDITION MODE — EDITORIAL ROOM

**Module:** `editorial_room.py` — `run_editorial_room()` (line 110)

**LLM Call 2:** DeepSeek (`deepseek-chat`), temperature 0.15, max_tokens 1800, JSON mode

**This is the PRE-WRITING ANALYSIS.** It combines three editorial roles into one prompt:
1. **Angle editor** — proposes materially different angles
2. **Skeptic** — states strongest objections
3. **Assigning editor** — decides format and whether to proceed

**Prompt components:**
- `EDITORIAL_CONSTITUTION` — Light Tower's publishing standard (4 lines)
- Event data (title, summary, score, franchise, desired format)
- Dossier control data (evidence level, source count, reported facts, counterquestions)
- Editorial priors from prior runs
- 11 decision rules (format requirements, source minimums, daily_depth floor)

**Output (room_plan dict):**
- `decision` — write, shorten, deal_tape, defer, kill
- `final_format` — flagship, brief, culture_signal, data_note, deal_tape
- `angle` — the preferred framing
- `why_now` — timeliness justification
- `favored_thesis` — the bounded claim to drive the article
- `alternate_angles` — rejected framings
- `skeptic_objections` — strongest counterarguments
- `reporting_gaps` — what the dossier doesn't establish
- `human_stakes` — the human or institutional consequence
- `concrete_detail` — a source-grounded anchor detail

**Fallback:** If API key unavailable, no LLM call, or evidence insufficient → `deterministic_room_plan()` produces a safe mechanical plan

### 2.8 PROMPT ASSEMBLY

**Module:** `daily_news_agent.py` — `generate_article()` (line 739)

**Voice mode selection** (line 765): `select_editorial_brief()` from `editorial_voice.py`
- Context-based selection across 8 voice modes
- Priority: distress/conflict → basis autopsy, major sale → underwriting margin, policy → consensus under cross-examination, culture dimensions ≥2 → capital after dark, multi-party transaction → counterparty map, time-sensitive → time as cost of capital
- Fallback: deterministic hash if no context match
- Recent modes tracked to avoid repetition (same mode not reused in recent packages)

**Headline shape selection** (line 774): `select_headline_shape()` from `editorial_voice.py`
- Context-based selection across 9 headline shapes
- Priority: has_big_number → Number as the hook, distress/bank_credit → Consequence-led or Contradiction reveal, policy/government → Plain unhedged declaration, 3+ companies → Colon reveal or Verb-first claim
- Fallback: deterministic hash

**EDITION MODE assembly** (lines 787-803):
- System: `EDITION_SYSTEM_PROMPT` + `VOICE_SYSTEM_ADDENDUM`
- User: `EDITION_USER_PROMPT_TEMPLATE` filled with format specs, franchise, room_plan JSON, dossier payload, voice_brief JSON, headline_shape JSON, today's date
- `max_tokens`: 5200 (flagship) or 3000 (other formats)

**LEGACY MODE assembly** (lines 804-818):
- System: `SYSTEM_PROMPT_ENHANCED` (~200 lines, includes `VOICE_SYSTEM_ADDENDUM` + `NARRATIVE_FINANCE_ADDENDUM` via f-string)
- User: `USER_PROMPT_TEMPLATE` filled with story metadata, summary, full text, addresses, voice_brief, headline_shape
- `max_tokens`: 4500

**Model parameters (both modes):**
- Model: `deepseek-chat`
- Temperature: 0.2
- Timeout: 120 seconds

### 2.9 ARTICLE GENERATION — THE SINGLE PASS

**LLM Call 3:** DeepSeek — the main writing call

**What the model receives in its context window (EDITION MODE):**

| Component | Source | Approximate Size |
|-----------|--------|-----------------|
| `EDITION_SYSTEM_PROMPT` | enhanced_prompts.py | ~33 lines (~400 words) |
| `VOICE_SYSTEM_ADDENDUM` | editorial_voice.py | ~50 lines (~550 words) |
| Format specs (name, word range, purpose) | Inline | ~3 lines |
| Franchise name and promise | Franchise dict | ~2 lines |
| `room_plan` JSON (angle, why_now, thesis, skeptic objections, human stakes, concrete detail, reporting gaps, decision, format) | LLM output | ~30-50 lines |
| Research dossier payload (sources, facts, quotes, counterquestions, prior context, reporting gaps) | research_dossier.py | Variable, up to 24,000 chars |
| Voice brief JSON (mode name, opening_move, stance, craft_rule, narrative_finance_checklist) | editorial_voice.py | ~20-30 lines |
| Headline shape JSON (name, instruction, example) | editorial_voice.py | ~4 lines |
| Today's date | Inline | 1 line |
| **TOTAL** | | **~2,000-3,000 words** |

**What the model receives in its context window (LEGACY MODE):**

| Component | Source | Approximate Size |
|-----------|--------|-----------------|
| `SYSTEM_PROMPT_ENHANCED` | enhanced_prompts.py | ~200 lines (~2,000 words) |
| `VOICE_SYSTEM_ADDENDUM` (embedded via f-string) | editorial_voice.py | ~50 lines |
| `NARRATIVE_FINANCE_ADDENDUM` (embedded via f-string) | editorial_voice.py | ~60 lines |
| Source story metadata (title, source, URL, date) | Inline | ~5 lines |
| Source article summary | From story dict | ~100 words |
| Full article text | From trafilatura | Up to 3,500 chars |
| Addresses block | From address extraction | 0-2 lines |
| Voice brief JSON | editorial_voice.py | ~20-30 lines |
| Headline shape JSON | editorial_voice.py | ~4 lines |
| **TOTAL** | | **~3,000-3,500 words** |

**The critical architectural observation:**

The model receives a dense prompt package and is asked to produce, in a single API call:
1. A complete article meeting strict word count requirements
2. A narrative ledger (anchor, tension, cast, mechanism, claim, reader consequence, reported facts, interpretations, open questions, scene)
3. A headline under 90 characters
4. A subtitle under 140/150 characters
5. A slug
6. A category
7. A meta description
8. Tags
9. Sources
10. Social posts (LinkedIn hook, Twitter hook)
11. Data points (edition mode only)
12. An excellence ledger (edition mode only: why_now, original_inference, counterargument, concrete_detail, human_stakes, reader_value, memorable_line, claim_evidence)

**There is no separation between reasoning and prose generation.** The same forward pass that produces the analysis must also produce the writing. This is the single most important structural finding about the system.

### 2.10 SELF-REPAIR LOOP

**Module:** `daily_news_agent.py` — lines 855-898

**Process:**
1. After generation, run `_article_control_findings()` which aggregates all quality checks
2. If findings exist, build `_article_revision_prompt()` containing the findings + current article JSON
3. Send to LLM as a follow-up message (system + original user + revision prompt in a single messages array)
4. LLM produces corrected JSON
5. Re-run all quality gates
6. Repeat up to 2 iterations maximum
7. If 2 iterations exhausted and issues remain → `ValueError`, article discarded

**Key insight:** The self-repair loop is the same model, same setup. It has no additional analytical capability—it simply gets a second chance to fix flagged issues. The revision prompt asks the model to "Correct every listed issue" but gives it the same context window constraints. There is no external editor, no separate QA model, no human review.

### 2.11 QUALITY GATES (FINAL)

**All gates run after the self-repair loop as the final validation before publication.**

**Gate 1: Content Governance** (`content_governance.py` — `independent_quality_issues()`, line 117)
- Word count checks (format-specific minimums and maximums)
- Source URL validity
- Fixture source detection
- Duplicate paragraph detection
- AI language tells (via `editorial_quality_issues()` from `editorial_voice.py`)
- Mojibake encoding damage detection
- Fact audit: claim-to-source verification via `fact_extractor.audit_article_facts()`
- Semantic claim audit: central claim support verification via `fact_extractor.audit_claim_semantic()`

**Gate 2: Narrative Finance** (`editorial_voice.py` — `narrative_finance_issues()`, line 477)
- Verifies all 6 ledger fields present (anchor, tension, mechanism, claim, reader_consequence)
- Verifies cast, reported_facts, interpretations, open_questions are populated lists
- Verifies scene provenance (if `used: true`, both `detail` and `source_basis` must be populated)

**Gate 3: Title Quality** (`editorial_voice.py` — `title_quality_issues()`, line 294)
- Detects overuse of "Shows"/"Tests" as connecting verbs
- Detects overuse of the ", Not X" contrast tail pattern

**Gate 4: Excellence** (`editorial_room.py` — `excellence_issues()`, line 222)
- Format-specific word count compliance
- Independent source count check
- Flagship long-form permission check
- Brief-specific checks: max 3 speculative sentences, no mislabeling redevelopment as net-new supply
- Dossier URL boundary check (article must not cite URLs outside the dossier)
- Data note: requires sourced data point with verified URL
- Excellence ledger: all 7 text fields present (why_now, original_inference, counterargument, concrete_detail, human_stakes, reader_value, memorable_line)
- Claim-evidence map URL verification
- Memorable line must appear verbatim in article body
- No repeated house abstractions ("the question is", "the signal is", etc.)

### 2.12 PUBLICATION

**Module:** `daily_news_agent.py` — PHASE 6 (line 1094)

**Steps:**
1. HTML sanitization via `_HtmlSanitizer` (allowlist tags: p, strong, em, b, i, ul, ol, li, blockquote, br, a, span, h2-h6)
2. Social image generation via `generate_article_image()` (Pillow-based)
3. Write standalone `.html` file to `/insights/` directory
4. Update `insights.json` manifest
5. Update `feed.xml` RSS feed
6. Update `sitemap.xml`
7. Optional: Generate LinkedIn essay package (`linkedin_essay_agent.py`)
8. Save editorial run record (`editorial_store.py`)
9. Build edition document (`edition_manager.py`)
10. Save publication decision
11. Update event memory (duplicate prevention)

---

## 3. Where Fact Verification Sits

```
SOURCE TEXT → dossier building → editorial room → article generation → [FACT VERIFICATION HERE] → publication
                                                                              │
                                                                              ├── audit_article_facts()
                                                                              │   (amounts, companies, addresses)
                                                                              │
                                                                              └── audit_claim_semantic()
                                                                                  (central claim vs. source texts)
```

Fact verification happens **after** the article is written, during the quality gate phase. It does not happen:
- Before the article is drafted (no pre-writing fact constraint enforcement)
- During the self-repair loop (the fact audit is part of the quality gates that trigger repair, but the model receives no fact-checking feedback — only the gate's pass/fail)

The fact audit (`fact_extractor.py`) is purely regex-based. It:
1. Extracts amounts, companies, and addresses from the article body
2. Checks each against the dossier's `source_facts`
3. Flags unmatched claims with a `hold_for_review` boolean
4. The semantic audit checks the central claim against source texts using keyword overlap

This is a post-hoc verification layer, not a preventive one.

---

## 4. The Single-Pass Problem

The architecture's defining characteristic is that **analytical reasoning and prose generation are collapsed into a single LLM call.** This means:

1. **The model cannot "think" separately from "writing."** In a traditional editorial workflow, an analyst identifies what matters (the financial meaning), an editor shapes the argument (the thesis and structure), and a writer produces the prose. Here, all three cognitive tasks are performed in one forward pass.

2. **The only pre-writing analysis is the editorial room call** — a separate LLM call with the same model, at a lower temperature (0.15 vs 0.2), producing a structured JSON plan. But this plan is passed to the writing call as raw JSON text — it's not used by the writing model as a structured reasoning scaffold. The writing model must internally re-derive the analysis from the plan text, not build on it step by step.

3. **The self-repair loop cannot fix fundamental reasoning problems.** It can catch surface-level issues (word count, missing fields, AI tells, repetitive patterns) but cannot detect that the financial analysis is shallow because the model simply didn't have the cognitive "budget" to do deep reasoning while also managing prose quality, voice, structure, and JSON formatting.

4. **The context window density creates competing demands.** The model receives ~2,500 words of instruction about voice, style, structure, what not to do, narrative finance methodology, and format requirements — plus the dossier facts. It must satisfy all these constraints simultaneously. The instructions about prose quality (vary sentences, breathe, show don't tell) compete with instructions about analytical rigor (find the decision, walk through the math, trace the capital stack). In a single pass, the model inevitably optimizes for the most prominent constraint — which is typically the structured output format (valid JSON with all required fields), not the analytical depth.

---

## 5. Model and Parameter Summary

| Parameter | Scoring | Editorial Room | Article Generation | Self-Repair |
|-----------|---------|---------------|-------------------|-------------|
| **Model** | deepseek-chat | deepseek-chat | deepseek-chat | deepseek-chat |
| **Temperature** | 0.2 | 0.15 | 0.2 | 0.15 |
| **Max tokens** | 3500 | 1800 | 3000-5200 | 5200 |
| **Timeout** | 60s | (via call_deepseek) | 120s | 120s |
| **JSON mode** | No | Yes | No (instructed) | No (instructed) |
| **Cost tracked** | Yes | No visible | Yes | Yes |

**Finding:** Every LLM call in the pipeline uses the exact same model (`deepseek-chat`). There is no differentiation between analytical calls and generative calls. The same model at nearly the same temperature performs everything from story scoring to final prose composition.

---

## 6. LLM Call Summary Per Article

### Edition Mode (full pipeline):
1. **Scoring** — rank all stories (1 call, shared across all candidates)
2. **Editorial room** — angle editor + skeptic + assigning editor (1 call per article)
3. **Article generation** — write the complete article (1 call)
4. **Self-repair** — 0-2 revision calls (optional)
**Total per article: 2-4 LLM calls** (excluding shared scoring)

### Legacy Mode:
1. **Scoring** — rank all stories (1 call, shared)
2. **Article generation** — write the complete article (1 call)
3. **Self-repair** — 0-2 revision calls (optional)
**Total per article: 1-3 LLM calls** (excluding shared scoring)

---

## 7. Key Architectural Findings

1. **No separation of reasoning and writing.** The system conflates "what should I say?" with "how should I say it?" into one LLM call.

2. **Same model for all tasks.** `deepseek-chat` is used for scoring, editorial planning, article writing, and self-repair. There is no specialized reasoning model, no chain-of-thought decomposition, no multi-step analytical pipeline.

3. **Post-hoc quality, not pre-hoc structure.** Quality gates run after the fact. The editorial room produces a plan, but that plan is only advisory — it's JSON passed as text, not a structural constraint on the writing model's behavior.

4. **The dossier is fact-rich but the model can't process it deeply.** Up to 24,000 characters of source material flow into the prompt, but the model has no mechanism to "study" the dossier before writing. It must ingest facts, synthesize insights, and produce prose in one forward pass.

5. **Sector-specific prompts exist but are disconnected from the main pipeline.** The 6 sector prompts (PE, DC, Energy, Banking, Fed/Macro, LocalGov) are defined in `sector_prompts.py` but are not integrated into `generate_article()` in the current code path. They are referenced in `bucketed_editorial.py` and `ideas_daily_agent.py` but do not appear in the main Insights edition pipeline documented here.

6. **The system is structured like a newsroom but operates like a single writer.** The editorial room function is named to evoke a multi-role editorial meeting, but it's actually one LLM call producing a JSON blob. The skeptical editor, angle editor, and assigning editor are not separate processes — they're all roles the model is asked to play in a single prompt.
