# 02 — Prompt Inventory: Every Active Prompt in the Writing System

**Purpose:** Catalog every prompt used in the Light Tower Group editorial writing pipeline. For each prompt, document its location, purpose, size, when it's used, and whether it's redundant, conflicting, or unused.

**Date:** July 2026  
**Methodology:** Source-code trace of every string passed as `system` or `user` content in LLM API calls to DeepSeek.

---

## 1. Master Prompt Map

```
                         ┌──────────────────────────────┐
                         │     LLM CALL CONTEXT          │
                         └──────────────────────────────┘
                                        │
          ┌─────────────────────────────┼─────────────────────────────┐
          ▼                             ▼                             ▼
    SCORING CALL                 EDITORIAL ROOM              ARTICLE GENERATION
    (score_stories)              (run_editorial_room)        (generate_article)
          │                             │                             │
          │                             │                    ┌────────┴────────┐
          │                             │                    ▼                 ▼
          │                             │             EDITION MODE       LEGACY MODE
          │                             │                    │                 │
          │                             │              SYSTEM:            SYSTEM:
          │                             │              EDITION_SYSTEM_    SYSTEM_PROMPT_
          │                             │              PROMPT             ENHANCED
          │                             │              [Prompt #2]        [Prompt #1]
          │                             │              + VOICE_ADDENDUM   + VOICE_ADDENDUM
          │                             │              [Prompt #11]       [Prompt #11]
          │                             │                                 + NARRATIVE_
          │                             │              USER:              FINANCE_ADDENDUM
          │                             │              EDITION_USER_      [Prompt #12]
          │                             │              PROMPT_TEMPLATE              
          │                             │              [Prompt #3]        USER:
          │                             │              + EDITORIAL ROOM   USER_PROMPT_
          │                             │                PLAN (JSON)      TEMPLATE
          │                             │              + DOSSIER PAYLOAD  [Prompt #4]
          │                             │              + VOICE BRIEF      + VOICE BRIEF (JSON)
          │                             │              + HEADLINE SHAPE   + HEADLINE SHAPE
          │                             │                                 (JSON)
          │                             │                    │                 │
          │                             │                    ▼                 ▼
          │                             │             SELF-REPAIR       SELF-REPAIR
          │                             │             [Prompt #14]      [Prompt #14]
          │                             │             _article_         _article_
          │                             │             revision_         revision_
          │                             │             prompt            prompt
          ▼                             ▼
    (inline prompt)              (inline prompt
    in score_stories)            in run_editorial_room)
    [Not catalogued as          [Prompt #13]
     persistent — inline
     function-level string]
```

---

## 2. Complete Prompt Inventory

### Prompt #1: SYSTEM_PROMPT_ENHANCED

**File:** `scripts/enhanced_prompts.py`, lines 10-193  
**Type:** System prompt (legacy mode)  
**Status:** ACTIVE — used in legacy code path

**Approximate size:** ~2,200 words / ~2,800 tokens (including embedded VOICE_SYSTEM_ADDENDUM and NARRATIVE_FINANCE_ADDENDUM)

**When used:** 
- Legacy mode article generation (`generate_article()`, line 817)
- Legacy mode self-repair (same system prompt reused, line 872)

**What it contains (documented by section):**

| Section | Lines | Content |
|---------|-------|---------|
| Reader definition | 14-18 | CRE audience profile: owners, developers, lenders, brokers, PE investors, REIT executives |
| The Standard | 22-38 | Four questions every article must answer; rejection rule if they can't be answered |
| Find the Decision, Not the Deal | 41-57 | Narrative methodology: build around invisible decisions, name the people, show their constraints |
| Sentences Breathe | 60-71 | Prose craft rules: vary sentence length, never three equal-length sentences in a row |
| Write From Inside the Deal | 74-94 | Domain-specific instructions for refis (walk through the math), sales (start with basis), distress (special servicer's file), policy (one provision → one deal) |
| The Physical World Is the Evidence | 98-111 | Use addresses, unit counts, building years — compare concrete vs. abstract writing |
| A Real, Chosen Point of View | 114-139 | Five convictions: time as cost, basis tells truth, structure survives cycles, liquidity is permission, every "yes" is "yes, if" |
| Facts, Interpretations, and Gaps | 143-158 | Keep three categories distinct; honesty rule when evidence is thin |
| What Not to Do | 162-181 | Forbidden: invent facts, manufacture access, use deal as pretext, filler words, rhetorical questions, vague forecasts |
| Voice (embedded) | 184-186 | `{VOICE_SYSTEM_ADDENDUM}` — ~550 words |
| Narrative Finance (embedded) | 190-192 | `{NARRATIVE_FINANCE_ADDENDUM}` — ~450 words |

**Key instructions:**
- "Write the piece a deal professional reads at 6 a.m., finishes, and forwards"
- "Find the Decision, Not the Deal"
- "Never let three consecutive sentences share the same length"
- "Basis tells the truth before management does"
- "Keep facts, interpretations, and gaps distinct"
- "Do not use filler words or pompous transitions"

**Recently revised:** Yes. This prompt was rewritten for the narrative financial voice update. It includes the new "Sentences Breathe" section, the "Find the Decision" methodology, and the five convictions.

**Redundancy assessment:** This prompt partially overlaps with EDITION_SYSTEM_PROMPT (#2). Both contain the voice addendum and address fact/inference distinction. SYSTEM_PROMPT_ENHANCED is significantly more detailed on prose craft and analytical method, while EDITION_SYSTEM_PROMPT is more concise and dossier-focused.

---

### Prompt #2: EDITION_SYSTEM_PROMPT

**File:** `scripts/enhanced_prompts.py`, lines 314-354  
**Type:** System prompt (edition mode)  
**Status:** ACTIVE — used in edition code path

**Approximate size:** ~400 words / ~500 tokens (including embedded VOICE_SYSTEM_ADDENDUM)

**When used:**
- Edition mode article generation (`generate_article()`, line 802)
- Edition mode self-repair (reused on line 872)

**What it contains:**
1. Identity: "writer for Light Tower Group's daily curated edition"
2. Dossier boundary rule: "The dossier IS the factual boundary of the article"
3. Attribution rule: cannot upgrade "reportedly" to fact
4. Publishing standard: "Publish only what changes a smart reader's understanding of a capital decision"
5. Deal Tape routing rule: if evidence only supports stating what happened, route to Deal Tape
6. Writing qualities: "clarity, texture, and quiet confidence of memorable financial journalism"
7. Fact/inference/unknown distinction (compressed version)
8. Money tangibility rule: "Make money tangible through reported consequences"
9. Candor rule: "If something is absurd, let the absurdity speak for itself"
10. One-voice rule: "Sound like one informed person with judgment. Not an institution. Not a template."
11. Scale restraint: "One deal is one deal. A pattern across three deals is a pattern."
12. `{VOICE_SYSTEM_ADDENDUM}` embedded

**Key instructions:**
- "You may not invent facts, numbers, quotes, or scenes"
- "Do not add a punchline"
- "Never inflate a routine transaction into a market-wide declaration"

**Redundancy assessment:** This prompt deliberately omits the prose craft rules from SYSTEM_PROMPT_ENHANCED (sentence rhythm, five convictions, what not to do) — those are handled by VOICE_SYSTEM_ADDENDUM instead. EDITION_SYSTEM_PROMPT adds dossier-specific rules (factual boundary, Deal Tape routing, scale restraint) that SYSTEM_PROMPT_ENHANCED lacks. These are complementary, not redundant.

**Conflict assessment:** No direct conflicts. EDITION_SYSTEM_PROMPT is stricter on attribution (cannot upgrade "reportedly" to fact) while SYSTEM_PROMPT_ENHANCED is more detailed on analytical method. When both are applied (they never are — they're used in different code paths), they would reinforce rather than contradict.

---

### Prompt #3: EDITION_USER_PROMPT_TEMPLATE

**File:** `scripts/enhanced_prompts.py`, lines 357-447  
**Type:** User prompt (edition mode)  
**Status:** ACTIVE — used when dossier exists

**Approximate size:** ~900 words / ~1,200 tokens (before variable interpolation)

**When used:**
- Edition mode article generation (`generate_article()`, lines 789-801)

**Template variables:**
- `{format_name}`, `{min_words}`, `{max_words}`, `{format_purpose}` — from FORMAT_SPECS
- `{franchise_name}`, `{franchise_promise}` — from franchise assignment
- `{room_plan}` — JSON string of editorial room output (angle, thesis, skeptic objections, human stakes, etc.)
- `{research_dossier}` — dossier prompt payload (sources, facts, quotes, counterquestions, up to 24,000 chars)
- `{voice_brief}` — JSON string of voice mode
- `{headline_shape}` — JSON string of headline shape
- `{today}` — formatted date

**What it contains:**
1. Assignment block: format, length, franchise, promise
2. Assigning editor and skeptic plan (the LLM-generated room_plan JSON)
3. Verified research dossier (the dossier prompt payload)
4. Voice mode and headline shape (as JSON)
5. Today's date
6. 9 article requirements (dossier-supported opening, explain change without canned pivot, bounded original inference + counterargument, financial mechanism → consequence, preserve uncertainty, sharp ending, word range, brief-specific rules, gross vs. net new supply)
7. JSON output schema: title, subtitle, slug, category, meta_description, tags, body_html, data_points, sources, narrative_ledger, excellence_ledger, linkedin_hook, twitter_hook
8. JSON requirements (7 rules)

**Key instructions:**
- "The dossier is the factual boundary"
- "Do not include a claim merely because the source article or assigning editor suggests it"
- "State one bounded original inference and test it against a counterargument"
- "Compression is an editorial virtue"
- "Distinguish gross building area from net-new supply"

**Redundancy assessment:** This prompt is the edition-mode equivalent of USER_PROMPT_TEMPLATE (#4). Both request the same output structure (JSON with article, narrative_ledger, social posts) but EDITION_USER_PROMPT_TEMPLATE adds dossier-specific constraints, the excellence_ledger requirement, data_points, and format-specific instructions.

---

### Prompt #4: USER_PROMPT_TEMPLATE

**File:** `scripts/enhanced_prompts.py`, lines 196-311  
**Type:** User prompt (legacy mode)  
**Status:** ACTIVE — used when no dossier exists

**Approximate size:** ~1,100 words / ~1,400 tokens (before variable interpolation)

**When used:**
- Legacy mode article generation (`generate_article()`, lines 805-816)

**Template variables:**
- `{title}`, `{source}`, `{url}`, `{published_date}` — from story dict
- `{summary}` — source article summary
- `{full_text}` — trafilatura extracted text (up to 3,500 chars)
- `{addresses_block}` — NYC addresses + lane context
- `{today}` — formatted date
- `{voice_brief}` — JSON string of voice mode
- `{headline_shape}` — JSON string of headline shape

**What it contains:**
1. Source story metadata block
2. Source article summary
3. Full article text
4. Addresses block
5. Editorial mode assignment (voice brief as JSON)
6. Assigned headline shape (as JSON)
7. Editorial task (thesis-led CRE analysis, not recap)
8. Required article logic (6 steps: tension, hidden signal, facts, economics, constraint, sharp close)
9. Forbidden constructions list: "the most important number is not", "the real story", "this is not a story about", "who benefits", "who is exposed", "in this cycle", "the capital stack is becoming"
10. Narrative finance ledger instruction: build anchor, tension, cast, mechanism, claim, reader consequence, reported facts, interpretations, open questions, scene provenance
11. No-invention rule
12. Word count: 800-1,050 words
13. JSON output schema: title, subtitle, slug, category, meta_description, tags, body_html, sources, narrative_ledger, linkedin_hook, twitter_hook
14. JSON requirements (7 rules)

**Key instructions:**
- "Lead with the most interesting tension, contradiction, number, or market implication"
- "State the hidden market signal by paragraph two or three"
- "Do not use canned constructions such as 'the most important number is not'"
- "Before drafting, build a narrative-finance ledger"
- "Set scene.used to false rather than inventing one"

**Redundancy assessment:** The forbidden constructions list partially overlaps with `_AI_TELLS` in `editorial_voice.py` (the quality gate regex patterns). The prompt prohibits them while the quality gate catches them — double coverage, which is good defense-in-depth rather than redundancy.

---

### Prompt #5: PE_SYSTEM_PROMPT

**File:** `scripts/sector_prompts.py`, lines 16-88  
**Type:** System prompt (sector-specific)  
**Status:** DEFINED but NOT ACTIVE in main pipeline

**Approximate size:** ~750 words

**When used (intended):** Private equity article generation in multi-sector pipeline (`bucketed_editorial.py`, `ideas_daily_agent.py`)  
**When used (actual):** NOT integrated into `generate_article()` in `daily_news_agent.py`. The sector prompts are imported elsewhere but do not appear in the main Insight edition code path documented in this audit.

**What it contains:**
1. PE is a people business — name the firm, the partners
2. Strategy taxonomy: buyout, growth equity, take-private, continuation vehicle, secondaries, carve-out, roll-up, distressed-for-control
3. Fund close numbers: target, hard cap, oversubscription, re-up rate, predecessor fund returns, LP commitments
4. Deal numbers: purchase price, EBITDA multiple, equity check, debt package, management rollover, GP coinvest, value creation paths
5. Exit numbers: holding period, MOIC, IRR, entry/exit multiples side by side, buyer type analysis
6. Incentive structure is the hidden motor: management rollover terms, earnout triggers, promote waterfalls
7. What an LP should test: specific, testable observations

**Redundancy assessment:** This prompt introduces PE-specific domain language and analytical frameworks not present in SYSTEM_PROMPT_ENHANCED. It is additive, not redundant. However, it is currently **unused** in the main Insights pipeline.

---

### Prompt #6: DC_SYSTEM_PROMPT

**File:** `scripts/sector_prompts.py`, lines 91-161  
**Type:** System prompt (sector-specific)  
**Status:** DEFINED but NOT ACTIVE in main pipeline

**Approximate size:** ~760 words

**What it contains:**
1. Data centers are power infrastructure with a roof
2. Physical facts first: megawatts, acres, market, utility, tenant, scale
3. Power constraint is the only constraint: interconnection queue, transmission upgrades, timeline, backup generation
4. Financial structure depends on power: spec dev vs. build-to-suit vs. stabilized asset
5. Capital behind the megawatts: hyperscaler cost of capital vs. PE developer IRR vs. infrastructure fund cap rate
6. Cooling system as tenant density signal

**Status:** Same as PE — defined but not active in main pipeline.

---

### Prompt #7: ENERGY_SYSTEM_PROMPT

**File:** `scripts/sector_prompts.py`, lines 164-240  
**Type:** System prompt (sector-specific)  
**Status:** DEFINED but NOT ACTIVE in main pipeline

**Approximate size:** ~820 words

**What it contains:**
1. Energy is the most capital-intensive sector — multi-decade bets on physical assets
2. Physical asset first: technology, capacity, location (grid region, RTO/ISO, load zone), developer, EPC, offtaker, lender, timeline
3. Regulation is the weather: FERC orders, PUC rate cases, EPA rules, DOE loan program, interconnection queue reform, tax credit eligibility
4. The spread is the analytical engine: PPA price vs. cost of capital, regulated ROE vs. WACC, spark spread, capture rate
5. Cross-sector transmission lines: energy ↔ CRE, banking, PE, data centers

**Status:** Same — defined but not active in main pipeline.

---

### Prompt #8: BANKING_SYSTEM_PROMPT

**File:** `scripts/sector_prompts.py`, lines 243-324  
**Type:** System prompt (sector-specific)  
**Status:** DEFINED but NOT ACTIVE in main pipeline

**Approximate size:** ~848 words

**What it contains:**
1. Banking is a confidence game backed by capital requirements
2. The institution is the character: name it, size it with regulatory metrics
3. Regulator specifics: Fed, FDIC, OCC, state banking commission, CFPB — cite specific rule, guidance, consent order
4. Bank portfolio numbers: CRE concentration, construction concentration, ACL, NPA, net charge-off, CET1, LDR, unrealized losses
5. Loan portfolio numbers: committed exposure, funded/unfunded, WA LTV, debt yield, WA rate/spread, maturity schedule, watch list %
6. Transmission mechanism: walk from regulatory change through arithmetic to capital cost impact
7. Private credit angle: how fund economics differ from bank economics

**Status:** Same — defined but not active in main pipeline.

---

### Prompt #9: FED_SYSTEM_PROMPT

**File:** `scripts/sector_prompts.py`, lines 327-421  
**Type:** System prompt (sector-specific)  
**Status:** DEFINED but NOT ACTIVE in main pipeline

**Approximate size:** ~790 words

**What it contains:**
1. Every macro story is about the price and availability of money
2. Open with what happened and why it matters: FOMC vote, CPI, payroll, minutes
3. The gap between expectation and reality is where the analytical edge lives
4. Transmission to capital decisions: cap rates, refinancing, construction lending, bank balance sheets — with specific arithmetic for each
5. Don't overstate: one CPI print is one data point, not a trend
6. Four-category distinction: what the data shows, what the committee said, what the market priced, what is unknown
7. The dots and the language: SEP analysis, FOMC statement word tracking
8. End with something testable: specific data release to watch, spread to monitor, futures contract to check

**Status:** Same — defined but not active in main pipeline.

---

### Prompt #10: LOCALGOV_SYSTEM_PROMPT

**File:** `scripts/sector_prompts.py`, lines 424-516  
**Type:** System prompt (sector-specific)  
**Status:** DEFINED but NOT ACTIVE in main pipeline

**Approximate size:** ~644 words

**What it contains:**
1. Government decisions are capital allocation decisions
2. Name the body, the vote, the action, the trigger, the geography
3. Quote elected officials from the public record
4. The mechanism: from legal text to development math with specific multipliers
5. Money mechanism: tax abatement → annual reduction → NPV impact
6. Market impact: who benefits, who loses, by how much — with spreadsheet-level specificity
7. The local angle is not provincial: cross-jurisdiction pattern recognition

**Status:** Same — defined but not active in main pipeline.

---

### Prompt #11: VOICE_SYSTEM_ADDENDUM

**File:** `scripts/editorial_voice.py`, lines 38-91  
**Type:** System prompt addendum (embedded in both main system prompts)  
**Status:** ACTIVE — embedded via f-string in both EDITION_SYSTEM_PROMPT (#2) and SYSTEM_PROMPT_ENHANCED (#1)

**Approximate size:** ~550 words / ~700 tokens

**When used:** Every article generation call (both edition and legacy mode)

**What it contains:**
1. The Light Tower Editorial Standard: write like you were in the room when the decision got made
2. Prose authority: "like someone who actually does this for a living"
3. Sentence rhythm: "Short. Then longer, building across a series of clauses"
4. Opening: "Start in the middle of something real"
5. Financial mechanics: "walking through them" rather than naming the tool
6. First person: permitted "when it serves the reader" — "I'd watch this lender's next deal" is acceptable with a source-grounded reason
7. Fabrication prohibition: no manufactured site visits, client calls, confidential conversations, personal memories, or deal involvement
8. Non-negotiable reporting rule: "Put the reader there" means use a reported fact with vivid precision, not pretense
9. Lunch-break rhythm: give the reader the point by paragraph three, prefer clean verbs, vary sentence length, explain unavoidable jargon

**Key instruction:** "You may use the first person when it serves the reader" — this is significant because the corpus analysis found **zero** first-person usage across 331+ articles, despite this permission being present in the prompt.

---

### Prompt #12: NARRATIVE_FINANCE_ADDENDUM

**File:** `scripts/editorial_voice.py`, lines 94-140  
**Type:** System prompt addendum  
**Status:** ACTIVE — embedded in SYSTEM_PROMPT_ENHANCED (#1) but NOT in EDITION_SYSTEM_PROMPT (#2)

**Approximate size:** ~450 words / ~580 tokens

**When used:** Legacy mode only (via SYSTEM_PROMPT_ENHANCED f-string). In edition mode, the narrative finance requirements are in the user prompt template instead.

**What it contains:**
1. Every deal is a story about someone who had to decide something under pressure
2. The six-part private ledger:
   - ANCHOR — the reported deal, number, filing, building, or policy action
   - TENSION — what made this decision hard
   - CAST — who had to decide, who had to live with the decision, their clocks
   - MECHANISM — the financial tool or structure, not just named but explained
   - CLAIM — a bounded, defensible interpretation
   - READER CONSEQUENCE — what someone should test, watch, or question next
3. Fact/inference/unknown distinction
4. Scene and physical detail rules: only when supported by source material

**Overlap with EDITION_USER_PROMPT_TEMPLATE:** The edition user prompt requires building a narrative ledger (line 248 in SYSTEM_PROMPT_ENHANCED → lines 385-402 in EDITION_USER_PROMPT_TEMPLATE). The methodology is identical, but it's presented differently (system-level instruction vs. user-level requirement).

---

### Prompt #13: Editorial Room Prompt

**File:** `scripts/editorial_room.py`, lines 123-176 (inline in `run_editorial_room()`)  
**Type:** User prompt (single-call, not templated)  
**Status:** ACTIVE — used in edition mode pre-writing analysis

**Approximate size:** ~600 words / ~800 tokens (before variable interpolation)

**When used:**
- Edition mode pre-writing analysis (`run_editorial_room()`, line 178)
- Only when API key is available and evidence is sufficient

**What it contains:**
1. Role: "angle editor and skeptical assigning editor for Light Tower Group"
2. `EDITORIAL_CONSTITUTION` (4 lines, ~50 words)
3. Event data JSON (title, summary, score, franchise, desired format, selection tier)
4. Dossier control data JSON (evidence level, source count, reported facts, prior context, reporting gaps, counterquestions)
5. Editorial priors JSON (from prior editorial runs)
6. 11 decision rules:
   - Rule 1: Propose materially different angles
   - Rule 2: Select one bounded thesis supported by the dossier
   - Rule 3: State the strongest skeptical objections
   - Rule 4: Identify human or institutional stakes and one source-grounded concrete detail
   - Rule 5: Decide write, shorten, deal_tape, defer, or kill
   - Rule 6: Flagship requires 3+ independent sources and 2+ usable full-text sources
   - Rule 7: Do not reward length, seriousness, or large dollar amounts by themselves
   - Rule 8: Treat editorial priors as hypotheses to test, never as facts to impose
   - Rule 9: Daily_depth brief: one reputable source with 3+ concrete facts is sufficient
   - Rule 10: Missing human stakes alone is not a reason to defer an asset-level brief
   - Rule 11: Defer/kill daily_depth brief for contradictory facts, legal risk, weak source authenticity, duplication, or no defensible CRE consequence
7. Output JSON schema: decision, final_format, angle, why_now, favored_thesis, alternate_angles, skeptic_objections, reporting_gaps, human_stakes, concrete_detail, kill_reason

**Key characteristic:** This prompt asks ONE model to play THREE editorial roles (angle editor, skeptic, assigning editor) in a single response. The roles are not separated into sequential calls or distinct reasoning steps.

**Model parameters:** deepseek-chat, temperature 0.15, max_tokens 1800, JSON mode

---

### Prompt #14: _article_revision_prompt

**File:** `scripts/daily_news_agent.py`, lines 937-963 (function `_article_revision_prompt()`)  
**Type:** User prompt (self-repair)  
**Status:** ACTIVE — used during self-repair loop

**Approximate size:** ~100 words / ~130 tokens (before variable interpolation)

**When used:**
- Self-repair loop, up to 2 iterations per article (line 876)

**What it contains:**
1. Notice that the previous article failed an independent publication control check
2. Instruction to rewrite the complete JSON article
3. Correction command: "Correct every listed issue and include complete narrative_ledger and excellence_ledger objects"
4. Word count requirement: `{min_words}-{max_words}` words (format-specific)
5. Depth instruction: "Build depth through source-grounded analysis of mechanism, incentives, constraints, and open questions — not filler"
6. Constraints: "Do not explain the revision, invent a scene, invent a source, or use a generic template phrase"
7. Control findings (the quality gate issues that triggered repair)
8. Current article JSON (the full article that failed)

**Key characteristic:** The revision prompt simply restates the problems and asks the model to try again. It does not:
- Decompose the problems into separate fixes
- Provide additional analytical guidance
- Use a different temperature or model
- Offer specific examples of how to fix each issue
- Isolate the reasoning step from the prose revision

**Model parameters:** Same model and temperature as original generation (ultimately 0.15), same max_tokens (5200), same timeout (120s)

---

## 3. Additional Context Elements (Not LLM Prompts, But Worth Noting)

### 3.1 Voice Mode Selection (editorial_voice.py, lines 375-453)

**Function:** `select_editorial_brief()`  
**Status:** ACTIVE — called before every article generation

**8 voice modes:**
1. Underwriting margin
2. Basis autopsy
3. Lender's-eye memorandum
4. Counterparty map
5. City in the balance sheet
6. Consensus under cross-examination
7. Time as a cost of capital
8. Operator's field note

**Selection method:** Context-based (not hash-based for priority matches). Matches story topics, features, entities, and culture dimensions against voice mode categories. Hash-based fallback if no context match.

**How it reaches the LLM:** The selected voice mode dict is serialized as JSON and inserted into the user prompt (both edition and legacy) as `{voice_brief}`.

### 3.2 Headline Shape Selection (editorial_voice.py, lines 236-291)

**Function:** `select_headline_shape()`  
**Status:** ACTIVE — called before every article generation

**9 headline shapes:**
1. Consequence-led
2. Colon reveal
3. Genuine question
4. Verb-first claim
5. Reader-consequence framing
6. Plain unhedged declaration
7. Contradiction reveal
8. Number as the hook
9. Wry dry observation

**Selection method:** Context-based, similar priority chain to voice mode. Hash-based fallback.

**How it reaches the LLM:** Serialized as JSON into `{headline_shape}` in the user prompt.

### 3.3 Franchise Assignment (editorial_intelligence.py, lines 78-103)

**6 franchises:**
1. Credit Committee Theater — "What the structure reveals about the lender's real risk test."
2. Five Minutes Before Maturity — "How time, extensions, and refinancing pressure redistribute bargaining power."
3. Who Got Paid / Who Got Stuck — "Follow the economics through every party rather than repeating the transaction headline."
4. What the Press Release Left Out — "Separate the announcement from the constraints, incentives, and unanswered questions."
5. Capital After Dark — "Where finance meets status, culture, politics, entertainment, and the life of a city."
6. The Most Expensive Assumption — "Identify the premise on which the capital plan quietly depends."

**How it reaches the LLM:** Through the user prompt template as `{franchise_name}` and `{franchise_promise}`.

### 3.4 Editorial Constitution (editorial_room.py, lines 14-20)

```
"Light Tower publishes only when it can make a smart reader see a capital
decision differently. Accuracy is the floor. The work must add consequence,
mechanism, human or institutional stakes, candor, and a bounded point of
view. Routine facts belong in the deal tape. Wit must be earned by a true
observation. A valid editorial outcome is to kill, shorten, or defer a story."
```

**Status:** This is the guiding editorial philosophy, cited in the editorial room prompt. It is NOT directly embedded in the article generation system prompt, meaning the writing LLM never sees this constitution.

---

## 4. Redundancy Analysis

| Prompt Pair | Overlap | Assessment |
|-------------|---------|------------|
| #1 (SYSTEM_PROMPT_ENHANCED) and #2 (EDITION_SYSTEM_PROMPT) | Both contain VOICE_SYSTEM_ADDENDUM, both address fact/inference distinction, both set editorial standards | Complementary, not redundant. #1 is detailed on prose craft; #2 is concise and dossier-focused. They are used in mutually exclusive code paths. |
| #11 (VOICE_SYSTEM_ADDENDUM) appears in both #1 and #2 | Full duplication | Intentional — it's the shared voice standard embedded in both paths. |
| #3 (EDITION_USER_PROMPT_TEMPLATE) and #4 (USER_PROMPT_TEMPLATE) | Both request the same JSON output structure, both include narrative ledger requirements, both have forbidden constructions | Redundant output schema. The JSON schema in #3 adds data_points and excellence_ledger fields. These could be unified into a single schema with optional fields. |
| Forbidden constructions in #4 vs. `_AI_TELLS` regex in editorial_voice.py | Same phrases | Defense-in-depth, not redundancy. The prompt tries to prevent them; the gate catches them if they slip through. |

---

## 5. Conflict Analysis

| Potential Conflict | Where | Severity |
|-------------------|-------|----------|
| First-person permission vs. corpus reality | VOICE_SYSTEM_ADDENDUM explicitly permits first person ("you may use the first person when it serves the reader"), but the corpus shows zero first-person usage across 331+ articles | Low — the permission is there but the model doesn't use it |
| "Never inflate a routine transaction into a market-wide declaration" (#2) vs. "State the hidden market signal by paragraph two or three" (#4) | EDITION_SYSTEM_PROMPT vs USER_PROMPT_TEMPLATE | Medium — the edition prompt says one deal is one deal, but the legacy user prompt asks for "hidden market signal" which can pressure the model toward overstatement |
| Voice variance instructions vs. single-pass fatigue | SYSTEM_PROMPT_ENHANCED contains detailed prose craft rules (vary sentences, never three equal length, use short paragraphs), but the single-pass generation means the model must execute these rules while also doing analytical work | High — the most important architectural tension in the system |

---

## 6. Unused/Orphaned Prompts

| Prompt | Status | Recommendation |
|--------|--------|---------------|
| PE_SYSTEM_PROMPT (#5) | Defined, not active in main pipeline | Integrate into multi-sector pipeline or archive |
| DC_SYSTEM_PROMPT (#6) | Defined, not active in main pipeline | Same |
| ENERGY_SYSTEM_PROMPT (#7) | Defined, not active in main pipeline | Same |
| BANKING_SYSTEM_PROMPT (#8) | Defined, not active in main pipeline | Same |
| FED_SYSTEM_PROMPT (#9) | Defined, not active in main pipeline | Same |
| LOCALGOV_SYSTEM_PROMPT (#10) | Defined, not active in main pipeline | Same |
| SYSTEM_PROMPT (legacy, line 720) | Inline in daily_news_agent.py, ~15 lines, simpler WSJ-style prompt | Appears to be an orphaned constant — `generate_article()` uses `SYSTEM_PROMPT_ENHANCED` instead. This was the original prompt before the rewrite. |

---

## 7. Prompt Size Summary

| Prompt | Approx. Words | Approx. Tokens | In Context Window |
|--------|--------------|---------------|-------------------|
| SYSTEM_PROMPT_ENHANCED (#1) | 2,200 | 2,800 | All legacy articles |
| EDITION_SYSTEM_PROMPT (#2) | 400 | 500 | All edition articles |
| EDITION_USER_PROMPT_TEMPLATE (#3) | 900 | 1,200 | All edition articles |
| USER_PROMPT_TEMPLATE (#4) | 1,100 | 1,400 | All legacy articles |
| VOICE_SYSTEM_ADDENDUM (#11) | 550 | 700 | All articles (embedded) |
| NARRATIVE_FINANCE_ADDENDUM (#12) | 450 | 580 | Legacy articles only |
| Editorial Room Prompt (#13) | 600 | 800 | Editorial room call only |
| Revision Prompt (#14) | 100 | 130 | Self-repair iterations only |
| **TOTAL per article (edition mode)** | **~2,400** | **~3,100** | System + user + embedded addenda |
| **TOTAL per article (legacy mode)** | **~4,300** | **~5,300** | System + user + embedded addenda |

Note: These totals exclude the variable content (dossier payload, room plan JSON, voice brief JSON, source article text) which can add thousands of additional tokens.
