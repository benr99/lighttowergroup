# The Light Tower Analytical Brief Schema

**Document:** 07-Analytical-Brief-Schema
**Date:** July 30, 2026
**Status:** Authoritative Schema — Required Pre-Writing Reasoning Output

---

## Table of Contents

1. [Purpose and Philosophy](#1-purpose-and-philosophy)
2. [Mandatory Fields (A-L)](#2-mandatory-fields-a-l)
3. [Field A: Event Summary](#3-field-a-event-summary)
4. [Field B: Parties and Incentives](#4-field-b-parties-and-incentives)
5. [Field C: Transaction Economics](#5-field-c-transaction-economics)
6. [Field D: Market Context](#6-field-d-market-context)
7. [Field E: Central Financial Question](#7-field-e-central-financial-question)
8. [Field F: Core Tension](#8-field-f-core-tension)
9. [Field G: Thesis](#9-field-g-thesis)
10. [Field H: Counterargument](#10-field-h-counterargument)
11. [Field I: Unknowns](#11-field-i-unknowns)
12. [Field J: Reader Relevance](#12-field-j-reader-relevance)
13. [Field K: Article Architecture](#13-field-k-article-architecture)
14. [Field L: Article Depth](#14-field-l-article-depth)
15. [Field M: Key Numbers to Interpret](#15-field-m-key-numbers-to-interpret)
16. [Sector-Specific Analytical Framework Mapping](#16-sector-specific-analytical-framework-mapping)
17. [Brief Output Format (JSON Schema)](#17-brief-output-format-json-schema)
18. [Brief Production Rules](#18-brief-production-rules)
19. [Quality Standards and Rejection Criteria](#19-quality-standards-and-rejection-criteria)
20. [Integration with Scoring and Audit](#20-integration-with-scoring-and-audit)
21. [Examples by Depth and Sector](#21-examples-by-depth-and-sector)

---

## 1. Purpose and Philosophy

### 1.1 The Core Principle

Every selected story must produce an Analytical Brief before drafting begins. The brief is a structured reasoning document — not prose, not an outline. It forces the system to understand the story before writing about it. An article without a brief is an article without a foundation.

### 1.2 Why a Structured Brief Exists

The brief serves five functions:

1. **Reasoning Capture.** Forces the system to articulate what it knows, what it infers, what it assumes, and what it cannot determine before it starts writing. This prevents the drafting model from generating plausible-sounding but ungrounded analysis.
2. **Consistency Enforcement.** By requiring every article to answer the same structured questions, the brief ensures that the editorial lens — financial, institutional, incentive-driven — is applied uniformly across all seven sectors.
3. **Review Anchor.** The Financial Review prompt (Stage 10) and Editorial Review prompt (Stage 11) compare the draft against the brief. Any claim in the article that contradicts the brief, exceeds what the brief supports, or introduces reasoning not present in the brief is flagged.
4. **Audit Trail.** Each brief is logged with the article manifest. When an article is questioned, retracted, or revised, the brief provides the reasoning that produced it.
5. **Editorial Onboarding.** A human editor can read the brief and understand the article's analytical framework in under 90 seconds without reading the full article.

### 1.3 Design Principles

1. **Structured Over Narrative.** The brief is a reasoning scaffold, not a mini-article. Every field has a bounded answer format. The brief's quality is measured by specificity, not prose.
2. **Source-Grounded.** Every claim in the brief must trace to a specific source, be marked as an inference, or be flagged as unknown. The brief does not permit unsupported assertions.
3. **Falsifiable.** A good brief makes claims that could be proven wrong. A bad brief makes claims that are always true. The thesis field (G) must be specific enough that evidence could disprove it.
4. **Financial First.** The brief centers on transaction economics, incentives, and market context. Sector dynamics matter, but they serve the financial analysis — not the reverse.
5. **Bounded Output.** Every field has a word limit, a format constraint, or both. The brief is not an opportunity for unbounded LLM generation.

---

## 2. Mandatory Fields (A-L)

The Analytical Brief consists of twelve mandatory fields (A through L) plus one synthesis field (M). Every field must be completed for every article, regardless of depth or sector. Fields may not be left blank, skipped, or replaced with generic placeholder text.

| Field | Name | Format Constraint | Word Limit |
|-------|------|-------------------|------------|
| A | Event Summary | Structured prose | 50–100 words |
| B | Parties and Incentives | Table (one row per party) | 40–80 words per party |
| C | Transaction Economics | Numbered list with labels | No limit; bounded by available data |
| D | Market Context | Structured prose with bullet points | 100–200 words |
| E | Central Financial Question | Single sentence, interrogative form | 15–40 words |
| F | Core Tension | Single sentence, declarative form | 15–40 words |
| G | Thesis | 1–3 sentences, declarative form | 30–100 words |
| H | Counterargument | 1–3 sentences | 30–80 words |
| I | Unknowns | Bulleted list | 3–10 items |
| J | Reader Relevance | Bulleted list by audience segment | 30–80 words |
| K | Article Architecture | Enum selection + justification | Enum + 15–30 words |
| L | Article Depth | Enum selection + justification | Enum + 15–30 words |
| M | Key Numbers to Interpret | Numbered list | 3–5 items, 20–40 words each |

**Failure Conditions:**
- Any field left blank → brief rejected, article cannot proceed to drafting
- Any field filled with generic text (e.g., "The parties acted in their best interest") → brief rejected
- Thesis field contains a statement that is unfalsifiable → brief returned for revision
- Event Summary contains no specific named entities, dates, or amounts → brief returned for revision
- Core Tension does not identify two opposing forces → brief returned for revision

---

## 3. Field A: Event Summary

### 3.1 Purpose

The Event Summary distills the story's factual core into 50–100 words. It is the anchor against which all subsequent analysis is checked. If the article makes claims that cannot be traced to the Event Summary, those claims are unsupported.

### 3.2 Required Elements

Every Event Summary must answer four sub-questions. The output is free text, but each sub-question must be addressable:

1. **What happened?** State the confirmed facts. Include dates, amounts, entities, and locations.
2. **What is the primary source?** Name the source and state its authority. Examples: "SEC 8-K filing dated June 12, 2025," "Blackstone press release," "FDIC enforcement order," "FOMC statement."
3. **What corroborating sources exist?** List at least one independent source that confirms the primary facts. If none exists, flag this explicitly.
4. **What remains unclear or unconfirmed?** Identify specific gaps in the factual record. Do not write "details are unknown" — write "purchase price, financing terms, and closing timeline are not disclosed."

### 3.3 Format

```
Event: [Prose summary of confirmed facts, 50–100 words]
Primary Source: [Source name, date, authority type]
Corroboration: [At least one corroborating source, or "NONE — single-source story"]
Unconfirmed: [Specific unresolved questions]
```

### 3.4 Quality Standards

| Score | Description |
|-------|-------------|
| 10 | All four sub-questions answered with specificity; facts are dated and quantified; sources are named with authority levels; unconfirmed items are enumerated as specific unknowns |
| 7 | All four sub-questions answered; facts are specific but some lack dates or sources; unconfirmed items identified |
| 5 | Facts present but vague; source named but authority not stated; unconfirmed items generic |
| 3 | Events described but no dates, amounts, or entities named |
| 1 | No usable factual content; pure summary without specificity |

### 3.5 Example

```
Event: KKR acquired a 49% stake in a 2.4 GW renewable energy portfolio
from NextEra Energy Partners for $2.8 billion, announced March 24, 2025.
The portfolio spans 1,100 wind turbines and 3.5 million solar panels
across 12 states. The transaction implies a $5.7 billion enterprise
value for the full portfolio.

Primary Source: NextEra Energy Partners press release, March 24, 2025
Corroboration: KKR 8-K filing dated March 25, 2025; Wall Street Journal
report March 24, 2025
Unconfirmed: Debt financing structure, KKR's equity contribution amount,
precise cap rate on the portfolio, closing conditions
```

---

## 4. Field B: Parties and Incentives

### 4.1 Purpose

Every transaction, policy change, regulatory action, or market event involves parties with distinct incentives. The Parties and Incentives field forces identification of each party's position, motivations, and constraints. This is the foundation for the Incentive Analysis scoring dimension (Score #5).

### 4.2 Required Fields Per Party

For each party, the brief must answer six questions:

| Sub-Field | Question | Format |
|-----------|----------|--------|
| **Identity** | Who is the party? | Real name from sources (not "the buyer") |
| **Gain** | What do they appear to gain? | Specific benefit — money, control, market access, liability reduction, regulatory relief |
| **Risk** | What risk are they accepting? | Financial, regulatory, reputational, operational risk |
| **Timing Motivation** | What may be motivating the timing? | Why now and not six months ago or six months from now? |
| **Constraint** | What constraint are they operating under? | Capital, regulatory, timeline, competitive, political constraint |
| **Clock** | What is their time horizon? | Days, months, quarters, years — and why |

### 4.3 Party Types

At minimum, the brief must identify parties in the following roles (where applicable):

- **Buyer / Acquirer**
- **Seller / Divestor**
- **Lender / Financing Provider**
- **Sponsor / General Partner**
- **Government / Regulator**
- **Operator / Manager**
- **Tenant / Offtaker**
- **Advisor / Intermediary**

For non-transaction stories (regulatory actions, policy changes, macro events), "parties" are the entities affected by or driving the event.

### 4.4 Output Format

```json
{
  "parties": [
    {
      "name": "KKR",
      "role": "Buyer / Acquirer",
      "gain": "Acquires 49% of 2.4 GW operating renewable portfolio at a price
               that represents a discount to replacement cost; gains immediate
               cash flow from long-term PPAs with investment-grade offtakers",
      "risk": "PPA renewal risk as contracts expire over next 5-10 years;
               technology obsolescence risk for older wind turbines;
               regulatory risk if IRA tax credits are modified",
      "timing_motivation": "NextEra Energy Partners under pressure to simplify
                            structure and reduce leverage after yieldco model
                            fell out of favor; KKR infrastructure fund in
                            deployment period with dry powder to commit",
      "constraint": "Infrastructure fund has defined investment period (3-4
                     years remaining); must deploy at scale to justify fund
                     economics; competing with Brookfield, Blackstone for
                     similar assets",
      "clock": "Years — infrastructure fund holds assets 7-12 years"
    },
    {
      "name": "NextEra Energy Partners",
      "role": "Seller / Divestor",
      "gain": "Receives $2.8 billion in cash, which can be used to reduce
               leverage, buy out convertible equity portfolio financings,
               and simplify corporate structure; improves cost of capital",
      "risk": "Loses a large cash-flow-generating portfolio; must redeploy
               or return capital; future growth trajectory depends on
               remaining asset base",
      "timing_motivation": "Yieldco model under sustained pressure from
                            rising interest rates; convertible equity
                            financings maturing in 2025-2027 create
                            refinancing risk; simplification imperative",
      "constraint": "Must maintain dividend; must satisfy convertible equity
                     holders; limited acquisition capacity until balance
                     sheet is repaired",
      "clock": "Quarters — convertible equity maturities are fixed dates"
    }
  ]
}
```

### 4.5 Quality Standards

| Score | Description |
|-------|-------------|
| 10 | All six sub-fields completed for every major party; answers are specific with named constraints, quantified risks, and dated motivations; party roles correctly identified |
| 7 | All major parties identified; most sub-fields completed; some answers generic |
| 5 | Parties listed but sub-fields incomplete or generic; "the buyer benefits from the acquisition" without specifics |
| 1 | No party analysis or parties misidentified |

---

## 5. Field C: Transaction Economics

### 5.1 Purpose

Extract every available number from the source material. Mark each number as REPORTED (appearing in a source document) or CALCULATED (derived from reported numbers). This field feeds the Use of Numbers scoring dimension (Score #6) and guarantees the article contains interpreted numbers, not just listed numbers.

### 5.2 Required Number Categories

The brief must attempt to extract numbers in every relevant category. If a category does not apply to the story (e.g., no tax incentive in a regulatory action), mark it N/A with a brief justification. If the number is unavailable but would be relevant, mark it as UNAVAILABLE.

| Category | Applicability | Description |
|----------|---------------|-------------|
| Purchase price / deal value | Transaction stories | Total consideration including assumed debt |
| Financing amount and structure | Transaction stories | Debt quantum, type (term loan, bridge, CMBS, private placement), maturity, rate |
| Equity contribution | Transaction stories | Sponsor equity, co-invest, LP co-invest |
| Implied leverage | Transaction stories | Debt / total capitalization or debt / EBITDA |
| Implied valuation multiple | Transaction stories | EV / EBITDA, price / unit, price / MW |
| Price per unit / sq ft / MW | Asset transactions | Unit-level pricing |
| Cap rate or yield | Income-producing assets | NOI / purchase price (going-in cap rate) |
| Prior sale price / basis | Asset transactions | What the seller paid, when |
| Fund size / target / hard cap | PE / fund stories | Fundraising metrics |
| Megawatts / acreage / unit count | Energy / DC / CRE | Physical scale |
| Tax incentive or subsidy value | Energy / development | ITC, PTC, LIHTC, TIF, opportunity zone |
| Replacement cost estimate | Development / DC / energy | What it would cost to build today |
| Development timeline | Development stories | Months to COD, entitlement timeline |
| Interest rate / spread | Financing / macro stories | Specific rate, index + spread |
| Regulatory capital impact | Banking stories | CET1 impact, RWA change, TLAC requirement |

### 5.3 Output Format

Each number must be presented with:

```
[NUMBER] — [What it represents]
  Source: REPORTED from [source] or CALCULATED as [formula]
  Context: [One sentence on what this number means in context]
  Confidence: HIGH / MEDIUM / LOW / ESTIMATED
```

### 5.4 Example

```
- $5.7 billion — Implied enterprise value of full portfolio
  Source: CALCULATED as $2.8 billion / 0.49 (49% stake)
  Context: Values the portfolio at approximately $2,375/kW, which is
           below the estimated $2,800-3,200/kW replacement cost for
           comparable wind and solar assets
  Confidence: HIGH — arithmetic from reported numbers

- $2.8 billion — Cash consideration to NextEra Energy Partners
  Source: REPORTED from NextEra Energy Partners press release
  Context: Represents approximately 2.4x the portfolio's annual
           cash available for distribution, implying a going-in yield
           of roughly 8-9% for KKR
  Confidence: HIGH — from official press release

- 2.4 GW — Total operating capacity of portfolio
  Source: REPORTED from NextEra Energy Partners press release
  Context: Makes this one of the largest single renewable portfolio
           transactions in the U.S.; portfolio alone represents
           approximately 0.2% of total U.S. installed generating capacity
  Confidence: HIGH — from official press release

- Financing amount — UNAVAILABLE
  Context: Neither party disclosed debt financing structure or amount.
           KKR typically finances infrastructure acquisitions with
           40-60% debt at the asset level. This is an important unknown
           for assessing KKR's true cash-on-cash return.
```

### 5.5 Quality Standards

| Score | Description |
|-------|-------------|
| 10 | All available numbers extracted and properly sourced; calculated numbers show formula; unavailable numbers flagged with explanation; all numbers contextualized |
| 7 | Key numbers extracted; most sourced correctly; some context missing |
| 5 | Numbers listed without source labels or context; calculated numbers not distinguished from reported |
| 1 | Missing key numbers that are clearly available in the source |

---

## 6. Field D: Market Context

### 6.1 Purpose

Place the event in its correct market context. This is not generic background — it is specific conditions, comparable transactions, and regulatory dynamics that make this story interpretable. This field feeds the Market Context scoring dimension (Score #7).

### 6.2 Required Sub-Fields

1. **Interest Rate and Credit Environment.** What are current conditions in the relevant credit market? Include specific rates, spreads, or indices where available.
2. **Comparable Transactions.** List 2-5 recent comparable transactions with dates, parties, values, and what makes them comparable. If no comparables are available, state why.
3. **Sector Supply and Demand Fundamentals.** What is the supply/demand balance in the relevant market? Is capacity growing, shrinking, or flat? Are rents/prices rising or falling?
4. **Regulatory Environment.** What regulatory conditions, rule changes, or policy proposals affect this asset class, transaction type, or sector?
5. **Timeliness Factor.** What has changed recently that makes this story worth publishing now? Why was this not equally relevant six months ago?

### 6.3 Output Format

```
Interest Rate / Credit Environment:
[2-4 sentences on current conditions with specific rates or indices]

Comparable Transactions:
- [Transaction description, date, value, parties, key similarity]
- [Transaction description, date, value, parties, key similarity]
- [Transaction description, date, value, parties, key similarity]

Sector Supply and Demand:
[2-4 sentences on fundamentals]

Regulatory Environment:
[2-4 sentences on relevant regulation/policy]

Timeliness Factor:
[1-2 sentences on why this story matters now]
```

### 6.4 Example

```
Interest Rate / Credit Environment:
The 10-year U.S. Treasury yield is approximately 4.25% as of March 2025,
down from a peak of 4.98% in October 2023. Investment-grade infrastructure
debt is pricing at approximately 150-200 bps over Treasuries, implying
all-in borrowing costs of 5.75-6.25%. Rate expectations have shifted from
six cuts in 2024 (predicted in January 2024) to two cuts expected in 2025.

Comparable Transactions:
- Brookfield acquired 51% of an 845 MW U.S. solar portfolio from
  Duke Energy for $1.3 billion (October 2024), implying $3,000/kW
- Blackstone acquired 100% of Trystar (distributed energy solutions)
  in December 2024 for an undisclosed amount
- Energy Capital Partners acquired 100% of Atlantica Sustainable
  Infrastructure for $2.6 billion (January 2025), implying ~12x EBITDA

Sector Supply and Demand:
U.S. renewable energy capacity additions reached 47 GW in 2024, a record.
Demand from data centers, manufacturing reshoring, and electrification
is projected to require 35-50 GW of new capacity annually through 2030.
Competition for operating renewable assets is intense among infrastructure
funds seeking yield in a higher-rate environment.

Regulatory Environment:
The Inflation Reduction Act's transferability provisions (enabling sale
of tax credits) became effective in 2024, increasing the pool of buyers
for renewable assets. The November 2024 election outcome introduces
uncertainty about potential IRA modifications. Treasury guidance on
prevailing wage and apprenticeship requirements finalized in June 2024.

Timeliness Factor:
The NextEra-KKR deal is the first major yieldco simplification transaction
of 2025 and tests whether institutional infrastructure capital will absorb
renewable assets at scale as the yieldco model unwinds.
```

### 6.5 Quality Standards

| Score | Description |
|-------|-------------|
| 10 | All five sub-fields completed with specific, dated, quantified context; comparables are genuinely comparable; timeliness factor is specific |
| 7 | Most sub-fields completed; comparables provided but comparison rationale weak; timeliness factor present |
| 5 | Generic market context ("the market is growing") without specifics; no comparables |
| 1 | No market context or factually incorrect context |

---

## 7. Field E: Central Financial Question

### 7.1 Purpose

State the ONE question this article must answer. The Central Financial Question constrains the entire article. Every paragraph should serve the answer to this question. If the article does not answer the Central Financial Question, the article has failed.

### 7.2 Required Form

- Must be a single sentence in interrogative form
- Must be specific to this story — not a generic question that could apply to any transaction
- Must be answerable from available evidence
- Must be a financial or economic question, not a narrative or descriptive question

### 7.3 Examples

**Strong (specific, answerable, financial):**
- "Is KKR acquiring a durable cash-flowing asset at a temporary discount caused by yieldco financing distress, or is it buying assets with hidden recontracting risk at the wrong point in the rate cycle?"
- "Does the financing structure reveal how difficult conventional construction debt has become for data center developers without hyperscaler pre-leasing?"
- "Is the bank's decision to exit CRE lending a rational response to concentration limits, or a signal that credit losses in office are worse than disclosed?"

**Weak (generic, unfalsifiable, non-financial):**
- "What happened in this transaction?" (too generic)
- "Is this a good deal?" (not specific enough)
- "How will the market react?" (unanswerable, speculative)

### 7.4 Quality Standards

| Score | Description |
|-------|-------------|
| 10 | Single, specific, answerable financial question that genuinely drives the analysis; question could not apply to a different story |
| 7 | Reasonable financial question but somewhat generic or partially answerable |
| 5 | Question is narrative ("what happened") or speculative ("what will happen") rather than analytical |
| 1 | No question or question is meaningless |

---

## 8. Field F: Core Tension

### 8.1 Purpose

State the central tension in one declarative sentence. The tension is the conflict between two opposing forces. This tension drives the article's narrative structure and determines which story architecture (K) is appropriate.

### 8.2 Required Form

- Must be exactly one declarative sentence
- Must identify two opposing forces
- Must be specific to this story
- Must be a genuine tension — the two forces must be in actual conflict, not just "two things that exist"

### 8.3 Tension Archetypes

The Core Tension should fit one of these archetypes. If it does not, the story may lack a genuine conflict and the Thesis (G) will be weak:

| Archetype | Pattern | Example |
|-----------|---------|---------|
| Price vs. Value | The price paid reflects X, but the underlying asset value depends on Y | "The portfolio trades at a 30% discount to replacement cost, but the PPA renewal schedule means half the cash flow reprices within five years." |
| Risk vs. Yield | The yield appears attractive under X assumption, but the risk is priced for Y scenario | "The 8.5% going-in yield compensates for visible risks, but does not price the possibility that renewable offtakers demand contract restructuring as new supply comes online." |
| Growth vs. Leverage | The growth story requires X, but the financing capacity depends on Y | "The development pipeline requires $4 billion in new equity, but the current fund has only $1.2 billion of dry powder remaining." |
| Liquidity vs. Duration | The asset is liquid under X conditions, but the holding period requires surviving Y | "The debt fund offers quarterly redemptions, but the underlying loans have 5-7 year maturities with limited secondary market liquidity." |
| Buyer Confidence vs. Seller Necessity | The buyer believes X, but the seller's motivation is Y | "KKR sees a long-term infrastructure return, but NextEra Energy Partners is selling because convertible equity maturities forced the decision — not because the price was optimal." |
| Policy Intent vs. Market Consequence | The policy aims to do X, but the market response is producing Y | "The IRA's transferability rules were designed to broaden the tax equity market, but the resulting capital flows are concentrating renewable ownership among the five largest infrastructure funds." |

### 8.4 Quality Standards

| Score | Description |
|-------|-------------|
| 10 | Identifies two specific, opposing forces; tension is real and story-specific; sentence is clear and declarative |
| 7 | Tension identified but one side is vague or the conflict is overstated |
| 5 | Apparent tension but not genuinely in conflict; or generic tension |
| 1 | No tension identified |

---

## 9. Field G: Thesis

### 9.1 Purpose

State the article's most defensible claim in 1-3 sentences. The thesis is what the article argues. It is not a summary of the event, a list of facts, or a prediction. It is a claim that evidence supports — and that evidence could (in principle) disprove.

### 9.2 Required Properties

A good thesis is:
- **Specific.** Refers to named entities, specific numbers, and bounded claims.
- **Bounded.** Does not overclaim. "The transaction signals growing institutional appetite for renewables" is bounded. "This deal will transform the energy market" is not.
- **Source-Grounded.** Every element of the thesis traces to at least one source in the brief.
- **Falsifiable.** A reader should be able to say "this thesis would be wrong if X were true," where X is a specified condition.
- **Analytical.** Goes beyond factual restatement. "KKR bought a portfolio" is not a thesis. "KKR's acquisition reveals that yieldco distress is creating a secondary market for renewable assets at prices below replacement cost" is a thesis.

### 9.3 Examples

**Strong:**
"The KKR-NextEra transaction is the first large-scale evidence that the yieldco model's collapse is creating a discount-to-replacement-cost entry point for institutional infrastructure capital — but the discount exists because the assets carry PPA renewal risk that the seller's corporate structure could no longer manage, not because the market mispriced the assets."

**Weak:**
"KKR made a smart acquisition of renewable assets." (vague, unfalsifiable, no analysis)

**Weak:**
"The renewable energy market is growing." (obvious, not specific to this story)

### 9.4 Quality Standards

| Score | Description |
|-------|-------------|
| 10 | Specific, bounded, source-grounded, falsifiable, analytical thesis in 1-3 clear sentences |
| 7 | Reasonable thesis but somewhat vague, overclaims, or lacks falsifiability |
| 5 | Thesis is vague, obvious, or primarily factual rather than analytical |
| 1 | No thesis or thesis is factually wrong |

---

## 10. Field H: Counterargument

### 10.1 Purpose

State the most reasonable alternative interpretation of the event. This is not a straw man. It must be an interpretation that a knowledgeable market participant could reasonably hold. The counterargument serves three functions: (1) it tests whether the thesis is genuinely debatable, (2) it identifies the evidence that would be most damaging to the thesis, and (3) it signals to the reader that the analysis has considered alternative views.

### 10.2 Required Form

- 1-3 sentences
- Must present a genuine alternative to the thesis
- Must identify the specific fact or assumption that, if different, would favor the counterargument
- Must state what would make the thesis wrong

### 10.3 Example

```
Counterargument: KKR is not acquiring assets at a genuine discount —
the 8-9% going-in yield appropriately prices the PPA renewal risk,
transmission congestion costs in certain markets, and the capital
expenditure required to repower aging wind turbines. If PPA renewal
rates come in 20-30% below current contract prices (consistent with
recent solar PPA trends in ERCOT and CAISO), the implied return falls
to 5-6% — below KKR's reported infrastructure target return of 8-10%.

What would make the thesis wrong: Evidence that PPA renewal rates in
the portfolio's specific markets (MISO, SPP, PJM) are trending
significantly below current contract prices, or that KKR's equity
check is larger than reported (implying a higher purchase price).
```

### 10.4 Quality Standards

| Score | Description |
|-------|-------------|
| 10 | Counterargument is genuinely reasonable, identifies specific conditions that would favor it, and states what would invalidate the thesis |
| 7 | Reasonable counterargument but lacks specificity about what evidence would support it |
| 5 | Straw man — counterargument is obviously wrong or misrepresents the thesis |
| 1 | No counterargument |

---

## 11. Field I: Unknowns

### 11.1 Purpose

List what cannot be known from available sources. This is an honesty mechanism: by enumerating what the article cannot claim to know, it prevents the drafting model from fabricating certainty. This field feeds the Intellectual Honesty scoring dimension (Score #12).

### 11.2 Required Categories

Unknowns must be organized into three categories:

1. **Unavailable Facts.** Information the source does not contain. Example: "Neither party disclosed the debt financing structure."
2. **Uncalculated Metrics.** Numbers that could be calculated if additional data were available. Example: "Going-in cap rate cannot be calculated because NOI was not disclosed."
3. **Unverified Assumptions.** Inferences the brief makes that have not been confirmed. Example: "Assumed KKR is using its Global Infrastructure Investors V fund ($17 billion target) — this has not been confirmed by KKR."

### 11.3 Output Format

```
Unavailable Facts:
- [Specific fact not in any source]
- [Specific fact not in any source]

Uncalculated Metrics:
- [Metric that cannot be computed]
- [Metric that cannot be computed]

Unverified Assumptions:
- [Assumption the analysis makes]
- [Assumption the analysis makes]
```

### 11.4 Quality Standards

| Score | Description |
|-------|-------------|
| 10 | At least 3 items in each relevant category; unknowns are specific and would affect the analysis if resolved; assumptions explicitly flagged |
| 7 | Most categories covered; unknowns identified but some important ones missed |
| 5 | Generic unknowns ("market conditions may change"); important unverified assumptions not flagged |
| 1 | No unknowns listed or claims certainty where sources are silent |

---

## 12. Field J: Reader Relevance

### 12.1 Purpose

State why specific audience segments should care about this story and what they should do next. This is not marketing copy — it is a disciplined articulation of the story's utility to each relevant constituency. This field feeds the Reader Utility scoring dimension (Score #13).

### 12.2 Audience Segments

The brief must address at least three of the following segments (choose those most relevant to the story):

| Segment | Description | What This Field Should Tell Them |
|---------|-------------|----------------------------------|
| **CRE Investor** | Institutional real estate equity investor | What signal does this send about pricing, cap rates, or market direction? What should they reprice? |
| **Lender / Credit** | Bank, debt fund, CMBS investor | What does this reveal about credit conditions, spreads, or underwriting standards? |
| **PE Professional** | Private equity GP or LP | What does this reveal about deal flow, entry multiples, or exit environments? |
| **Developer** | Real estate, energy, or infrastructure developer | What does this reveal about construction costs, entitlement risk, or offtake markets? |
| **Operator** | Asset or portfolio operator | What does this reveal about operational benchmarks, cost structures, or revenue trends? |
| **Policymaker** | Federal, state, or local government | What does this reveal about policy effectiveness, unintended consequences, or market responses to regulation? |
| **Data Center Investor/Operator** | DC developer, hyperscaler, DC REIT | What does this reveal about power procurement, land availability, or tenant demand? |
| **Energy Investor** | Renewable developer, IPP, infrastructure fund | What does this reveal about PPA pricing, development yields, or tax equity markets? |
| **Banking Professional** | Bank analyst, risk manager, regulator | What does this reveal about loan books, deposit costs, or regulatory capital? |
| **Macro Observer** | Economist, strategist, allocator | What does this reveal about the macro environment? |

### 12.3 Output Format

```
[Audience Segment 1]: [What they should take away and what to test/question/watch next]
[Audience Segment 2]: [What they should take away and what to test/question/watch next]
[Audience Segment 3]: [What they should take away and what to test/question/watch next]
```

### 12.4 Quality Standards

| Score | Description |
|-------|-------------|
| 10 | At least three audience segments addressed with specific, actionable takeaways; each takeaway is specific to this story |
| 7 | At least two segments addressed; takeaways are relevant but somewhat generic |
| 5 | Audience segments mentioned but takeaways are vague ("investors should watch this space") |
| 1 | No reader relevance or completely generic |

---

## 13. Field K: Article Architecture

### 13.1 Purpose

Select the story structure that best fits the Central Financial Question (E), Core Tension (F), and Thesis (G). The architecture determines the article's narrative organization, not its content. Different architectures answer different types of questions and serve different reader needs.

### 13.2 The Six Story Architectures

#### Architecture 1: The Hidden Bet

**When to use:** The story is about an assumption embedded in a transaction, strategy, or policy that is not obvious from the headline. The article reveals the bet and assesses whether it is well-calibrated.

**Structure:**
1. Open with the visible transaction/event
2. Reveal the hidden assumption or bet
3. Show what would need to be true for the bet to pay off
4. Show what the market is pricing (and what it's not)
5. Conclude with what to watch to know if the bet is paying off

**Example stories:** A REIT acquiring office assets in a declining market (the hidden bet: office utilization will recover to 80%+); a bank expanding CRE lending while peers retreat (the hidden bet: credit losses are cyclical, not structural).

#### Architecture 2: The Constraint

**When to use:** The story is about a binding constraint — capital, land, power, permitting, talent, regulation — that is shaping market outcomes. The constraint, not the transaction, is the story.

**Structure:**
1. Open with a specific transaction or market outcome
2. Reveal the constraint that produced it
3. Show how the constraint affects different parties differently
4. Show what would release the constraint (and what wouldn't)
5. Conclude with what changes in the constraint to watch

**Example stories:** A data center developer paying 3x market rate for land with power access (constraint: transmission interconnection queue); a PE firm sitting on $5 billion of dry powder but unable to deploy (constraint: bid-ask spread between buyers and sellers).

#### Architecture 3: The Price Signal

**When to use:** The story is about what a specific price, spread, or valuation tells us about market conditions. The price is the story.

**Structure:**
1. Open with the specific price/valuation and why it matters
2. Show what the price implies when decomposed
3. Compare to historical norms, peers, and replacements cost
4. Show what market participants are doing in response
5. Conclude with what would need to happen for the price to change

**Example stories:** A CRE portfolio trading at a 9% cap rate when the 10-year is at 4.25%; a renewable PPA signed at $28/MWh when the LCOE is $35/MWh; a bank loan trading at 85 cents on the dollar.

#### Architecture 4: The Incentive Conflict

**When to use:** The story is about parties whose incentives are misaligned — agent-principal problems, GP-LP conflicts, regulatory arbitrage, or moral hazard. The conflict produces the outcome.

**Structure:**
1. Open with the outcome that seems puzzling or suboptimal
2. Reveal whose incentives are misaligned and how
3. Show the structure that creates the conflict (contract, regulation, market convention)
4. Show who bears the cost of the conflict
5. Conclude with what would realign incentives

**Example stories:** A yieldco selling assets below replacement cost to satisfy near-term financing obligations (LP-shareholder conflict); a bank originating loans it immediately syndicates (originate-to-distribute vs. portfolio lender incentives).

#### Architecture 5: The Policy Consequence

**When to use:** The story is about a policy, regulation, or government action whose consequences — intended or unintended — are now visible in market data. The policy is the story.

**Structure:**
1. Open with the market outcome that reveals the policy consequence
2. Show what the policy was designed to do
3. Show what it actually did (with specific evidence)
4. Show who benefited and who was harmed
5. Conclude with what the policy response might be

**Example stories:** The IRA's transferability provisions concentrating renewable ownership; local zoning changes that redirected multifamily development from one submarket to another; bank capital rules that shifted CRE lending from banks to debt funds.

#### Architecture 6: The Market Turning Point

**When to use:** The story is about an inflection point — a transaction, data release, or event that marks the end of one market regime and the beginning of another. The evidence of the turn is the story.

**Structure:**
1. Open with the signal that suggests a turning point
2. Show what the prior regime looked like (with evidence)
3. Show what has changed and why it's durable, not noise
4. Show what hasn't changed (the counterargument to the turn)
5. Conclude with what to watch to confirm or refute the turn

**Example stories:** First office building to trade at a price that implies a new clearing level for the asset class; first bank to report rising CRE charge-offs after two years of benign credit; first quarter where data center absorption exceeds new supply by 2x.

### 13.3 Selection Logic

The prompt (Stage 7) selects the architecture by asking:

1. Is there a hidden assumption driving this story? → The Hidden Bet
2. Is a binding constraint producing market outcomes? → The Constraint
3. Is a specific price the most important signal? → The Price Signal
4. Is a misalignment of incentives producing puzzling outcomes? → The Incentive Conflict
5. Is a policy producing visible market consequences? → The Policy Consequence
6. Does this event mark a change in market regime? → The Market Turning Point

If multiple apply, select the primary one. If none clearly apply, the story may not be strong enough to write.

### 13.4 Output Format

```
Selected Architecture: [Architecture Name]
Justification: [1-2 sentences on why this architecture fits the story's
Central Financial Question, Core Tension, and Thesis]
```

---

## 14. Field L: Article Depth

### 14.1 Purpose

Select the appropriate article depth based on the story's complexity, available information, and audience need. This determines word count, analytical depth, and review requirements.

### 14.2 The Three Depth Tiers

| Depth | Word Count | When to Use | Review Requirements |
|-------|-----------|-------------|---------------------|
| **Brief** | 400–700 words | Straightforward announcement with one insight; story is significant but thin on available analysis; the event speaks for itself | Financial Review (Stage 10) optional; Editorial Review (Stage 11) optional; Fact Verification (Stage 12) required |
| **Standard** | 800–1,300 words | Meaningful transaction, policy change, or market development with sufficient information for multi-dimensional analysis; most articles | All 15 prompt stages required |
| **Deep** | 1,400–2,500 words | Major deal, structural market shift, complex capital structure, multi-party transaction, policy with far-reaching consequences; flagged as flagship content | All 15 prompt stages required; Financial Understanding minimum score 8; multiple human-review checkpoints |

### 14.3 Selection Criteria

**Choose Brief when:**
- The source contains one primary new fact
- The financial analysis can be completed in 2-3 sentences
- Only 1-2 parties have significant incentive analysis
- The thesis is straightforward but specific
- The story is worth covering but does not sustain 800+ words of analysis

**Choose Standard when:**
- The source contains multiple new facts or the event has multiple dimensions
- Financial analysis requires several numbers with interpretation
- Multiple parties have distinct incentives
- The thesis requires supporting evidence from 2+ angles
- The story sustains at least 800 words without padding

**Choose Deep when:**
- The transaction structure is complex (multiple tranches, earn-outs, contingent payments)
- The event has implications across multiple sectors
- The capital structure requires detailed explanation
- The policy or regulatory change has first-, second-, and third-order effects
- The story is a flagship piece that the publication leads with

### 14.4 Output Format

```
Selected Depth: [Brief / Standard / Deep]
Justification: [1-2 sentences on why this depth is appropriate]
Word Target: [Specific word count target, e.g., "~600 words" or "~1,200 words"]
```

---

## 15. Field M: Key Numbers to Interpret

### 15.1 Purpose

List 3-5 numbers that will anchor the analysis in the article. These are not just numbers that appear in the article — they are numbers whose interpretation carries the analytical weight of the piece. For each, state the number, what it represents, and what interpretation is defensible.

### 15.2 Output Format

```
1. [NUMBER] — [What it represents]
   Interpretation: [1-2 sentences on what this number means and why it matters]

2. [NUMBER] — [What it represents]
   Interpretation: [1-2 sentences on what this number means and why it matters]

3. [NUMBER] — [What it represents]
   Interpretation: [1-2 sentences on what this number means and why it matters]
```

### 15.3 Example

```
1. $2,375/kW — Implied acquisition price per installed kW of capacity
   Interpretation: This is 15-25% below the estimated $2,800-3,200/kW
   replacement cost for comparable wind and solar in the portfolio's
   markets. The discount exists because replacement cost assumes new
   assets with 30-year useful lives, while the portfolio's average
   asset age is 8 years with PPA maturities concentrated in 2028-2032.

2. 8-9% — Estimated going-in cash yield to KKR
   Interpretation: This is 375-475 bps above the 10-year Treasury yield.
   For comparison, infrastructure funds have targeted 8-10% net IRR
   historically. The yield compensates for PPA renewal risk and
   technology obsolescence, but if PPA renewal rates decline 20%,
   the yield compresses to 5-6% — below KKR's target.

3. $17 billion — KKR Global Infrastructure Investors V fund target
   Interpretation: At the time of the acquisition, KKR had reportedly
   deployed approximately 40% of the fund. The $2.8 billion equity
   check (estimated at 50% of purchase price, or $1.4 billion) would
   represent approximately 8% of the fund — a concentrated bet on
   renewable operating assets at scale.

4. 2028-2032 — Concentration window for PPA expirations in the portfolio
   Interpretation: The cash flow visibility is strong for the first
   3-7 years but declines sharply after 2028. KKR's 7-12 year hold
   period means it must manage through at least one full PPA renewal
   cycle. The outcome depends on power price forecasts, renewable
   penetration rates, and offtaker demand in MISO, SPP, and PJM.

5. 2.4x — Multiple of annual cash available for distribution represented
   by the purchase price
   Interpretation: This is below the 3-4x multiple at which comparable
   yieldco portfolios traded in 2019-2021. The compression reflects
   the market's repricing of yieldco equity (higher cost of capital),
   not a deterioration in asset quality. The question is whether 2.4x
   represents a floor or whether further compression is possible if
   the Federal Reserve does not cut rates as expected.
```

---

## 16. Sector-Specific Analytical Framework Mapping

### 16.1 Purpose

The Analytical Brief's fields are universal — they apply to all seven sectors. However, each sector has distinct analytical frameworks that shape how certain fields are completed. This section maps the brief's fields to the sector-specific frameworks defined in the editorial mandate.

### 16.2 CRE Transactions (Commercial Real Estate)

**Framework:** Price discovery through comparable transactions, cap rate analysis, replacement cost, debt market conditions.

| Brief Field | CRE-Specific Application |
|-------------|-------------------------|
| C: Transaction Economics | Cap rate, price per sq ft, price per unit, LTV, debt yield, replacement cost, prior sale price |
| D: Market Context | Submarket vacancy, absorption, pipeline, rent growth; CMBS issuance and spreads; bank CRE loan growth/contraction |
| E: Central Financial Question | Often about cap rate compression/expansion, debt availability, or basis reset |
| F: Core Tension | Frequently Price vs. Value (is the cap rate discounting risks correctly?) or Buyer Confidence vs. Seller Necessity (is the seller a forced seller?) |

**Key metrics to extract (Field C):** Cap rate (going-in and exit), price per sq ft, LTV, debt yield, DSCR, replacement cost, submarket vacancy, rent per sq ft vs. market, lease expiration schedule, tenant concentration.

### 16.3 Private Equity (PE)

**Framework:** Fund-level economics (deployment pace, DPI, TVPI, fund vintage pressure), GP-LP alignment, exit environment, leverage conditions.

| Brief Field | PE-Specific Application |
|-------------|------------------------|
| C: Transaction Economics | Fund size, target, hard cap, amount deployed, DPI, TVPI, entry multiple, leverage multiple |
| D: Market Context | M&A volume, IPO window, sponsor-to-sponsor deal volume, direct lending conditions, LP allocation trends |
| E: Central Financial Question | Often about deployment pressure, exit timing, or GP-LP alignment |
| F: Core Tension | Frequently Growth vs. Leverage or Incentive Conflict (GP deployment incentives vs. LP return-of-capital expectations) |

**Key metrics to extract (Field C):** Fund vintage, fund size, percentage deployed, entry EBITDA multiple, debt/EBITDA, equity check, hold period to date, DPI, TVPI, exit multiple (if exited), co-invest amount.

### 16.4 Banking / Credit

**Framework:** Credit quality trends (charge-offs, NPLs, reserves, criticized loans), regulatory capital, deposit costs, net interest margin, loan growth by category.

| Brief Field | Banking-Specific Application |
|-------------|------------------------------|
| C: Transaction Economics | Loan portfolio size, weighted average LTV, DSCR distribution, charge-off rate, reserve coverage, CET1 ratio, deposit beta |
| D: Market Context | Fed funds rate, yield curve, deposit competition, regulatory actions, M&A activity |
| E: Central Financial Question | Often about credit loss recognition timing, capital adequacy, or deposit franchise value |
| F: Core Tension | Frequently Risk vs. Yield (are loan yields compensating for credit risk?) or Policy Consequence (did regulation cause behavior change?) |

**Key metrics to extract (Field C):** Total loans by category, NPL ratio, net charge-off rate, ACL/loans, CET1 ratio, LCR, NSFR, NIM, deposit cost, deposit beta, loan/deposit ratio, criticized/classified loan ratio.

### 16.5 Data Centers

**Framework:** Power procurement timeline (years), land + power = site value, hyperscaler pre-leasing as financing condition, interconnection queue as primary constraint.

| Brief Field | Data Center-Specific Application |
|-------------|----------------------------------|
| C: Transaction Economics | MW capacity, price per MW, land cost, power cost per MWh, interconnection queue position, construction cost per MW, lease rate per kW/month |
| D: Market Context | Vacancy by market (Northern Virginia, Phoenix, Dallas, etc.), absorption, pipeline, power availability by utility territory, hyperscaler capex guidance |
| E: Central Financial Question | Often about the power constraint, the pre-leasing requirement, or the land+power premium |
| F: Core Tension | Frequently The Constraint (power interconnection timeline vs. tenant demand) or The Hidden Bet (speculative development without pre-leasing) |

**Key metrics to extract (Field C):** Total MW, IT load MW, price per MW, land acres, land cost per acre, power cost per MWh, construction cost per MW, lease rate per kW/month, interconnection queue position (in years), pre-leased percentage, hyperscaler tenant(s).

### 16.6 Energy

**Framework:** LCOE vs. PPA price, renewable penetration and curtailment risk, IRA incentive value, interconnection queue, offtaker credit quality.

| Brief Field | Energy-Specific Application |
|-------------|-----------------------------|
| C: Transaction Economics | MW capacity, price per MW, PPA price per MWh, PPA remaining term, LCOE, ITC/PTC value, tax equity amount, development pipeline MW |
| D: Market Context | Power price forecasts by hub, renewable penetration by ISO, interconnection queue backlog, IRA guidance, transmission buildout |
| E: Central Financial Question | Often about PPA renewal risk, IRA dependence, or development yield compression |
| F: Core Tension | Frequently Price vs. Value (does the acquisition price properly discount PPA renewal risk?) or Policy Consequence (is IRA creating a subsidy-dependent asset class?) |

**Key metrics to extract (Field C):** Total MW (operating, under construction, development pipeline), PPA price per MWh, PPA weighted average remaining term, LCOE, ITC/PTC value, tax equity amount and cost, interconnection deposit amount, development spend to date.

### 16.7 Fed / Macro

**Framework:** Data release interpretation (payrolls, CPI, GDP, JOLTS, etc.), FOMC communication parsing, yield curve signals, financial conditions indices.

| Brief Field | Fed/Macro-Specific Application |
|-------------|--------------------------------|
| C: Transaction Economics | Data release values vs. consensus, revision history, trend direction, components driving the headline |
| D: Market Context | Fed funds futures pricing, yield curve shape, breakeven inflation rates, credit spreads, financial conditions indices |
| E: Central Financial Question | Often about whether the data supports the market's rate path pricing or whether a trend is accelerating/decelerating |
| F: Core Tension | Frequently Price Signal (what is the data telling us that the market is not pricing?) or Market Turning Point (is this the data point that changes the narrative?) |

**Key metrics to extract (Field C):** Headline data value, consensus estimate, prior month value, prior month revision, year-over-year change, 3-month annualized rate, 6-month annualized rate, component contribution to headline, wage/price components.

### 16.8 Local Government

**Framework:** Zoning changes, incentives (TIF, LIHTC, opportunity zones), permitting timelines, infrastructure commitments, tax base impact, public-private partnership structure.

| Brief Field | Local Government-Specific Application |
|-------------|---------------------------------------|
| C: Transaction Economics | Incentive value (TIF, tax abatement, land contribution), infrastructure commitment cost, permit timeline, fee structure, public contribution vs. private investment ratio |
| D: Market Context | Municipal fiscal condition, comparable incentive packages, development pipeline in jurisdiction, political environment |
| E: Central Financial Question | Often about whether the incentive package is appropriately calibrated or whether the public is bearing disproportionate risk |
| F: Core Tension | Frequently Incentive Conflict (developer return vs. public benefit) or Policy Consequence (did the incentive produce the intended development?) |

**Key metrics to extract (Field C):** Total project cost, public contribution (TIF, grant, land, infrastructure), private investment, projected tax revenue, projected jobs, incentive net present value, clawback provisions, affordable housing units required/provided.

### 16.9 Cross-Sector Framework Selection

When a story spans multiple sectors (e.g., a data center transaction that is also a CRE land deal and an energy procurement story), the brief must:

1. **Identify the primary sector** (the sector from which the Central Financial Question arises)
2. **Apply the primary sector's framework** to Fields C, D, E, and F
3. **Note secondary-sector implications** in Field J (Reader Relevance)
4. **Flag the cross-sector nature** in Field A (Event Summary) so the drafting prompt applies the correct sector voice

---

## 17. Brief Output Format (JSON Schema)

The Analytical Brief must be producible as structured JSON for programmatic consumption by downstream prompt stages. The JSON schema is:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "LightTowerAnalyticalBrief",
  "type": "object",
  "required": [
    "story_id", "brief_version", "analyst_model", "timestamp",
    "field_a_event_summary", "field_b_parties_and_incentives",
    "field_c_transaction_economics", "field_d_market_context",
    "field_e_central_financial_question", "field_f_core_tension",
    "field_g_thesis", "field_h_counterargument", "field_i_unknowns",
    "field_j_reader_relevance", "field_k_article_architecture",
    "field_l_article_depth", "field_m_key_numbers"
  ],
  "properties": {
    "story_id": { "type": "string" },
    "brief_version": { "type": "string", "const": "1.0" },
    "analyst_model": { "type": "string" },
    "timestamp": { "type": "string", "format": "date-time" },
    "field_a_event_summary": {
      "type": "object",
      "required": ["event", "primary_source", "corroboration", "unconfirmed"],
      "properties": {
        "event": { "type": "string", "minLength": 50, "maxLength": 800 },
        "primary_source": { "type": "string" },
        "corroboration": { "type": "string" },
        "unconfirmed": { "type": "string" }
      }
    },
    "field_b_parties_and_incentives": {
      "type": "object",
      "required": ["parties"],
      "properties": {
        "parties": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "required": ["name", "role", "gain", "risk", "timing_motivation", "constraint", "clock"],
            "properties": {
              "name": { "type": "string" },
              "role": { "type": "string" },
              "gain": { "type": "string" },
              "risk": { "type": "string" },
              "timing_motivation": { "type": "string" },
              "constraint": { "type": "string" },
              "clock": { "type": "string" }
            }
          }
        }
      }
    },
    "field_c_transaction_economics": {
      "type": "object",
      "required": ["numbers"],
      "properties": {
        "numbers": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "required": ["value", "description", "source_type", "source_detail", "context", "confidence"],
            "properties": {
              "value": { "type": "string" },
              "description": { "type": "string" },
              "source_type": { "type": "string", "enum": ["REPORTED", "CALCULATED", "ESTIMATED", "UNAVAILABLE"] },
              "source_detail": { "type": "string" },
              "context": { "type": "string" },
              "confidence": { "type": "string", "enum": ["HIGH", "MEDIUM", "LOW", "ESTIMATED"] }
            }
          }
        }
      }
    },
    "field_d_market_context": {
      "type": "object",
      "required": ["interest_rate_credit_environment", "comparable_transactions", "sector_supply_demand", "regulatory_environment", "timeliness_factor"],
      "properties": {
        "interest_rate_credit_environment": { "type": "string" },
        "comparable_transactions": { "type": "array", "items": { "type": "string" } },
        "sector_supply_demand": { "type": "string" },
        "regulatory_environment": { "type": "string" },
        "timeliness_factor": { "type": "string" }
      }
    },
    "field_e_central_financial_question": { "type": "string" },
    "field_f_core_tension": { "type": "string" },
    "field_g_thesis": { "type": "string" },
    "field_h_counterargument": {
      "type": "object",
      "required": ["counterargument", "what_would_make_thesis_wrong"],
      "properties": {
        "counterargument": { "type": "string" },
        "what_would_make_thesis_wrong": { "type": "string" }
      }
    },
    "field_i_unknowns": {
      "type": "object",
      "required": ["unavailable_facts", "uncalculated_metrics", "unverified_assumptions"],
      "properties": {
        "unavailable_facts": { "type": "array", "items": { "type": "string" } },
        "uncalculated_metrics": { "type": "array", "items": { "type": "string" } },
        "unverified_assumptions": { "type": "array", "items": { "type": "string" } }
      }
    },
    "field_j_reader_relevance": {
      "type": "object",
      "required": ["segments"],
      "properties": {
        "segments": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["segment", "takeaway"],
            "properties": {
              "segment": { "type": "string" },
              "takeaway": { "type": "string" }
            }
          }
        }
      }
    },
    "field_k_article_architecture": {
      "type": "object",
      "required": ["selected_architecture", "justification"],
      "properties": {
        "selected_architecture": {
          "type": "string",
          "enum": ["The Hidden Bet", "The Constraint", "The Price Signal", "The Incentive Conflict", "The Policy Consequence", "The Market Turning Point"]
        },
        "justification": { "type": "string" }
      }
    },
    "field_l_article_depth": {
      "type": "object",
      "required": ["selected_depth", "justification", "word_target"],
      "properties": {
        "selected_depth": { "type": "string", "enum": ["Brief", "Standard", "Deep"] },
        "justification": { "type": "string" },
        "word_target": { "type": "string" }
      }
    },
    "field_m_key_numbers": {
      "type": "array",
      "minItems": 3,
      "maxItems": 5,
      "items": {
        "type": "object",
        "required": ["number", "representation", "interpretation"],
        "properties": {
          "number": { "type": "string" },
          "representation": { "type": "string" },
          "interpretation": { "type": "string" }
        }
      }
    }
  }
}
```

---

## 18. Brief Production Rules

### 18.1 When the Brief Is Produced

The Analytical Brief is produced at **Stage 6 (Thesis Generation)** through **Stage 7 (Article Architecture)** of the Modular Prompt Architecture (see Document 08). Specifically:

- Fields A, B, C: Populated by Stage 1 (Fact Extraction) and Stage 3 (Financial Analysis)
- Fields D, E, F, G, H, I: Populated by Stage 6 (Thesis Generation)
- Fields J, K, L, M: Populated by Stage 7 (Article Architecture)

The brief is assembled into its complete form after Stage 7 and before Stage 8 (Article Outline). No drafting occurs until the complete brief is validated.

### 18.2 Brief Validation

Before the brief is accepted, it must pass validation:

1. **Schema validation:** The JSON must conform to the schema in Section 17.
2. **Completeness check:** All required fields must be non-empty and non-generic.
3. **Falsifiability check:** Field G (Thesis) must contain a claim that is falsifiable. This is verified by an automated check: "If we asked an LLM 'what evidence would disprove this thesis?' can it produce a specific answer?"
4. **Consistency check:** The Core Tension (F) must be consistent with the Central Financial Question (E) and Thesis (G). An automated check verifies that the three fields do not contradict each other.
5. **Source traceability:** Every claim in Fields A-E must either cite a specific source or be marked as an inference. Claims that are neither sourced nor flagged are rejected.

### 18.3 Brief Revision Loop

If validation fails, the brief is returned to the relevant stage for revision:

| Validation Failure | Stage to Revise |
|--------------------|-----------------|
| Schema validation | Stage 6 (Thesis Generation) — regenerate entire brief |
| Field A (Event Summary) incomplete | Stage 1 (Fact Extraction) — re-extract facts |
| Field B (Parties) incomplete | Stage 2 (Entity Extraction) — re-extract parties |
| Field C (Transaction Economics) sparse | Stage 3 (Financial Analysis) — re-analyze |
| Field G (Thesis) unfalsifiable | Stage 6 (Thesis Generation) — generate new thesis |
| Fields E, F, G inconsistent | Stage 6 (Thesis Generation) — regenerate E, F, G |

Maximum two revision loops per brief. If the brief fails validation after two revisions, the story is flagged for human review and the automated pipeline does not proceed.

### 18.4 Brief Versioning and Audit

Every brief is versioned and logged:

```json
{
  "brief_id": "brief-{story_id}-v{version}",
  "story_id": "story_2025_001452",
  "brief_version": "1.0",
  "analyst_model": "deepseek-v4-pro",
  "timestamp": "2025-03-25T14:22:18Z",
  "pipeline_stage": "stage_6_thesis_generation",
  "validation_passed": true,
  "revision_count": 0,
  "fields": { "...complete brief JSON..." }
}
```

Briefs are stored in `editorial_state/briefs/{story_id}.json` and appended to the audit trail `audit/briefs.jsonl`.

---

## 19. Quality Standards and Rejection Criteria

### 19.1 Minimum Quality Thresholds

Every brief field is scored 1-10 during validation. Fields below their minimum trigger revision:

| Field | Minimum Score | Consequence of Failure |
|-------|---------------|------------------------|
| A: Event Summary | 7 | Brief returned to Stage 1 |
| B: Parties and Incentives | 6 | Brief returned to Stage 2 |
| C: Transaction Economics | 6 | Brief returned to Stage 3 |
| D: Market Context | 6 | Brief returned to Stage 6 |
| E: Central Financial Question | 7 | Brief returned to Stage 6 |
| F: Core Tension | 6 | Brief returned to Stage 6 |
| G: Thesis | 7 | Brief returned to Stage 6 |
| H: Counterargument | 6 | Brief returned to Stage 6 |
| I: Unknowns | 7 | Brief returned to Stage 6 |
| J: Reader Relevance | 6 | Brief returned to Stage 7 |
| K: Article Architecture | 7 | Brief returned to Stage 7 |
| L: Article Depth | 7 | Brief returned to Stage 7 |
| M: Key Numbers | 6 | Brief returned to Stage 7 |

### 19.2 Automatic Rejection Conditions

The brief is automatically rejected (cannot proceed to drafting) if:

1. Any field is left blank or contains only placeholder text.
2. Field A (Event Summary) contains no named entities, no dates, and no amounts.
3. Field C (Transaction Economics) contains fewer than three numbers, none of which are contextualized.
4. Field G (Thesis) is unfalsifiable (automated check fails).
5. Fields E, F, and G are logically inconsistent (automated check fails).
6. The brief exceeds two revision loops without passing validation.
7. The story's scoring from the selection pipeline (Document 06) is below Tier 2, making it ineligible for automated drafting.

---

## 20. Integration with Scoring and Audit

### 20.1 Relationship to the 10 Scoring Dimensions

The Analytical Brief directly feeds the editorial scoring system (Document 09: Editorial Scoring Rubric). Each brief field corresponds to at least one scoring dimension:

| Brief Field | Scoring Dimension(s) Fed |
|-------------|--------------------------|
| A: Event Summary | 1: Factual Accuracy |
| B: Parties and Incentives | 5: Incentive Analysis |
| C: Transaction Economics | 6: Use of Numbers |
| D: Market Context | 7: Market Context |
| E: Central Financial Question | 4: Thesis Strength |
| F: Core Tension | 4: Thesis Strength, 8: Narrative Structure |
| G: Thesis | 4: Thesis Strength, 3: Analytical Originality |
| H: Counterargument | 12: Intellectual Honesty |
| I: Unknowns | 12: Intellectual Honesty |
| J: Reader Relevance | 13: Reader Utility |
| K: Article Architecture | 8: Narrative Structure |
| L: Article Depth | 8: Narrative Structure |
| M: Key Numbers | 6: Use of Numbers |

### 20.2 Audit Trail Requirements

Every brief must log:

- `story_id` — unique identifier linking to the source story in the manifest
- `brief_id` — unique brief identifier
- `brief_version` — version number (increments on revision)
- `analyst_model` — the LLM model that produced the brief
- `pipeline_stage` — the stage at which the brief was completed
- `timestamp` — ISO 8601 datetime of brief completion
- `total_tokens_consumed` — tokens used across all stages to produce this brief
- `total_cost` — estimated cost in USD
- `validation_passed` — boolean
- `revision_count` — number of revisions required
- `rejection_reason` — if rejected, the specific reason code
- `sector` — primary sector classification
- `depth` — Brief, Standard, or Deep
- `architecture` — selected story architecture
- `fields_hash` — SHA-256 hash of the JSON brief for integrity verification

---

## 21. Examples by Depth and Sector

### 21.1 Example: Brief — CRE Transaction

```
Field A — Event Summary:
Event: Clarion Partners sold a 312-unit multifamily property in
Phoenix, AZ (The Bristol at South Mountain) to TruAmerica
Multifamily for $94.5 million on March 18, 2025, representing
$302,885 per unit. The property was built in 2021 and is 94.5%
occupied. The sale represents a 5.1% going-in cap rate on current
NOI.

Primary Source: Cushman & Wakefield press release (broker), March 18, 2025
Corroboration: Maricopa County property records, recorded March 20, 2025
Unconfirmed: Buyer financing terms, seller's original basis, specific cap rate

Field C — Transaction Economics:
- $94.5 million — Purchase price
  Source: REPORTED from Cushman & Wakefield press release
  Context: Represents a 4.8% decline from the seller's original
           asking price of $99.3 million (listed October 2024)
  Confidence: HIGH

- $302,885/unit — Price per unit
  Source: CALCULATED as $94,500,000 / 312 units
  Context: Below the Phoenix MSA average of $325,000/unit for
           Class A multifamily (per CoStar Q4 2024), but above
           the $280,000/unit average for 2021-vintage product
  Confidence: HIGH

- 5.1% — Going-in cap rate (estimated)
  Source: ESTIMATED based on market NOI for comparable Phoenix
          Class A assets
  Context: 5.1% represents 85 bps above the 10-year Treasury
           (4.25%) — a spread that is roughly in line with the
           10-year average of 100-150 bps for Sun Belt multifamily
  Confidence: MEDIUM — NOI not independently confirmed
```

### 21.2 Example: Standard — Banking / Credit Story

```
Field E — Central Financial Question:
Does the 23% year-over-year increase in criticized CRE loans at
Regions Financial represent a normalization from unsustainably low
levels, or is it the leading edge of a credit cycle that will
materially exceed the bank's current 1.5% ACL/loans reserve?

Field F — Core Tension:
The criticized loan growth is concentrated in office (62% of the
increase) and suggests accelerating deterioration, but the
weighted-average LTV on criticized loans is 58% — implying the bank
has a 42% equity cushion before credit losses materialize, and the
criticism may reflect appraisal lag rather than fundamental loss
severity.

Field G — Thesis:
Regions Financial's Q4 2024 criticized loan data is not a false
alarm — it is the first bank-level confirmation that office CRE
credit is deteriorating faster than the industry's reserving
assumes. However, the 58% LTV on criticized loans means realized
losses will be deferred until 2026-2027, when these loans mature
and must be refinanced at higher rates and lower appraised values.
The bank's current 1.5% reserve is adequate for 2025 but likely
insufficient for 2026-2027 if the 10-year Treasury does not decline
below 3.75%.
```

### 21.3 Example: Deep — Energy / Data Center Cross-Sector

```
Field G — Thesis:
The Constellation Energy-Microsoft agreement to restart Three Mile
Island Unit 1 is not primarily an energy story — it is a data center
power procurement story that reveals the nuclear option has become
economically competitive for the first time in four decades, but
only because hyperscaler offtakers are willing to pay a premium that
no utility regulator would allow a ratepayer to bear. The $1.6 billion
restart cost and $100/MWh offtake price are both above what any
competitive wholesale market would support, meaning this model works
only for behind-the-meter or direct-connect arrangements where the
data center tenant — not the ratepayer — absorbs the above-market cost.
This structure bypasses the traditional utility cost-recovery model
and creates a new asset class: the dedicated nuclear data center.

Field H — Counterargument:
This is a one-off arrangement exploiting a unique asset (a recently
closed reactor with intact infrastructure) and a unique offtaker
(Microsoft, with the largest corporate clean-energy commitment in
history). It does not signal a broader trend because (1) only 3-4
recently retired U.S. nuclear plants are candidates for restart, (2)
the NRC has never approved a restart of this scale, and (3) new-build
nuclear remains uneconomic at $8,000-12,000/kW. The TMI restart is a
novelty, not a template.
```

---

## Document Control

| Field | Value |
|-------|-------|
| Document ID | 07-Analytical-Brief-Schema |
| Version | 1.0 |
| Author | Light Tower Group Editorial Architecture |
| Approved By | [Pending] |
| Last Modified | July 30, 2026 |
| Next Review | January 30, 2027 |
| Supersedes | None (new document) |
| Dependencies | Document 06 (Scoring and Ranking), Document 08 (Modular Prompt Architecture), Document 09 (Editorial Scoring Rubric) |
| Distribution | Editorial Engineering, Pipeline Engineering, Editorial Leadership |
