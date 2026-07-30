# 08 — Modular Prompt Architecture: 15-Stage Editorial Pipeline

**Document:** 08-Modular-Prompt-Architecture
**Date:** July 30, 2026
**Status:** Authoritative Architecture — Required System Design Reference

---

## Table of Contents

1. [Purpose and Design Philosophy](#1-purpose-and-design-philosophy)
2. [Architectural Principles](#2-architectural-principles)
3. [Stage Dependency Diagram](#3-stage-dependency-diagram)
4. [Stage 1: Fact Extraction](#4-stage-1-fact-extraction)
5. [Stage 2: Entity and Party Extraction](#5-stage-2-entity-and-party-extraction)
6. [Stage 3: Financial Analysis](#6-stage-3-financial-analysis)
7. [Stage 4: Incentive Analysis](#7-stage-4-incentive-analysis)
8. [Stage 5: Market Context](#8-stage-5-market-context)
9. [Stage 6: Thesis Generation](#9-stage-6-thesis-generation)
10. [Stage 7: Article Architecture](#10-stage-7-article-architecture)
11. [Stage 8: Article Outline](#11-stage-8-article-outline)
12. [Stage 9: Drafting](#12-stage-9-drafting)
13. [Stage 10: Financial Review](#13-stage-10-financial-review)
14. [Stage 11: Editorial Review](#14-stage-11-editorial-review)
15. [Stage 12: Fact Verification](#15-stage-12-fact-verification)
16. [Stage 13: Final Revision](#16-stage-13-final-revision)
17. [Stage 14: Headline Generation](#17-stage-14-headline-generation)
18. [Stage 15: Metadata Generation](#18-stage-15-metadata-generation)
19. [Parallelization Strategy](#19-parallelization-strategy)
20. [Total Token Budget](#20-total-token-budget)
21. [Implementation Notes](#21-implementation-notes)

---

## 1. Purpose and Design Philosophy

### 1.1 The Single-Call Problem

The original pipeline attempted to produce a complete article in one LLM call. This failed in predictable ways: financial reasoning was shallow, facts were misattributed, the thesis was generic, and the prose lacked the specificity that distinguishes the Light Tower voice. A single forward pass cannot simultaneously extract facts, analyze incentives, construct a thesis, draft prose, and verify itself. It compromises on every dimension.

### 1.2 The Modular Solution

The modular prompt architecture breaks article generation into **15 distinct stages**, each with a dedicated prompt, a specific model, a token budget, and a well-defined output format. Stages pass structured output to downstream stages. No stage does more than one thing. No stage relies on implicit knowledge from a previous stage — all handoffs are explicit data structures.

### 1.3 Why Fifteen Stages

Fifteen stages is not arbitrary. It reflects the minimum decomposition required to ensure:

- **Factual accuracy:** Facts are extracted once, verified once, and never regenerated.
- **Financial depth:** Financial analysis happens before the thesis is formed, not as decoration after.
- **Editorial quality:** Drafting, review, and revision are separate operations by separate models.
- **Traceability:** Every claim in the final article can be traced back through the pipeline to a source fact.

### 1.4 The Two-Phase Structure

Stages 1–8 are **Reasoning Stages**. They produce structured analytical output but no prose. They use cheaper, faster models where possible and reserve premium models for tasks that genuinely require them.

Stages 9–15 are **Production Stages**. They produce and refine the article. They consume the structured output of the reasoning stages and never invent new facts.

---

## 2. Architectural Principles

### 2.1 Separation of Reasoning and Writing

The system must know what it thinks before it writes it. The Analytical Brief (Stages 1–8) is the reasoning document. The draft (Stage 9) is the prose document. Review stages (10–12) compare them. Revision (Stage 13) reconciles differences.

### 2.2 Deterministic Where Possible, LLM Where Necessary

Fact extraction uses regex and named entity recognition first, then falls back to a cheap LLM only for ambiguous cases. Financial calculations (cap rates, DSCR, implied appreciation) are deterministic arithmetic — the LLM identifies which numbers to use; the system does the math.

### 2.3 Model Selection by Task Complexity

Not every stage needs a premium model. The model router assigns:

- **Cheap, fast models** (e.g., DeepSeek-V3, Claude Haiku) to extraction, classification, and metadata tasks.
- **Mid-tier models** (e.g., Claude Sonnet, GPT-4o) to analysis, thesis, and review tasks.
- **Premium models** (e.g., Claude Opus, DeepSeek-R1) to drafting and final revision.

### 2.4 Explicit Handoffs

Every stage output is a structured data object (JSON or typed dict). No stage receives raw text from a previous stage and has to re-parse it. The handoff format is defined, validated, and versioned.

### 2.5 Idempotency and Caching

Every stage is idempotent: given the same inputs, it produces the same outputs. Stage outputs are cached. If a downstream stage fails or a prompt is updated, only the affected stage and its dependents need to rerun.

---

## 3. Stage Dependency Diagram

```
SOURCE TEXT (raw article, dossier, canonical item)
│
├──► Stage 1: Fact Extraction ──────────────┐
│                                            │
├──► Stage 2: Entity & Party Extraction ────┤
│                                            │
├──► Stage 3: Financial Analysis ◄──────────┤ (reads facts + entities)
│                                            │
├──► Stage 4: Incentive Analysis ◄──────────┤ (reads parties + facts)
│                                            │
├──► Stage 5: Market Context ◄──────────────┤ (reads facts + financials)
│                                            │
│    ┌──────────────────────────────────────┘
│    ▼
├──► Stage 6: Thesis Generation ◄── (reads all above: facts, entities,
│                                     financials, incentives, market)
│    │
│    ├──► Stage 7: Article Architecture ◄── (reads thesis + facts)
│    │
│    └──► Stage 8: Article Outline ◄─────── (reads architecture + thesis +
│                                             key facts + financials)
│         │
│         ▼
│    Stage 9: Drafting ◄─────────────────── (reads outline + analytical
│                                             brief + source text)
│         │
│         ├──► Stage 10: Financial Review ◄ (reads draft + Stage 3 output)
│         │
│         ├──► Stage 11: Editorial Review ◄ (reads draft + thesis + voice guide)
│         │
│         └──► Stage 12: Fact Verification ◄ (reads draft + Stage 1 output)
│              │
│              ▼
│         Stage 13: Final Revision ◄─────── (reads draft + all review outputs)
│              │
│              ▼
│         Stage 14: Headline Generation ◄── (reads final article + thesis)
│              │
│              ▼
│         Stage 15: Metadata Generation ◄── (reads final article + headline
│                                             + canonical item)
```

### Dependency Rules

| Stage | Must Complete Before | Can Run In Parallel With |
|-------|---------------------|--------------------------|
| 1. Fact Extraction | 3, 4, 5 | 2 |
| 2. Entity & Party Extraction | 3, 4 | 1 |
| 3. Financial Analysis | 6 | 4, 5 |
| 4. Incentive Analysis | 6 | 3, 5 |
| 5. Market Context | 6 | 3, 4 |
| 6. Thesis Generation | 7, 8 | — |
| 7. Article Architecture | 8 | — |
| 8. Article Outline | 9 | — |
| 9. Drafting | 10, 11, 12 | — |
| 10. Financial Review | 13 | 11, 12 |
| 11. Editorial Review | 13 | 10, 12 |
| 12. Fact Verification | 13 | 10, 11 |
| 13. Final Revision | 14, 15 | — |
| 14. Headline Generation | — | 15 |
| 15. Metadata Generation | — | 14 |

---

## 4. Stage 1: Fact Extraction

### Purpose

Extract every verifiable factual claim from the source material. This stage does not interpret, analyze, or judge facts. It extracts them in a structured format that downstream stages can consume without re-reading source text.

### Input

- `source_texts`: List of full-text source articles (from `research_dossier.py`)
- `canonical_item`: The scored and classified `CanonicalItem`
- `raw_summary`: The RSS/source summary text

### Process

1. **Deterministic extraction (regex):** Dollar amounts, percentages, dates, square footages, unit counts, addresses, company names (against known entity list), person names (capitalized sequences matching name patterns).
2. **LLM fallback (cheap model):** For sentences where deterministic extraction fails (ambiguous pronouns, industry-specific amounts without `$` prefix, narrative amounts embedded in prose), a cheap LLM identifies the fact and returns it in the standard format.
3. **Fact normalization:** All extracted facts are normalized to standard units (e.g., "3.5 billion dollars" → `3500000000.0`, "300 megawatts" → `300.0`).

### Output Format

```json
{
  "extracted_facts": [
    {
      "fact_id": "F001",
      "fact_type": "dollar_amount | percentage | date | square_footage | unit_count | megawatt | entity_action | location | other",
      "raw_text": "Amazon Web Services plans a new 300-megawatt hyperscale data center campus",
      "normalized_value": 300.0,
      "normalized_unit": "megawatts",
      "source_index": 0,
      "source_span": [0, 72],
      "confidence": 0.98,
      "extraction_method": "regex | llm",
      "fact_category": "size | cost | timeline | location | party | action | condition"
    }
  ],
  "total_facts": 24,
  "extraction_stats": {
    "regex_extracted": 18,
    "llm_extracted": 6,
    "ambiguous_flagged": 2
  }
}
```

### Model

**Deterministic + cheap LLM fallback.** The regex engine runs locally with zero token cost. The LLM fallback uses **DeepSeek-V3** or **Claude Haiku** — any model capable of basic entity-value extraction.

### Token Budget

- **Input:** Source text (up to 8,000 tokens) + extraction schema (~200 tokens) = ~8,200 tokens
- **LLM fallback output:** ~500 tokens per ambiguous sentence, ~3,000 tokens total for 6 ambiguous sentences
- **Total LLM tokens:** ~11,200 (only when LLM fallback is needed)

### Mandatory

**Yes.** No downstream stage can operate without extracted facts. This is the foundation of the entire pipeline. If fact extraction fails, the pipeline aborts.

---

## 5. Stage 2: Entity and Party Extraction

### Purpose

Identify every named entity (company, person, government body, fund, property) in the source material, resolve them to canonical names, and classify their roles in the transaction.

### Input

- `source_texts`: Full-text source articles
- `canonical_item`: Pre-populated entity fields (companies, people, buyers, sellers, lenders, developers)
- `entity_registry`: Known entity database (from `classification.py`)

### Process

1. **NER extraction:** Named Entity Recognition against the source texts using the known entity registry.
2. **Role classification:** Each entity is classified by its role: buyer, seller, lender, developer, tenant, advisor, government regulator, competitor, beneficiary, affected party.
3. **Canonical name resolution:** "Amazon Web Services", "AWS", "Amazon" are resolved to a single canonical entity ID.
4. **Relationship mapping:** Entities are linked: "AWS is the parent of AWS Data Centers Inc.", "Loudoun County approved the project."

### Output Format

```json
{
  "entities": [
    {
      "entity_id": "E001",
      "canonical_name": "Amazon Web Services",
      "aliases": ["AWS", "Amazon"],
      "entity_type": "corporation",
      "role": "buyer | developer",
      "role_confidence": 0.95,
      "parent_entity_id": null,
      "publicly_traded": true,
      "ticker": "AMZN",
      "sector": "technology | cloud_infrastructure"
    }
  ],
  "relationships": [
    {
      "from_entity_id": "E001",
      "to_entity_id": "E003",
      "relationship_type": "received_approval_from",
      "source_span": [245, 310]
    }
  ],
  "entity_count": 8,
  "unresolved_entities": []
}
```

### Model

**Deterministic NER + cheap LLM for disambiguation.** The entity registry handles known entities. The LLM (DeepSeek-V3 or Claude Haiku) handles novel entities and role classification.

### Token Budget

- **Input:** Source text (~8,000 tokens) + entity registry subset (~1,000 tokens) = ~9,000 tokens
- **Output:** ~2,000 tokens
- **Total:** ~11,000 tokens

### Mandatory

**Yes.** Party identification is required for incentive analysis (Stage 4) and for the cast component of the article architecture.

---

## 6. Stage 3: Financial Analysis

### Purpose

Extract, calculate, and interpret every financial data point in the story. This stage produces the transaction economics section of the Analytical Brief. It distinguishes between reported numbers (directly stated in the source), calculated numbers (derived from reported numbers), and missing numbers (should be present but are not).

### Input

- `extracted_facts`: Output from Stage 1
- `canonical_item`: Pre-populated financial fields
- `sector_framework`: Financial metrics relevant to the story's sector (from `sector_prompts.py`)

### Process

1. **Reported number extraction:** Identify every dollar amount, percentage, ratio, and count in the facts. Classify each: `reported` (directly stated), `derived` (calculable from two reported numbers), `implied` (suggested but not stated), `missing` (relevant metric not provided).
2. **Deterministic calculation:** For `derived` numbers, compute them deterministically. Cap rate = NOI / price. DSCR = NOI / debt service. Basis per unit = total basis / unit count. Cost per megawatt = total investment / megawatts.
3. **Benchmarking:** Compare each calculated metric against sector benchmarks from `config/thresholds.json`.
4. **Financial narrative:** Identify the "money sentence" — the single financial fact that most determines the story's significance.

### Output Format

```json
{
  "transaction_economics": {
    "reported": [
      {
        "metric": "total_investment",
        "value": 3500000000.0,
        "unit": "USD",
        "source_fact_id": "F003",
        "precision": "stated"
      },
      {
        "metric": "megawatts",
        "value": 300.0,
        "unit": "MW",
        "source_fact_id": "F001",
        "precision": "stated"
      }
    ],
    "calculated": [
      {
        "metric": "cost_per_megawatt",
        "value": 11666666.67,
        "unit": "USD_per_MW",
        "formula": "total_investment / megawatts",
        "inputs": ["F003", "F001"],
        "benchmark": 10000000.0,
        "benchmark_source": "Northern Virginia average, Q2 2026",
        "deviation_pct": 16.7,
        "significance": "above_market"
      }
    ],
    "missing": [
      {
        "metric": "cap_rate",
        "reason": "Not applicable to owner-occupied data center development",
        "criticality": "low"
      },
      {
        "metric": "power_purchase_agreement_rate",
        "reason": "Not disclosed; relevant for tenant economics",
        "criticality": "medium"
      }
    ]
  },
  "money_sentence": "At $11.7 million per megawatt, AWS is paying a 17% premium to the Northern Virginia average — a signal either of site-specific constraints or of infrastructure scope beyond standard hyperscale.",
  "financial_significance_score": 7.5
}
```

### Model

**Deterministic calculations + mid-tier LLM for interpretation.** The math is code. The LLM (Claude Sonnet or GPT-4o) handles benchmarking interpretation, significance assessment, and the money sentence.

### Token Budget

- **Input:** Extracted facts (~4,000 tokens) + sector framework (~1,000 tokens) = ~5,000 tokens
- **Output:** ~3,000 tokens
- **Total:** ~8,000 tokens

### Mandatory

**Yes.** Financial analysis is the core differentiator of Light Tower content. A story without financial analysis is not a Light Tower story.

---

## 7. Stage 4: Incentive Analysis

### Purpose

For each identified party, determine what they want, what they fear, what constraints they face, and what their participation reveals about their strategy. This stage answers: "Why did this transaction happen in this way at this time?"

### Input

- `extracted_facts`: Output from Stage 1
- `entities`: Output from Stage 2
- `transaction_economics`: Output from Stage 3

### Process

1. **Party profiling:** For each entity, assemble everything known: stated goals, historical behavior, financial position, regulatory environment.
2. **Incentive mapping:** For each party, identify: desired outcome, feared outcome, constraint, bet.
3. **Conflict identification:** Find where party incentives conflict. These conflicts are the story's dramatic engine.
4. **Winner/loser analysis:** Given the transaction structure, which party got the better deal and why?

### Output Format

```json
{
  "party_incentives": [
    {
      "entity_id": "E001",
      "canonical_name": "Amazon Web Services",
      "desired_outcome": "Secure 300MW of power capacity in the world's largest data center market to support cloud revenue growth.",
      "feared_outcome": "Power capacity constraints in Northern Virginia force migration of incremental cloud workloads to higher-latency regions.",
      "constraint": "Dominion Energy interconnection queue — 7+ year wait for new transmission capacity in Loudoun County.",
      "bet": "Paying a site premium now is cheaper than losing cloud market share to Microsoft Azure, which has 2.4GW of committed capacity in the same market.",
      "leverage": "AWS is the largest taxpayer in Loudoun County; county incentives are contingent on continued investment."
    }
  ],
  "conflicts": [
    {
      "parties": ["E001", "E004"],
      "conflict_type": "resource_competition",
      "description": "AWS and competing data center operators are bidding for the same constrained power interconnection slots.",
      "stakes": "Whichever operator secures interconnection first captures the available transmission capacity."
    }
  ],
  "incentive_thesis": "AWS is not buying land. It is buying queue position. The premium reflects the NPV of cloud revenue that would be forgone if capacity were not available by 2028."
}
```

### Model

**Mid-tier LLM (Claude Sonnet, GPT-4o).** Incentive analysis requires causal reasoning about human and institutional behavior — a task that cheaper models handle poorly and premium models do well. Mid-tier models handle this effectively.

### Token Budget

- **Input:** Facts (~4,000 tokens) + entities (~2,000 tokens) + financials (~1,500 tokens) = ~7,500 tokens
- **Output:** ~3,000 tokens
- **Total:** ~10,500 tokens

### Mandatory

**Yes.** The Light Tower editorial lens is fundamentally incentive-driven. An article that reports what happened without explaining why each party acted is an incomplete article.

---

## 8. Stage 5: Market Context

### Purpose

Place the story in its market context. What trends does it reflect? What does it signal about the sector? How does it compare to similar transactions? This stage provides the "so what" that elevates a transaction report into market intelligence.

### Input

- `extracted_facts`: Output from Stage 1
- `transaction_economics`: Output from Stage 3
- `sector_data`: Market data for the story's sector (cap rate trends, volume trends, comparable transactions)
- `canonical_item`: Sector classification and geography

### Process

1. **Trend fit:** Does this transaction confirm, accelerate, or contradict known sector trends?
2. **Comparable transactions:** Identify 2–3 similar recent transactions. Compare size, pricing, structure.
3. **Market signal:** What does this transaction signal to other market participants? Who should change their behavior based on this information?
4. **Timing significance:** Why now? What changed that made this transaction possible or necessary at this moment?

### Output Format

```json
{
  "market_context": {
    "sector": "data_centers",
    "geography": "Northern Virginia / Loudoun County",
    "trend_alignment": "confirms",
    "trend_description": "Hyperscale data center investment in Northern Virginia continues to accelerate despite power constraints. This is the fourth 200MW+ campus announced in the market in Q3 2026.",
    "comparables": [
      {
        "description": "Microsoft's 400MW Boydton, VA campus expansion, announced June 2026",
        "cost_per_mw": 10500000.0,
        "deviation": "+11% vs. AWS campus"
      }
    ],
    "market_signal": "Land prices in Loudoun County's data center overlay district will increase 15-20% within 12 months as remaining developable parcels are absorbed.",
    "timing_rationale": "AWS needed to secure capacity before Dominion Energy's Q4 2026 interconnection queue window closes, after which the next window is not until 2028.",
    "sector_cycle_position": "mid_cycle_accelerating",
    "risk_factors": [
      "Dominion Energy transmission capacity constraints",
      "Loudoun County considering data center moratorium",
      "Interest rate sensitivity of $3.5B capex commitment"
    ]
  }
}
```

### Model

**Mid-tier LLM (Claude Sonnet, GPT-4o).** Market context requires synthesis of multiple data sources and the ability to draw defensible inferences — a mid-tier model task.

### Token Budget

- **Input:** Facts (~3,000 tokens) + financials (~1,500 tokens) + sector data (~2,000 tokens) = ~6,500 tokens
- **Output:** ~2,500 tokens
- **Total:** ~9,000 tokens

### Mandatory

**Yes, for Tier 1 and Tier 2 stories.** For Tier 3 stories, scaled market context is generated from the canonical item fields directly.

---

## 9. Stage 6: Thesis Generation

### Purpose

Produce the article's thesis: a single, specific, arguable claim that the article will prove. The thesis is NOT a topic statement ("This article is about AWS building a data center"). It IS an argument ("AWS's Loudoun County campus reveals that data center site selection is no longer about land — it is about queue position in the interconnection line").

### Input

- `extracted_facts`: Output from Stage 1
- `transaction_economics`: Output from Stage 3
- `party_incentives`: Output from Stage 4
- `market_context`: Output from Stage 5

### Process

1. **Candidate theses (3–5):** Generate multiple candidate theses, each taking a different angle on the story.
2. **Thesis evaluation:** Score each candidate on: specificity (is it about this deal, not deals like this?), arguability (could someone reasonably disagree?), evidence support (can the extracted facts support it?), reader interest (will a CRE professional care?).
3. **Thesis selection:** Select the best thesis. If no thesis scores above threshold, generate more candidates or flag for human review.
4. **Counterargument generation:** For the selected thesis, generate the strongest counterargument. The counterargument must be defensible — not a strawman.

### Output Format

```json
{
  "thesis": {
    "statement": "AWS's $3.5 billion Loudoun County campus is not a real estate play — it is a power infrastructure play disguised as a data center announcement. The transaction economics make sense only if you model the NPV of cloud revenue that would be lost if this capacity were not online by 2028.",
    "specificity_score": 9,
    "arguability_score": 8,
    "evidence_support_score": 7,
    "reader_interest_score": 8,
    "composite_thesis_score": 8.0
  },
  "counterargument": {
    "statement": "This is simply AWS building capacity to meet demand in its largest market. The premium is explained by Loudoun County land costs, not by a queue-position thesis. Every hyperscaler is paying similar premiums.",
    "strength": "moderate",
    "rebuttal": "If this were routine capacity expansion, AWS would have announced multiple campuses, not a single large one. The concentration of 300MW in one site — rather than 3x100MW across multiple sites — supports the queue-position thesis."
  },
  "alternative_theses": [
    {
      "statement": "AWS is front-running an expected data center moratorium in Loudoun County by securing entitlements before the regulatory window closes.",
      "rejected_reason": "No evidence of imminent moratorium beyond speculation; weaker than queue-position thesis."
    }
  ]
}
```

### Model

**Mid-tier LLM (Claude Sonnet).** Thesis generation requires genuine analytical reasoning across multiple dimensions. The model must understand the facts deeply enough to form an argument about them.

### Token Budget

- **Input:** Combined Stage 1–5 outputs (~15,000 tokens) + thesis schema (~500 tokens) = ~15,500 tokens
- **Output:** ~3,000 tokens
- **Total:** ~18,500 tokens

### Mandatory

**Yes.** A Light Tower article without a thesis is a news summary. The thesis is what distinguishes editorial content from reporting.

---

## 10. Stage 7: Article Architecture

### Purpose

Select the narrative structure that best serves the thesis and the source material. The architecture determines the article's section sequence, argument flow, and structural logic — before any prose is written.

### Input

- `thesis`: Output from Stage 6
- `extracted_facts`: Output from Stage 1
- `canonical_item`: Sector, event type, story depth
- `architecture_library`: Available article architectures (from `analytical_brief.py`)

### Process

1. **Architecture selection:** Match the story against the library of available architectures. Each architecture is a named pattern: `the_ticking_clock`, `the_contrarian_take`, `the_anatomy_of_a_deal`, `the_market_signal`, `the_two_sides`, `the_ripple_effect`, `the_basis_is_the_story`, `the_bet_the_company`.
2. **Architecture justification:** Why this architecture fits this story.
3. **Section specification:** Define the article's sections, their purpose, and what each section must accomplish.

### Output Format

```json
{
  "article_architecture": {
    "name": "the_contrarian_take",
    "justification": "The surface story is 'AWS builds data center.' The actual story is 'power queue position is the binding constraint on cloud growth.' The contrarian architecture lets the article state the surface story, then flip it.",
    "sections": [
      {
        "name": "lead",
        "purpose": "State the surface story: AWS announces $3.5B, 300MW campus. Ground in a specific reported number.",
        "target_length": "2-3 paragraphs",
        "key_elements": ["the $3.5B number", "the 300MW number", "the Loudoun County location"]
      },
      {
        "name": "the_flip",
        "purpose": "Reveal the actual story: this is not about real estate. It is about interconnection queue position.",
        "target_length": "2-3 paragraphs",
        "key_elements": ["cost-per-MW premium calculation", "Dominion Energy queue context", "NPV framing"]
      },
      {
        "name": "the_evidence",
        "purpose": "Present the financial and strategic evidence that supports the queue-position thesis.",
        "target_length": "4-5 paragraphs",
        "key_elements": ["comparables", "timeline pressure", "competitive dynamics with Microsoft"]
      },
      {
        "name": "the_implication",
        "purpose": "What this means for other market participants.",
        "target_length": "2-3 paragraphs",
        "key_elements": ["land price signal", "queue-position as asset class", "who wins and who loses"]
      },
      {
        "name": "the_reader_consequence",
        "purpose": "Give the reader something testable: a question to ask, a number to watch, a deal to compare.",
        "target_length": "1-2 paragraphs",
        "key_elements": ["watch Dominion Energy's Q4 queue", "compare next hyperscale announcement pricing"]
      }
    ]
  }
}
```

### Model

**Cheap-to-mid LLM (DeepSeek-V3, Claude Haiku, or Claude Sonnet).** Architecture selection is a pattern-matching and structural task that does not require premium reasoning.

### Token Budget

- **Input:** Thesis (~3,000 tokens) + facts summary (~2,000 tokens) + architecture library (~1,500 tokens) = ~6,500 tokens
- **Output:** ~2,000 tokens
- **Total:** ~8,500 tokens

### Mandatory

**Yes.** Articles written without an architecture read as shapeless blocks of text. The architecture is the skeleton that the outline and draft hang on.

---

## 11. Stage 8: Article Outline

### Purpose

Produce a detailed outline that specifies, for each section of the architecture, what paragraphs it contains, what claim each paragraph makes, what evidence supports each claim, and what transition connects each paragraph to the next. The outline is the bridge between analytical reasoning and prose generation.

### Input

- `article_architecture`: Output from Stage 7
- `thesis`: Output from Stage 6
- `extracted_facts`: Output from Stage 1
- `transaction_economics`: Output from Stage 3
- `party_incentives`: Output from Stage 4
- `market_context`: Output from Stage 5

### Process

1. **Section-level outlining:** For each architecture section, specify the argument that section makes.
2. **Paragraph-level specification:** For each paragraph: claim, evidence (with fact_id references), transition.
3. **Evidence assignment:** Every claim in the outline must reference at least one fact_id from Stage 1. Claims without evidence are flagged.
4. **Flow check:** Verify that paragraphs flow logically — each paragraph sets up the one that follows.

### Output Format

```json
{
  "outline": {
    "sections": [
      {
        "section_name": "lead",
        "paragraphs": [
          {
            "paragraph_number": 1,
            "claim": "AWS is making its largest single-campus data center bet in history.",
            "evidence_fact_ids": ["F001", "F003"],
            "transition_to_next": "The headline number is large — but the real story is in what the number doesn't say.",
            "voice_note": "Open with the number. Put it in context immediately."
          },
          {
            "paragraph_number": 2,
            "claim": "At $11.7M per megawatt, AWS is paying well above the Northern Virginia average.",
            "evidence_fact_ids": ["C001"],
            "transition_to_next": "To understand why, you have to look at what AWS is really buying.",
            "voice_note": "Show the math. The reader should feel the premium."
          }
        ]
      }
    ]
  },
  "orphaned_claims": [],
  "evidence_coverage_pct": 94.0
}
```

### Model

**Mid-tier LLM (Claude Sonnet, GPT-4o).** Outlining requires understanding both the analytical content and the craft of structuring an argument — a task that rewards a model with strong reasoning and writing capabilities.

### Token Budget

- **Input:** All Stage 1–7 outputs (~25,000 tokens) + outline schema (~500 tokens) = ~25,500 tokens
- **Output:** ~4,000 tokens
- **Total:** ~29,500 tokens

### Mandatory

**Yes.** Drafting without an outline is the single largest source of structural problems in the current system. The outline captures the analytical structure before the drafting model's prose fluency obscures it.

---

## 12. Stage 9: Drafting

### Purpose

Produce the complete first draft of the article. This is the ONLY stage that generates article prose. All previous stages generated structured analytical data. All subsequent stages review, verify, and revise the prose this stage produces.

### Input

- `article_outline`: Output from Stage 8 (complete paragraph-by-paragraph specification)
- `analytical_brief`: Compiled brief from Stages 1–8
- `source_texts`: Original source material (for reference, not for new fact extraction)
- `voice_config`: Editorial voice parameters (from `editorial_voice.py` — tone, rhythm, authority level, first-person permission)
- `headline_shape`: Working headline structure(s) to guide the opening
- `sector_prompt`: Sector-specific system prompt (from `sector_prompts.py`)

### Process

1. **System prompt assembly:** Combine the voice config and sector prompt into the system prompt. The analytical brief and outline go into the user prompt.
2. **Section-by-section generation:** The draft is generated section by section, not in a single call. Each section receives: the outline for that section, the relevant portion of the analytical brief, and the preceding sections for continuity.
3. **Fact freeze:** The drafting model is explicitly instructed not to introduce new factual claims beyond what is in the analytical brief. It may phrase, frame, and sequence facts — but not invent them.
4. **Voice injection:** The system prompt includes the full voice guide, with emphasis on: concrete nouns, active verbs, sentence rhythm variation, the lunch-break test, and the prohibition on fabricated scene-setting.

### Output Format

```json
{
  "draft": {
    "headline": "[Working headline — will be finalized in Stage 14]",
    "body_html": "<article>...</article>",
    "sections": [
      {
        "section_name": "lead",
        "html": "<p>...</p><p>...</p>",
        "paragraph_count": 3,
        "word_count": 187
      }
    ],
    "total_word_count": 850,
    "readability_metrics": {
      "flesch_kincaid": 42.0,
      "avg_sentence_length": 18.3,
      "sentence_length_variance": 0.72
    }
  },
  "generation_metadata": {
    "model": "claude-opus-4-20250514",
    "temperature": 0.7,
    "sections_generated": 5,
    "fact_deviations": []
  }
}
```

### Model

**Premium model only — Claude Opus, DeepSeek-R1, or GPT-4o (not mini).** This is the only stage where prose quality directly determines article quality. The premium model investment here pays for itself in reduced revision work and higher editorial scores.

The model must:
- Write financial prose that a professional would not find embarrassing
- Vary sentence rhythm naturally
- Handle the voice requirements (concrete, specific, unpretentious)
- Follow a detailed outline without sounding mechanical
- Respect the fact freeze

### Token Budget

- **System prompt:** Voice config + sector prompt + drafting instructions (~3,000 tokens)
- **Input per section:** Outline portion (~800 tokens) + brief portion (~2,000 tokens) + preceding sections (~1,500 tokens) = ~4,300 tokens
- **Output per section:** ~500 tokens
- **Total per section:** ~7,800 tokens
- **Total for 5 sections:** ~39,000 tokens

### Mandatory

**Yes.** Obviously. This is the article. Every other stage exists to support this one.

---

## 13. Stage 10: Financial Review

### Purpose

Verify that every financial claim in the draft is correct, supported by the financial analysis (Stage 3), and free of calculation errors. This is NOT a proofreading stage. It is a financial accuracy audit.

### Input

- `draft`: Output from Stage 9
- `transaction_economics`: Output from Stage 3
- `extracted_facts`: Output from Stage 1 (financial subset)

### Process

1. **Financial claim extraction:** Extract every sentence in the draft that makes a financial claim (dollar amount, percentage, ratio, comparison, benchmark).
2. **Source mapping:** For each financial claim, map it to its source in the Stage 3 output. Claims that have no source in Stage 3 are flagged as potential hallucinations.
3. **Calculation verification:** For any calculated numbers (cap rates, per-unit costs, implied appreciation), re-run the deterministic calculation from the original inputs. Flag discrepancies.
4. **Precision audit:** Check that numbers are reported with appropriate precision. "$3.5 billion" is appropriate for a corporate announcement; "$3,500,000,000.00" is not.

### Output Format

```json
{
  "financial_review": {
    "total_financial_claims": 12,
    "verified_claims": 10,
    "flagged_claims": [
      {
        "claim_text": "The campus will deliver a 7.2% stabilized yield.",
        "issue": "no_source",
        "severity": "high",
        "recommendation": "Remove claim. No yield data in source material or Stage 3 output."
      }
    ],
    "calculation_errors": [
      {
        "claim_text": "At $11.7M per megawatt...",
        "expected_value": 11666666.67,
        "draft_value": 11700000.0,
        "discrepancy": "rounding",
        "severity": "low",
        "recommendation": "Acceptable rounding for prose."
      }
    ],
    "precision_issues": [],
    "financial_score": 8.5,
    "pass": true
  }
}
```

### Model

**Cheap-to-mid LLM (DeepSeek-V3, Claude Haiku, or Claude Sonnet).** The heavy financial reasoning happened in Stage 3. This stage is verification — pattern matching claims against sources, re-running deterministic math, checking precision conventions. A cheaper model suffices.

### Token Budget

- **Input:** Draft (~7,000 tokens) + financial analysis (~3,000 tokens) + financial facts (~2,000 tokens) = ~12,000 tokens
- **Output:** ~2,000 tokens
- **Total:** ~14,000 tokens

### Mandatory

**Yes, for all stories with transaction_economics content.** Stories with no financial content (rare) skip this stage.

---

## 14. Stage 11: Editorial Review

### Purpose

Evaluate the draft against the full 14-dimension editorial scoring rubric (see Document 09). Identify specific problems, not general impressions. Every flagged issue must include a line reference and a suggested fix.

### Input

- `draft`: Output from Stage 9
- `thesis`: Output from Stage 6 (to verify the draft actually argues the thesis)
- `voice_guide`: Full editorial voice specification (Document 06)
- `scoring_rubric`: Full 14-dimension rubric (Document 09)

### Process

1. **Dimension-by-dimension scoring:** Score the draft on all 14 dimensions. Each score requires a one-sentence justification.
2. **Below-threshold diagnosis:** For any dimension scoring below its minimum threshold, provide: the specific passage(s) that caused the low score, the nature of the deficiency, and a concrete fix.
3. **Voice compliance check:** Verify the draft adheres to the voice guide: concrete nouns, active verbs, varied rhythm, authority through specificity, no fabricated scene-setting.
4. **Thesis fidelity check:** Does the draft actually argue the thesis from Stage 6, or did the drafting model drift to a different argument?

### Output Format

```json
{
  "editorial_review": {
    "dimension_scores": {
      "factual_accuracy": {"score": 9, "justification": "All claims trace to source facts. No hallucinated numbers detected."},
      "financial_understanding": {"score": 8, "justification": "Cost-per-MW calculation correctly shown. Could go deeper on interconnection cost allocation."},
      "analytical_originality": {"score": 8, "justification": "Queue-position framing is original and defensible. Counterargument is fairly represented."},
      "thesis_strength": {"score": 7, "justification": "Queue-position thesis is maintained throughout. Weakening in paragraph 8 where it shifts to generic 'market demand' language."},
      "incentive_analysis": {"score": 7, "justification": "AWS's incentive is clear. Microsoft's competitive position underdeveloped."},
      "use_of_numbers": {"score": 8, "justification": "Strong: $3.5B, 300MW, $11.7M/MW. Benchmark comparison provided."},
      "market_context": {"score": 7, "justification": "NOVA market context present. Missing discussion of PJM capacity market implications."},
      "narrative_structure": {"score": 8, "justification": "Lead-flip-evidence-implication-reader structure is clear and effective."},
      "opening_quality": {"score": 9, "justification": "Opens with the number and immediately contextualizes it. Strong."},
      "sentence_quality": {"score": 7, "justification": "Good rhythm in sections 1-3. Section 4 paragraphs run long. One 42-word sentence should be split."},
      "originality_of_language": {"score": 7, "justification": "'Queue position' framing is fresh. Some CRE clichés in market context section."},
      "intellectual_honesty": {"score": 9, "justification": "Counterargument acknowledged. Unknowns flagged. No false certainty."},
      "reader_utility": {"score": 7, "justification": "Reader consequence is testable. Could be more specific about what to watch."},
      "conclusion_quality": {"score": 7, "justification": "Ends with actionable watch-item. Not as strong as opening."}
    },
    "overall_score": 7.6,
    "below_threshold": [
      {
        "dimension": "thesis_strength",
        "score": 7,
        "threshold": 7,
        "location": "paragraph 8",
        "issue": "Language shifts from queue-position argument to generic 'strong market demand.'",
        "fix": "Replace 'strong market demand' with specific reference to Dominion's Q4 queue deadline."
      }
    ],
    "flagged_passages": [
      {
        "location": "paragraph 14",
        "issue_type": "voice_violation",
        "description": "'The data center market continues to exhibit robust fundamentals' — this is the kind of abstract financial language the voice guide explicitly prohibits.",
        "fix": "Replace with a specific claim: what exactly is robust? Vacancy? Rents? Pipeline?"
      }
    ],
    "thesis_fidelity": "maintained",
    "pass": true
  }
}
```

### Model

**Mid-tier LLM (Claude Sonnet, GPT-4o).** Editorial review requires strong language evaluation and the ability to apply a detailed rubric systematically. Mid-tier models handle this well.

### Token Budget

- **Input:** Draft (~7,000 tokens) + thesis (~2,000 tokens) + rubric (~3,000 tokens) + voice guide (~2,000 tokens) = ~14,000 tokens
- **Output:** ~5,000 tokens
- **Total:** ~19,000 tokens

### Mandatory

**Yes.** Editorial review is the quality gate. No article proceeds to revision without passing editorial review.

---

## 15. Stage 12: Fact Verification

### Purpose

Verify that every factual claim in the draft is supported by at least one extracted fact from Stage 1. Flag unsupported claims. Verify that supported claims haven't drifted in meaning (correct numbers, wrong implications).

### Input

- `draft`: Output from Stage 9
- `extracted_facts`: Output from Stage 1

### Process

1. **Claim extraction:** Extract every factual assertion from the draft — names, numbers, dates, locations, actions, conditions.
2. **Source attribution:** For each claim, find the `fact_id` in the Stage 1 output that supports it. Use fuzzy matching for rephrased claims.
3. **Drift detection:** For matched claims, verify that the claim in the draft hasn't changed the meaning of the source fact.
4. **Hallucination flagging:** Claims with no source match are flagged. Severity is assigned: `critical` (financial number, company name), `high` (location, date), `medium` (qualitative characterization), `low` (non-material detail).

### Output Format

```json
{
  "fact_verification": {
    "total_claims": 28,
    "verified_claims": 25,
    "unsupported_claims": [
      {
        "claim_text": "Dominion Energy's interconnection queue has a 7-year backlog.",
        "severity": "high",
        "nearest_fact_id": null,
        "recommendation": "Verify 7-year backlog claim against source. If unverified, attribute to 'industry estimates' or remove."
      }
    ],
    "drifted_claims": [
      {
        "claim_text": "The campus will span 500 acres.",
        "source_fact_id": "F008",
        "source_text": "The data center campus will be developed on a 450-acre parcel.",
        "drift_description": "Draft says 500 acres; source says 450 acres.",
        "severity": "medium"
      }
    ],
    "verification_rate": 89.3,
    "pass": true
  }
}
```

### Model

**Deterministic matching + cheap LLM for semantic comparison.** Claim-to-fact matching is a search problem best solved with embedding similarity or keyword overlap. The LLM (DeepSeek-V3 or Claude Haiku) handles the semantic comparison for drift detection.

### Token Budget

- **Input:** Draft (~7,000 tokens) + extracted facts (~3,000 tokens) = ~10,000 tokens
- **Output:** ~3,000 tokens
- **Total:** ~13,000 tokens

### Mandatory

**Yes, for all stories.** Fact verification is a non-negotiable quality gate. Stories with a verification rate below 85% are automatically returned to revision or flagged for human review.

---

## 16. Stage 13: Final Revision

### Purpose

Apply all review feedback (Stages 10, 11, 12) to produce the final article. Fix factual errors. Address editorial issues. Tighten prose. Ensure the article meets all minimum thresholds.

### Input

- `draft`: Output from Stage 9
- `financial_review`: Output from Stage 10
- `editorial_review`: Output from Stage 11
- `fact_verification`: Output from Stage 12
- `analytical_brief`: Compiled brief (for reference — the revision shouldn't need new facts)

### Process

1. **Priority-ordered fix queue:** Critical fixes (factual errors, hallucinated numbers) are applied first. High fixes (voice violations, structural issues) next. Medium/low fixes (sentence quality, word choice) last if within budget.
2. **Fix verification:** Each applied fix is checked: did removing the hallucinated number break a sentence? Did fixing the voice violation introduce a new issue?
3. **Score reassessment:** After all fixes, the draft is re-scored on the 14-dimension rubric. If any dimension still falls below threshold, the revision loop iterates (up to 3 iterations).
4. **Final sign-off:** The article is marked as final and the revision history is preserved.

### Output Format

```json
{
  "final_article": {
    "headline": "[Carried from draft — finalized by Stage 14]",
    "body_html": "<article>...</article>",
    "total_word_count": 840,
    "revision_summary": {
      "critical_fixes": 0,
      "high_fixes": 2,
      "medium_fixes": 4,
      "low_fixes": 3,
      "fixes_deferred": 1,
      "fixes_rejected": 1
    }
  },
  "post_revision_scores": {
    "dimension_scores": { /* same structure as Stage 11 output */ },
    "overall_score": 8.1,
    "all_dimensions_above_threshold": true
  },
  "revision_iterations": 1,
  "pass": true
}
```

### Model

**Premium model (Claude Opus, DeepSeek-R1, or equivalent).** Revision requires the model to understand what to change, what to preserve, and how to apply fixes without degrading other dimensions. This is a premium-model task — the model needs to be as good at editing as it is at writing.

### Token Budget

- **Input:** Draft (~7,000 tokens) + reviews (~10,000 tokens) + revision instructions (~1,000 tokens) = ~18,000 tokens
- **Output:** ~6,000 tokens
- **Total per iteration:** ~24,000 tokens
- **Max 3 iterations:** ~72,000 tokens (worst case; typical is 1 iteration at ~24,000 tokens)

### Mandatory

**Yes.** The output of Stage 9 is a draft. The output of Stage 13 is the final article. Skipping revision means shipping a draft.

---

## 17. Stage 14: Headline Generation

### Purpose

Generate the final published headline. The headline must be specific, accurate, and interesting — in that order. The working headline from drafting is a starting point, not the final product.

### Input

- `final_article`: Output from Stage 13
- `thesis`: Output from Stage 6
- `headline_templates`: Library of successful headline structures by sector and event type
- `canonical_item`: Source name, sector, key numbers

### Process

1. **Candidate generation (5–10 headlines):** Multiple headline candidates in different styles: number-led, tension-led, implication-led, question-led.
2. **Accuracy check:** Each candidate is checked against the verified facts. Headlines that overclaim or misrepresent the story are eliminated.
3. **Interest scoring:** Remaining candidates are scored on: specificity, curiosity gap, clarity, sector-appropriateness.
4. **SEO consideration:** The selected headline is checked for keyword presence (sector terms, company names) but never at the expense of accuracy or interest.
5. **Subheadline generation:** A one-sentence subheadline that extends the headline's promise.

### Output Format

```json
{
  "headlines": {
    "primary": "The Real Cost of AWS's Loudoun County Campus: Queue Position, Not Land",
    "candidates": [
      {
        "text": "AWS Is Paying a 17% Premium in Loudoun County. Here's What It's Really Buying.",
        "style": "number_led",
        "accuracy_score": 9,
        "interest_score": 8
      },
      {
        "text": "The $3.5 Billion Bet That Reveals Data Center Site Selection Has Changed Forever",
        "style": "tension_led",
        "accuracy_score": 8,
        "interest_score": 9
      }
    ],
    "subheadline": "At $11.7M per megawatt, the hyperscaler's newest campus is a power infrastructure play hiding in plain sight.",
    "seo_keywords_present": ["AWS", "Loudoun County", "data center", "hyperscale"],
    "clickbait_penalty": 0
  }
}
```

### Model

**Mid-tier LLM (Claude Sonnet, GPT-4o).** Headline generation requires creativity and accuracy — a mid-tier model task. The premium model would be overkill for 5–10 candidate headlines.

### Token Budget

- **Input:** Final article (~6,000 tokens) + thesis (~1,000 tokens) + templates (~500 tokens) = ~7,500 tokens
- **Output:** ~1,500 tokens
- **Total:** ~9,000 tokens

### Mandatory

**Yes.** The headline is the most-read element of the article. A weak headline buries a strong article.

---

## 18. Stage 15: Metadata Generation

### Purpose

Generate all publication metadata: slugs, tags, categories, social descriptions, image suggestions, reading time, and the structured data required for SEO and social sharing.

### Input

- `final_article`: Output from Stage 13
- `primary_headline`: Output from Stage 14
- `canonical_item`: All source metadata
- `analytical_brief`: Key themes and entities

### Process

1. **Slug generation:** URL-safe slug from the headline. Check against existing slugs to avoid collisions.
2. **Tag generation:** 3–5 relevant tags from the controlled tag vocabulary.
3. **Meta description:** 155-character description for search results.
4. **Social description:** Longer description optimized for LinkedIn sharing.
5. **OG image suggestion:** Keywords for the social image generator.
6. **Reading time:** Calculate from word count.
7. **Structured data:** Generate JSON-LD for schema.org Article type.

### Output Format

```json
{
  "metadata": {
    "slug": "real-cost-aws-loudoun-county-queue-position",
    "tags": ["data-centers", "hyperscale", "northern-virginia", "power-infrastructure", "aws"],
    "meta_description": "AWS's $3.5B Loudoun County campus looks like a real estate play — but at $11.7M per megawatt, it's a bet on interconnection queue position.",
    "social_description": "The numbers behind AWS's newest data center campus tell a different story than the press release. At $11.7M/MW, this isn't about land costs. It's about what happens when power infrastructure becomes the binding constraint on cloud growth.",
    "og_image_keywords": ["data center", "Northern Virginia", "utility infrastructure", "aerial"],
    "reading_time_minutes": 4,
    "canonical_url": "https://lighttowergroup.com/insights/real-cost-aws-loudoun-county-queue-position",
    "jsonld": { /* schema.org Article */ }
  }
}
```

### Model

**Cheap LLM (DeepSeek-V3, Claude Haiku).** Metadata generation is a templated task with minor creativity requirements. A cheap model is appropriate.

### Token Budget

- **Input:** Final article (~6,000 tokens) + headline (~500 tokens) + tag vocabulary (~500 tokens) = ~7,000 tokens
- **Output:** ~1,500 tokens
- **Total:** ~8,500 tokens

### Mandatory

**Yes.** Without metadata, the article cannot be published to the CMS, shared on social media, or discovered via search.

---

## 19. Parallelization Strategy

### 19.1 Reasoning Phase (Stages 1–8)

Stages 1 and 2 run in parallel (both read source text independently). Stages 3, 4, and 5 run in parallel after Stages 1–2 complete. Stage 6 runs sequentially after 3–5. Stages 7 and 8 run sequentially after 6.

**Total reasoning wall-clock time:** ~4 sequential steps (1|2 → 3|4|5 → 6 → 7 → 8). With caching, typical reasoning phase completes in 15–30 seconds.

### 19.2 Production Phase (Stages 9–15)

Stage 9 (drafting) is the bottleneck — a single premium-model call that can take 30–90 seconds. Stages 10, 11, and 12 run in parallel after Stage 9 completes. Stage 13 runs sequentially after 10–12. Stages 14 and 15 run in parallel after Stage 13.

**Total production wall-clock time:** ~4 sequential steps (9 → 10|11|12 → 13 → 14|15). Typical production phase completes in 60–120 seconds.

### 19.3 Total Pipeline Latency

**Typical:** 75–150 seconds for a complete article.
**Worst case (3 revision iterations):** 180–300 seconds.

### 19.4 Concurrent Story Processing

The pipeline can process multiple stories concurrently. Stage 9 (the premium model bottleneck) can be staggered: while Story A is drafting, Story B can be in reasoning. A queue of 5 stories can complete all reasoning before the first story finishes drafting.

---

## 20. Total Token Budget

| Stage | Model Tier | Input Tokens | Output Tokens | Total |
|-------|-----------|-------------|---------------|-------|
| 1. Fact Extraction | N/A (Deterministic) + cheap | 8,200 | 3,000 | 11,200 |
| 2. Entity & Party Extraction | N/A (NER) + cheap | 9,000 | 2,000 | 11,000 |
| 3. Financial Analysis | Deterministic + mid | 5,000 | 3,000 | 8,000 |
| 4. Incentive Analysis | Mid | 7,500 | 3,000 | 10,500 |
| 5. Market Context | Mid | 6,500 | 2,500 | 9,000 |
| 6. Thesis Generation | Mid | 15,500 | 3,000 | 18,500 |
| 7. Article Architecture | Cheap-to-mid | 6,500 | 2,000 | 8,500 |
| 8. Article Outline | Mid | 25,500 | 4,000 | 29,500 |
| 9. Drafting | Premium | 20,000 | 5,000 | 25,000 |
| 10. Financial Review | Cheap-to-mid | 12,000 | 2,000 | 14,000 |
| 11. Editorial Review | Mid | 14,000 | 5,000 | 19,000 |
| 12. Fact Verification | Deterministic + cheap | 10,000 | 3,000 | 13,000 |
| 13. Final Revision | Premium | 18,000 | 6,000 | 24,000 |
| 14. Headline Generation | Mid | 7,500 | 1,500 | 9,000 |
| 15. Metadata Generation | Cheap | 7,000 | 1,500 | 8,500 |
| **Total** | | **172,200** | **46,500** | **218,700** |

### Cost by Model Tier

| Tier | Tokens | Models |
|------|--------|--------|
| Deterministic (zero LLM cost) | ~20,000 | Regex, NER, arithmetic |
| Cheap | ~40,000 | DeepSeek-V3, Claude Haiku |
| Mid | ~95,000 | Claude Sonnet, GPT-4o |
| Premium | ~49,000 | Claude Opus, DeepSeek-R1 |

### Cost Optimization Notes

- Caching reduces effective cost for repeat stories or retries by 60–80%.
- Stages 1–2 are largely deterministic; LLM cost only applies to ambiguous extraction.
- Premium model cost (~49K tokens) is 22% of the total budget but produces 100% of the prose.
- Per-article API cost estimate: $0.80–$1.50 depending on model provider and caching hit rate.

---

## 21. Implementation Notes

### 21.1 Current Coverage in editorial_pipeline.py

The current `EditorialPipeline` class implements a subset of these stages: analytical brief generation (which encompasses several reasoning stages in one call), prompt selection, drafting placeholder, and review stage placeholders. The 15-stage architecture extends this to full decomposition.

### 21.2 Migration Path

1. **Phase 1:** Refactor the Analytical Brief to produce the structured outputs of Stages 1–8 as separate, cacheable objects while preserving the existing `build_analytical_brief()` interface.
2. **Phase 2:** Implement Stages 10–12 as parallel review calls that feed into the existing revision flow.
3. **Phase 3:** Split Stage 9 (drafting) into section-by-section calls with voice injection.
4. **Phase 4:** Implement Stages 14–15 for headline and metadata separation from the main drafting call.

### 21.3 Model Router Integration

Stage model selection is handled by `model_router.py`. Each stage registers its model preference and the router dispatches based on availability, cost, and rate limits:

```python
STAGE_MODEL_MAP = {
    "fact_extraction": "deepseek-v3",
    "entity_extraction": "deepseek-v3",
    "financial_analysis": "claude-sonnet-4-20250514",
    "incentive_analysis": "claude-sonnet-4-20250514",
    "market_context": "claude-sonnet-4-20250514",
    "thesis_generation": "claude-sonnet-4-20250514",
    "article_architecture": "deepseek-v3",
    "article_outline": "claude-sonnet-4-20250514",
    "drafting": "claude-opus-4-20250514",
    "financial_review": "deepseek-v3",
    "editorial_review": "claude-sonnet-4-20250514",
    "fact_verification": "deepseek-v3",
    "final_revision": "claude-opus-4-20250514",
    "headline_generation": "claude-sonnet-4-20250514",
    "metadata_generation": "deepseek-v3",
}
```

### 21.4 Checkpoint System

Every stage writes its output to the checkpoint system (`checkpoint.py`). If the pipeline is interrupted, it resumes from the last completed stage. No stage re-executes if its inputs haven't changed and its previous output is still valid.

### 21.5 Human-in-the-Loop Integration

For Tier 1 stories (must-cover), the pipeline pauses at two gates:

- **Gate A (after Stage 6):** Human editor reviews the thesis before the architecture and outline are built. This is the most cost-effective intervention point — correcting the thesis before drafting avoids expensive rework.
- **Gate B (after Stage 13):** Human editor reviews the final article before headline and metadata are generated. This allows quick approval or targeted revision before publication.

For Tier 2 and Tier 3 stories, the pipeline runs fully automated with human spot-checking.

### 21.6 Quality Gates Summary

| Gate | After Stage | Condition | Action on Failure |
|------|------------|-----------|-------------------|
| Fact Coverage | 1 | < 15 facts extracted | Abort; insufficient source material |
| Financial Depth | 3 | < 3 reported + calculated metrics | Downgrade to Tier 3; simplified article |
| Thesis Quality | 6 | Composite thesis score < 6.0 | Flag for human review; regenerate candidates |
| Draft Quality | 9 | < 500 words or > 70% fact deviation | Return to outline (Stage 8) |
| Financial Accuracy | 10 | Financial score < 7.0 | Force revision of financial passages |
| Editorial Score | 11 | Overall score < 7.0 or any dimension below threshold | Return for revision (Stage 13) |
| Fact Verification | 12 | Verification rate < 85% | Flag unsupported claims; human review if > 5 critical flags |
| Final Score | 13 | Overall score < 7.0 | Abort; do not publish |
