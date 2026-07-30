# 09 — Editorial Scoring Rubric: 14-Dimension Quality Assessment

**Document:** 09-Editorial-Scoring-Rubric
**Date:** July 30, 2026
**Status:** Authoritative Reference — Required Scoring Standard for All Published Content

---

## Table of Contents

1. [Purpose and Application](#1-purpose-and-application)
2. [Scoring Architecture](#2-scoring-architecture)
3. [Publication Thresholds](#3-publication-thresholds)
4. [Dimension 1: Factual Accuracy](#4-dimension-1-factual-accuracy)
5. [Dimension 2: Financial Understanding](#5-dimension-2-financial-understanding)
6. [Dimension 3: Analytical Originality](#6-dimension-3-analytical-originality)
7. [Dimension 4: Thesis Strength](#7-dimension-4-thesis-strength)
8. [Dimension 5: Incentive Analysis](#8-dimension-5-incentive-analysis)
9. [Dimension 6: Use of Numbers](#9-dimension-6-use-of-numbers)
10. [Dimension 7: Market Context](#10-dimension-7-market-context)
11. [Dimension 8: Narrative Structure](#11-dimension-8-narrative-structure)
12. [Dimension 9: Opening Quality](#12-dimension-9-opening-quality)
13. [Dimension 10: Sentence Quality](#13-dimension-10-sentence-quality)
14. [Dimension 11: Originality of Language](#14-dimension-11-originality-of-language)
15. [Dimension 12: Intellectual Honesty](#15-dimension-12-intellectual-honesty)
16. [Dimension 13: Reader Utility](#16-dimension-13-reader-utility)
17. [Dimension 14: Conclusion Quality](#17-dimension-14-conclusion-quality)
18. [Composite Score Calculation](#18-composite-score-calculation)
19. [Scoring Process and Calibration](#19-scoring-process-and-calibration)
20. [Integration with Pipeline Gate System](#20-integration-with-pipeline-gate-system)

---

## 1. Purpose and Application

### 1.1 What This Rubric Is

The 14-dimension editorial scoring rubric is the authoritative standard for evaluating every piece of content the Light Tower Group publishes. It transforms "this article feels weak" into "this article scores 4 on Incentive Analysis because it names the parties but doesn't explain what each party needs from the deal, fears losing, or is betting on." Every score must be accompanied by a one-sentence justification that references specific content in the article.

### 1.2 What This Rubric Is Not

This rubric is not a checklist. A score of 8 on Use of Numbers does not mean "the article has 8 numbers in it." It means the article uses numbers the way a financial professional would — to prove a point, to reveal a relationship, to benchmark against a standard. The scoring criteria describe behaviors, not counts.

### 1.3 Who Uses This Rubric

- **The Editorial Review stage (Stage 11)** of the modular prompt architecture applies this rubric automatically to every draft.
- **Human editors** use this rubric when spot-checking articles or reviewing Tier 1 content.
- **The pipeline audit system** uses this rubric to track quality trends across sectors, models, and time.
- **The scoring recalibration system** (`scoring_recalibration.py`) uses this rubric to tune the automated scoring weights.

### 1.4 When Scoring Happens

| Timing | Context | Scorer |
|--------|---------|--------|
| Post-draft (Stage 11) | Automated editorial review of the first draft | LLM (mid-tier) |
| Post-revision (Stage 13) | Automated reassessment after fixes | LLM (mid-tier) |
| Pre-publication | Human spot-check for Tier 1 stories | Human editor |
| Post-publication | Retrospective audit and corpus analysis | Automated + human audit |

---

## 2. Scoring Architecture

### 2.1 The 1–10 Scale

Every dimension uses the same 10-point scale. The scale is not symmetric — the middle is not 5. The scale is designed around publication standards:

| Score Range | Meaning | Publication Implication |
|-------------|---------|------------------------|
| 1–3 | Fundamentally deficient | Do not publish. Restart from brief. |
| 4–5 | Below standard | Major revision required. May need brief reconsideration. |
| 6 | Meets minimum threshold | Acceptable for publication only if all other dimensions also pass. |
| 7 | Competent professional standard | Publishable. No embarrassment. |
| 8 | Strong, with notable insight | Good article. Reader will learn something. |
| 9 | Exceptional, best-in-class | Anchor article for an edition. Share widely. |
| 10 | Definitive | Rare. The article is the reference on this topic. |

### 2.2 Scoring Principle

Scores are not awarded for trying. A factually accurate but shallow article gets a 9 on Factual Accuracy and a 4 on Financial Understanding. Dimensions are scored independently. The composite score reveals whether an article that excels in one area is carried by that strength despite weakness elsewhere.

### 2.3 Score Justification Requirement

Every score must include a one-sentence justification. "6 — Acceptable" is not a valid justification. "6 — Names all parties but does not explain what any party's constraint or bet is" is a valid justification. Justifications make scoring auditable and force the scorer to engage with the article's content rather than producing an impression.

---

## 3. Publication Thresholds

### 3.1 Individual Dimension Thresholds

| # | Dimension | Minimum for Publication | Weight in Composite |
|---|-----------|------------------------|---------------------|
| 1 | Factual Accuracy | 9 | 2.0x |
| 2 | Financial Understanding | 7 | 1.8x |
| 3 | Analytical Originality | 7 | 1.5x |
| 4 | Thesis Strength | 6 | 1.5x |
| 5 | Incentive Analysis | 6 | 1.3x |
| 6 | Use of Numbers | 6 | 1.2x |
| 7 | Market Context | 6 | 1.2x |
| 8 | Narrative Structure | 6 | 1.1x |
| 9 | Opening Quality | 7 | 1.1x |
| 10 | Sentence Quality | 6 | 1.0x |
| 11 | Originality of Language | 6 | 1.0x |
| 12 | Intellectual Honesty | 9 | 1.5x |
| 13 | Reader Utility | 6 | 1.2x |
| 14 | Conclusion Quality | 6 | 1.0x |

### 3.2 Overall Threshold

**Minimum composite score: 7.0**

An article must meet BOTH conditions to publish:
1. Every individual dimension meets or exceeds its minimum threshold
2. The weighted composite score is 7.0 or higher

An article that scores 9 on Factual Accuracy, 9 on Intellectual Honesty, and 4 on everything else has a composite score of approximately 6.1 and does NOT publish — even though it meets the two most heavily weighted thresholds.

### 3.3 Tier-Based Adjustment

| Tier | Minimum Composite | Audit Intensity |
|------|-------------------|-----------------|
| Tier 1 (Must Cover) | 7.5 | Full 14-dimension review + human editor |
| Tier 2 (Strongly Recommended) | 7.0 | Full 14-dimension review, automated |
| Tier 3 (Optional / Brief) | 6.5 | 7-dimension subset review (dimensions 1, 2, 4, 6, 9, 12, 13) |

---

## 4. Dimension 1: Factual Accuracy

**Minimum for Publication: 9**
**Weight: 2.0x**

### What This Dimension Measures

Every factual assertion in the article — name, number, date, location, action, condition — is verifiable against source material and correctly represented. This is the foundation. Nothing else matters if the facts are wrong.

### Scoring Criteria

| Score | Criteria |
|-------|----------|
| 1–3 | Multiple critical factual errors: wrong company names, wrong dollar amounts, wrong locations, misattributed actions. Article is harmful. |
| 4–5 | At least one significant factual error: a number off by an order of magnitude, a party misidentified, a timeline error that changes the story's meaning. |
| 6 | No critical errors, but 2–3 minor inaccuracies: slightly wrong date, approximate number presented as exact, location described at wrong granularity. |
| 7 | One minor inaccuracy. All material facts are correct. |
| 8 | All facts correct. Minor imprecision in one non-material detail (e.g., "last month" for an event 5 weeks ago). |
| 9 | All facts correct and precisely stated. Every number matches source. Every party is correctly named. Every location is accurate. |
| 10 | All facts correct AND the article correctly handles ambiguity: notes when a source disagrees with another source, distinguishes reported from unconfirmed information, does not present inference as fact. |

### Common Failure Mode

The drafting model fills gaps in source material with plausible-sounding facts from its training data. "The 350,000-square-foot building was constructed in 2008" — when the source says nothing about construction date. This is a hallucination, not a minor error. Score 3 maximum.

### Verification Method

Every factual claim must map to a `fact_id` in the Stage 1 Fact Extraction output. Claims without source mapping are flagged. The verification rate (percentage of claims with source mapping) is a leading indicator of factual accuracy.

---

## 5. Dimension 2: Financial Understanding

**Minimum for Publication: 7**
**Weight: 1.8x**

### What This Dimension Measures

The article demonstrates genuine comprehension of the financial mechanics at work — not just vocabulary, but reasoning. It explains why a number matters, not just that a number exists.

### Scoring Criteria

| Score | Criteria |
|-------|----------|
| 1–3 | Financial terms used incorrectly. Calculations are wrong. Article confuses debt and equity, cap rate and interest rate, basis and market value. Financially illiterate. |
| 4–5 | Correct vocabulary but no demonstrated understanding. States numbers but does not interpret them. Reads like a press release with financial jargon added. |
| 6 | Correctly identifies the key financial metric(s) but does not explain their significance. States "the cap rate was 5.2%" but doesn't say whether that's high, low, or what it implies. |
| 7 | Identifies key financial metrics AND provides at least one correct interpretation. "The 5.2% cap rate is 80 bps inside the submarket average, suggesting the buyer is underwriting rent growth." |
| 8 | Multiple correct financial interpretations. Shows the math when appropriate (e.g., implied price per unit, cost per MW, LTV calculation). Benchmarks at least one number. |
| 9 | Sophisticated financial reasoning: traces a number through the capital structure, explains the relationship between multiple financial metrics, identifies what the numbers reveal that the press release doesn't say. |
| 10 | The financial analysis is the article's organizing insight. The story is told through the numbers — not as decoration but as the primary narrative device. A reader who only reads the financial analysis paragraphs understands the story. |

### Common Failure Mode

The article uses financial vocabulary correctly but never does math. "The transaction reflects strong market fundamentals" — this is not financial understanding. It is financial cosplay. Score 4.

### What Counts as Financial Understanding

- Calculating a metric from two reported numbers (e.g., NOI / price = cap rate)
- Comparing a metric to a benchmark (e.g., "80 bps inside the submarket average")
- Explaining the implication of a metric (e.g., "at a 5.2% cap rate, the buyer needs 3% annual rent growth just to break even on a levered basis")
- Tracing a number through the capital structure (e.g., "the senior lender's 55% LTV means the mezzanine piece is effectively subordinated at 75% LTV")

### What Does Not Count

- Stating that a number exists ("the deal was valued at $450 million")
- Using financial adjectives without evidence ("an aggressive bid," "a conservative structure")
- Mentioning sector trends without connecting them to the specific transaction

---

## 6. Dimension 3: Analytical Originality

**Minimum for Publication: 7**
**Weight: 1.5x**

### What This Dimension Measures

The article contributes an insight that is not obvious from reading the source material. It does not merely restate the press release in different words. It identifies something the source didn't say — a pattern, an implication, a contradiction — that a knowledgeable reader would find valuable.

### Scoring Criteria

| Score | Criteria |
|-------|----------|
| 1–3 | Pure restatement. The article is the source material rewritten with different adjectives. No original thought. |
| 4–5 | Minimal original contribution. One sentence of genuine analysis surrounded by summary. The reader learns nothing they couldn't have learned from the headline. |
| 6 | One genuine insight, but it is obvious (e.g., "this is a large deal" or "interest rates matter"). The insight would occur to any reader with basic sector knowledge. |
| 7 | At least one non-obvious insight. A reader with sector knowledge would say "I hadn't thought of it that way." The insight is specific to this transaction, not generic. |
| 8 | Multiple non-obvious insights. The article connects dots that are not connected in the source material — across parties, across deals, across time. |
| 9 | The article's central insight is genuinely original — it interprets the facts in a way that changes how a professional reader would think about the transaction, the sector, or the market. |
| 10 | Definitive reinterpretation. The article's analysis becomes the lens through which other market participants will view this transaction. It sets the terms of the conversation. |

### Common Failure Mode

The thesis is "this is a significant transaction" — which is true of every transaction the system covers. If the thesis could describe any deal in the sector, it is not original. Score 3.

### What Counts as Originality

- Identifying a pattern across multiple transactions that isn't in any single source
- Surfacing a contradiction between what a party said and what the numbers show
- Reframing the story: "this looks like X but is actually Y"
- Identifying an implication that would change a market participant's behavior
- Connecting this transaction to a trend that the source didn't mention

### What Does Not Count

- Stronger adjectives ("massive" instead of "large")
- Adding generic context ("this comes amid rising interest rates")
- Restating the article's topic as an insight ("this shows that data centers are growing")

---

## 7. Dimension 4: Thesis Strength

**Minimum for Publication: 6**
**Weight: 1.5x**

### What This Dimension Measures

The article has a single, specific, arguable thesis that is stated or clearly implied in the first third of the article and that the remainder of the article supports with evidence. The thesis is not a topic statement. It is not a summary. It is an argument.

### Scoring Criteria

| Score | Criteria |
|-------|----------|
| 1–3 | No discernible thesis. The article is a sequence of facts with no organizing argument. The reader finishes and thinks "ok, but what's the point?" |
| 4–5 | A weak or vague thesis is present but buried or underdeveloped. The thesis is a topic statement ("this article discusses the AWS data center announcement") rather than an argument ("AWS's pricing reveals data center site selection has become a queue-position problem"). |
| 6 | A specific thesis is present and identifiable by paragraph 5. It is arguable (a reasonable person could disagree). The rest of the article is at least loosely organized around proving it. |
| 7 | Strong thesis, clearly stated early, arguable, specific to this transaction. The article's structure is visibly organized around the thesis. |
| 8 | Thesis is the article's organizing principle. Every section advances the argument. Evidence is marshaled effectively. The thesis survives a reasonable counterargument. |
| 9 | Thesis is the kind of insight a professional would pay for. It is specific, surprising, well-supported, and changes how the reader thinks about the transaction. The article does not wander — every paragraph earns its place in service of the thesis. |
| 10 | The thesis is definitive — it becomes the standard interpretation of the event. Other market participants will reference it. The thesis is stated with such precision and supported with such rigor that it compels agreement. |

### Common Failure Mode

The article has a thesis in the headline and then abandons it. The body is a generic summary of the transaction with no argumentative structure. This is not a weak thesis — it is a broken one. Score 3.

### Thesis Quality Test

If you can replace the article's specific subject with another company and location and the thesis still makes sense, it is not specific enough. "This deal shows that [sector] continues to attract capital" fails this test. "AWS's cost-per-MW premium reveals that data center site selection is now a power interconnection problem, not a real estate problem" passes.

---

## 8. Dimension 5: Incentive Analysis

**Minimum for Publication: 6**
**Weight: 1.3x**

### What This Dimension Measures

The article explains why each party acted as it did — not just what they did. It identifies constraints, motivations, fears, and bets. It shows how the deal structure reflects the parties' incentives.

### Scoring Criteria

| Score | Criteria |
|-------|----------|
| 1–3 | No incentive analysis. Lists parties but not what drove their decisions. "AWS announced" — no explanation of why or why now. |
| 4–5 | Generic motivational language. "The buyer saw an opportunity" or "the seller wanted to exit." These could describe any transaction. |
| 6 | At least one party's incentive is explained specifically. The explanation is tied to a reported fact or financial metric rather than a generic motivation. |
| 7 | Multiple parties' incentives are explained. At least one conflict of interest is identified (parties want different things and the transaction resolves the conflict in a specific way). |
| 8 | Full incentive mapping: each major party's desire, fear, constraint, and bet are identified. The deal's structure is explained as the resolution of conflicting incentives. |
| 9 | The incentive analysis is the article's analytical engine. The reader understands not just what happened but why it happened in this way, at this time, with these parties. Could not have happened differently given the incentive structure. |
| 10 | The incentive analysis reveals something the parties themselves might not have stated publicly — a hidden motivation, an unstated bet, a constraint that shaped the deal in ways the press release obscures. |

### Common Failure Mode

The article says "the buyer is betting on rent growth" without specifying: what rent growth assumption, over what period, and why that assumption is notable. Generic betting language is not incentive analysis. Score 3.

### What Counts as Incentive Analysis

- Identifying a party's specific constraint (e.g., fund deployment deadline, regulatory requirement, competitive pressure)
- Explaining what a party needs the deal to accomplish that goes beyond the stated rationale
- Identifying which party has leverage and why
- Showing how the deal structure (price, terms, timing, contingencies) reflects the balance of incentives
- Naming what each party fears — the outcome they structured the deal to avoid

---

## 9. Dimension 6: Use of Numbers

**Minimum for Publication: 6**
**Weight: 1.2x**

### What This Dimension Measures

The article uses numbers to do work — to prove, compare, reveal, or quantify. Numbers are not decorative. They are not mentioned and abandoned. Each number in the article advances the argument.

### Scoring Criteria

| Score | Criteria |
|-------|----------|
| 1–3 | No numbers, or numbers used incorrectly. Wrong units, wrong orders of magnitude, numbers stated without context. |
| 4–5 | Numbers present but inert. The article says "$3.5 billion" but doesn't contextualize, compare, or interpret it. The number is wallpaper. |
| 6 | At least one number is actively used: compared to a benchmark, divided to produce a per-unit metric, or traced through a chain of reasoning. |
| 7 | Multiple numbers are actively used. At least one calculation is shown or implied. Numbers are integral to the article's argument, not parenthetical. |
| 8 | Numbers are the backbone of the analysis. The article builds its case by showing the reader the numbers and explaining what they mean. A reader could reconstruct the financial logic from the numbers alone. |
| 9 | Every number in the article earns its place. No number is stated without being interpreted. The article uses numbers the way an analyst would — as evidence, not as decoration. |
| 10 | The article's use of numbers is so effective that a numerically literate reader could reproduce the analysis independently. The numbers tell the story; the prose frames them. |

### Common Failure Mode

The article includes a "statistics paragraph" that lists numbers without connecting them to the argument: "The deal is valued at $450 million. The property is 350,000 square feet. The cap rate was 5.2%." These numbers are present but doing no work. Score 4.

### Active vs. Inert Numbers

Inert: "The property comprises 350,000 square feet."
Active: "At $1,286 per square foot, the buyer is paying a 22% premium to the submarket average of $1,050."

Inert: "The cap rate was 5.2%."
Active: "The 5.2% cap rate is 80 bps inside the trailing 12-month average of 6.0% — and 110 bps inside where this submarket was pricing 18 months ago."

---

## 10. Dimension 7: Market Context

**Minimum for Publication: 6**
**Weight: 1.2x**

### What This Dimension Measures

The article situates the transaction in its market context. It explains what trends this transaction reflects, contradicts, or accelerates. The reader understands why this transaction matters beyond itself.

### Scoring Criteria

| Score | Criteria |
|-------|----------|
| 1–3 | No market context. The article treats the transaction as an isolated event with no connection to broader market dynamics. |
| 4–5 | Generic context: "this comes amid rising interest rates" or "the market remains strong." These statements are true of almost any transaction in any cycle. |
| 6 | At least one specific market connection: a comparable transaction, a trend that this deal confirms or contradicts, a market statistic that contextualizes the deal's numbers. |
| 7 | Multiple specific market connections. At least one comparable transaction is named with numbers. The article explains what this deal signals about the market, not just what the market says about this deal. |
| 8 | Rich market context: comparables with numbers, trend analysis with evidence, market cycle positioning, and implication for other participants. The reader understands this deal's place in the market narrative. |
| 9 | The market context is itself analytical — it doesn't just describe the market, it interprets what this deal means for the market. The article identifies who should change their behavior based on this signal. |
| 10 | The article is the market context. A professional reading this piece would cite it as evidence in their own market analysis. The deal is the occasion; the market insight is the content. |

### Common Failure Mode

The market context section is a cut-and-paste of generic sector trends that could be appended to any article about that sector. It doesn't connect the specific deal to the specific trend. Score 4.

### What Counts as Market Context

- Named comparable transactions with specific numbers
- Sector-specific trend data (cap rate movement, volume trends, absorption, vacancy)
- Geographic market dynamics (submarket supply pipeline, regulatory changes, demographic shifts)
- Capital markets context (debt availability, spread movements, investor appetite shifts)
- Implication: what should other market participants do differently based on this signal?

---

## 11. Dimension 8: Narrative Structure

**Minimum for Publication: 6**
**Weight: 1.1x**

### What This Dimension Measures

The article is organized according to a recognizable structure that serves its thesis and its reader. The structure is not arbitrary. The reader can sense where they are in the argument at any point.

### Scoring Criteria

| Score | Criteria |
|-------|----------|
| 1–3 | No structure. Paragraphs are arranged arbitrarily. The article reads like notes assembled in random order. |
| 4–5 | Loose structure that doesn't consistently serve the argument. Some sections advance the thesis, others wander. The reader loses the thread. |
| 6 | Recognizable structure. The article has a clear beginning, middle, and end. The structure is appropriate to the material (e.g., chronological for a timeline story, thesis-evidence for an analytical piece). |
| 7 | Strong structure that visibly supports the thesis. Each section has a clear purpose and the purpose is fulfilled. Transitions connect sections logically. |
| 8 | The structure is a craft choice — it enhances the argument rather than merely containing it. The architecture (from Stage 7) is executed cleanly. The reader moves through the argument without effort. |
| 9 | The structure is itself part of the article's effectiveness. The way the argument unfolds — what is revealed when — makes the conclusion feel inevitable. A different structure would produce a weaker article. |
| 10 | Exemplary structure. The article could be used as a teaching example of how to organize a financial analysis for maximum impact. The structure is invisible to the reader but obvious to the analyst. |

### Common Failure Mode

The article uses a "miscellaneous" structure: facts, then some analysis, then more facts, then a conclusion that doesn't follow from the preceding paragraphs. This is not a structure — it's a sequence. Score 3.

### Recognized Architecture Patterns (from Document 08, Stage 7)

- **The Ticking Clock:** What must happen and by when
- **The Contrarian Take:** Surface story → actual story → evidence → implication
- **The Anatomy of a Deal:** Structure → parties → incentives → resolution
- **The Market Signal:** Transaction → comparables → trend → implication
- **The Two Sides:** Buyer's case → seller's case → why this deal at this price
- **The Ripple Effect:** Transaction → first-order effects → second-order effects
- **The Basis Is the Story:** Purchase price → current value → what changed
- **The Bet the Company:** What the company needs → the bet they made → the stakes

---

## 12. Dimension 9: Opening Quality

**Minimum for Publication: 7**
**Weight: 1.1x**

### What This Dimension Measures

The first three paragraphs do the work of an opening: they establish subject, stakes, and direction. The reader knows what the article is about, why it matters, and where it is going — and they want to keep reading.

### Scoring Criteria

| Score | Criteria |
|-------|----------|
| 1–3 | Opening is confusing, generic, or misleading. The reader cannot identify the article's subject or why they should care. |
| 4–5 | Opening establishes subject but not stakes. The reader knows what the article is about but doesn't know why it matters or what the article will argue. |
| 6 | Opening establishes subject and stakes. The reader knows the story and why it matters. The direction is implied but not stated. |
| 7 | Strong opening. Subject, stakes, and direction are all established by paragraph 3. The reader has a reason to continue. The opening contains at least one specific, concrete detail — a number, a quote, a specific decision. |
| 8 | The opening does real work. It not only establishes subject, stakes, and direction but begins the argument. The first paragraph contains the thesis in embryo. The reader is intellectually engaged by paragraph 2. |
| 9 | The opening is the kind of writing that makes a professional reader forward the article to a colleague. It is specific, surprising, and authoritative. The reader is hooked by the first sentence. |
| 10 | The opening is memorable. A reader could paraphrase it days later. It achieves the voice guide's standard: "Start in the middle of something real — a number that surprised the market, a sponsor who had to choose between two bad options." |

### Common Failure Mode

The opening is a throat-clearing paragraph that could introduce any article: "The commercial real estate market continues to evolve as participants adapt to changing conditions." This tells the reader nothing and gives them no reason to continue. Score 2.

### Opening Requirements

An opening must, by paragraph 3:
1. Name the specific subject (company, property, transaction, decision)
2. State why the subject matters (stakes — what hangs in the balance)
3. Indicate the article's direction (thesis or question the article will address)

An opening should:
4. Contain at least one specific, concrete detail
5. Avoid abstract nouns that could apply to any transaction

---

## 13. Dimension 10: Sentence Quality

**Minimum for Publication: 6**
**Weight: 1.0x**

### What This Dimension Measures

The article's sentences are well-constructed, varied in length and structure, and free of prose defects. The reader is never pulled out of the argument by an awkward construction, a run-on sentence, or a string of identically structured sentences.

### Scoring Criteria

| Score | Criteria |
|-------|----------|
| 1–3 | Pervasive sentence-level problems: run-ons, fragments, subject-verb disagreement, garbled syntax. Sentences must be reconstructed to be understood. |
| 4–5 | Grammatically correct but monotonous. Every sentence is 18–22 words. Every paragraph has three sentences. The prose has no rhythm. |
| 6 | Generally competent. Sentence variety is present but inconsistent. Some paragraphs rhythmically flat. One or two sentences that should be split. No major errors. |
| 7 | Good sentence craft. Sentences vary in length and structure. Short sentences create emphasis. Longer sentences build across clauses. The reader is never confused by syntax. |
| 8 | Strong sentence craft. Rhythm is deliberate. Short sentences land. Complex ideas are expressed in clear sentences. No sentence makes the reader reread to understand. |
| 9 | Exceptional sentence craft. The prose has a voice — not generic "professional writing" but a specific sensibility. Sentence rhythm varies the way the voice guide specifies: "Short. Then longer, building across a series of clauses that accumulate evidence." |
| 10 | The sentence-level writing is a competitive advantage. The prose would not be out of place in a top-tier financial publication. A reader would notice the writing quality independently of the analytical quality. |

### Common Failure Mode

The drafting model produces grammatically correct but rhythmically dead prose. Every sentence is declarative. Every paragraph is three sentences. The reader's attention wanders not because the content is boring but because the prose offers no variation. Score 4.

### Rhythm Test

Count the words in 10 consecutive sentences. If the standard deviation is less than 3 words (all sentences are roughly the same length), rhythm is poor. If sentences vary from 4 to 35 words with no pattern, rhythm is chaotic. Effective rhythm has a deliberate pattern with strategic variation.

---

## 14. Dimension 11: Originality of Language

**Minimum for Publication: 6**
**Weight: 1.0x**

### What This Dimension Measures

The article uses language that is specific, fresh, and precise — not the generic vocabulary of financial journalism. It avoids cliché, jargon without explanation, and the dead metaphors that accumulate in business writing.

### Scoring Criteria

| Score | Criteria |
|-------|----------|
| 1–3 | Pervasive cliché and jargon. Entire paragraphs could be produced by a financial-writing mad-lib. No original phrasing. |
| 4–5 | Mostly generic phrasing with occasional specific language. The article reads like it was written by someone who has read a lot of CRE journalism but never walked an asset. |
| 6 | Some original phrasing. The article avoids the worst clichés ("in this environment," "going forward," "a tale of two cities"). Concrete language is used in at least half the paragraphs. |
| 7 | Frequent original phrasing. The article prefers specific words to generic ones ("Dominion's interconnection queue" rather than "infrastructure constraints"). Minimal cliché. |
| 8 | Language is consistently specific and fresh. The article has a vocabulary — it uses the actual terms of the sector precisely, not the watered-down versions that appear in general business coverage. |
| 9 | The language is a pleasure to read — not because it's ornate but because it's precise. Every word earns its place. No filler. No dead metaphor. No jargon without explanation. |
| 10 | The language is distinctive. A reader familiar with the Light Tower voice would recognize it. The article uses language the way a good analyst uses numbers — as a precision instrument. |

### Forbidden Phrases

These phrases are automatic flags. Their presence pulls down the score regardless of other qualities:

- "In today's rapidly evolving market..."
- "As we navigate these uncertain times..."
- "Unprecedented challenges and opportunities..."
- "A perfect storm of factors..."
- "At the end of the day..."
- "Going forward..."
- "In this environment..."
- "It remains to be seen whether..."
- "Only time will tell..."
- "The new normal..."

### What Counts as Original Language

- Naming the specific thing rather than the category ("Dominion Energy's interconnection queue" not "infrastructure constraints")
- Using financial terms precisely ("the mezzanine piece is effectively subordinated at 75% LTV" not "the capital stack has multiple layers")
- Concrete descriptions of real things ("a 450-acre parcel in Loudoun County's data center overlay district" not "a strategically located site")
- Verbs that describe a specific action ("Dominion's queue closed without awarding AWS an interconnection slot" not "AWS faced headwinds in securing power")

---

## 15. Dimension 12: Intellectual Honesty

**Minimum for Publication: 9**
**Weight: 1.5x**

### What This Dimension Measures

The article is honest about what it knows, what it doesn't know, what it infers, and what it assumes. It does not present interpretation as fact. It does not pretend confidence it doesn't have. It acknowledges counterarguments and unknowns.

This is the highest-weighted dimension alongside Factual Accuracy because intellectual dishonesty — even in a factually accurate article — erodes reader trust in the publication. A single article that presents speculation as certainty can damage credibility across the entire corpus.

### Scoring Criteria

| Score | Criteria |
|-------|----------|
| 1–3 | Actively dishonest. Presents speculation as fact. Attributes motives without evidence. Ignores obvious counterarguments. Makes predictions without stating assumptions. |
| 4–5 | Passively dishonest. Does not actively deceive but fails to distinguish between what is known and what is inferred. States inferences with the same confidence as reported facts. |
| 6 | Some honesty markers present (e.g., "appears to," "suggests that") but inconsistently applied. At least one instance where inference is presented as fact. |
| 7 | Generally honest. Distinguishes between reported facts and analytical interpretations in most cases. Acknowledges at least one significant unknown or counterargument. |
| 8 | Consistently honest. The reader always knows whether a statement is a reported fact, a calculation, an inference, or a judgment. The article preempts the strongest counterargument. |
| 9 | The article's intellectual honesty is a structural feature — not just hedged language but genuine epistemic clarity. The article tells the reader: here is what we know, here is what we think it means, here is what we don't know, and here is why the counterargument is worth considering. |
| 10 | The article's treatment of uncertainty is itself valuable to the reader. A professional could use the article's "unknowns" section as a research agenda. The article is trusted because it is honest. |

### Common Failure Mode

The article makes a strong thesis claim that goes beyond what the evidence supports. "AWS's decision signals a fundamental shift in data center site selection strategy" — when the article has one data point (this deal) and no evidence of a pattern. This is overclaiming. Score 4.

### Required Honesty Markers

An intellectually honest article will:

1. **Signal inference:** "This suggests that..." / "The implication is..." (not "This means that...")
2. **Acknowledge unknowns:** "What isn't clear from the announcement is..."
3. **Present counterarguments:** "The alternative reading is..."
4. **State assumptions:** "Assuming Dominion's queue timeline hasn't changed..."
5. **Qualify predictions:** "If current trends hold..." (not "The market will...")
6. **Admit limitations:** "One deal doesn't make a trend, but..."

The article doesn't need every marker in every paragraph. But across the article, these signals must be present.

---

## 16. Dimension 13: Reader Utility

**Minimum for Publication: 6**
**Weight: 1.2x**

### What This Dimension Measures

The article gives the reader something they can use — a question to ask, a number to watch, a deal to compare, a pattern to look for. The reader finishes the article with something they didn't have before: not just information, but a tool.

### Scoring Criteria

| Score | Criteria |
|-------|----------|
| 1–3 | No utility. The article provides information but no way to use it. The reader knows something they didn't know before but has no idea what to do with it. |
| 4–5 | Implied utility. A sophisticated reader could extract an implication, but the article doesn't help them do it. The reader has to do the work of figuring out what to do with the information. |
| 6 | At least one stated reader consequence. The article explicitly tells the reader something they should do, watch, ask, or compare based on the analysis. |
| 7 | Specific, actionable reader consequence. It is not generic ("investors should watch this trend") but specific ("investors with data center exposure should check their portfolio's exposure to Dominion Energy's interconnection queue timeline"). |
| 8 | Multiple specific reader consequences. The article serves different readers differently: an investor gets one takeaway, a lender gets another, an operator gets a third. |
| 9 | The reader consequence is the article's payoff. The analysis builds toward a specific, testable claim that changes how the reader will think about future transactions. The reader will use this article. |
| 10 | The article is a tool. A reader could take the article's framework and apply it to a different transaction, a different market, a different sector. The article teaches a way of thinking, not just a set of facts. |

### Common Failure Mode

The article ends with a generic conclusion: "This transaction highlights the continued strength of the [sector] market." This tells the reader nothing they can use. It is a summary, not a consequence. Score 3.

### What Counts as Reader Utility

- A specific number to watch in future announcements
- A question to ask when evaluating similar transactions
- A comparable transaction to benchmark against
- A regulatory date or process that will determine the outcome
- A pattern to look for in other companies' behavior
- A framework for analyzing similar situations
- A specific risk to monitor

### What Does Not Count

- "This trend bears watching" (without saying what to watch)
- "The market will be interesting to follow" (vacuous)
- "Time will tell" (content-free)
- "[Sector] remains attractive for investors" (generic)

---

## 17. Dimension 14: Conclusion Quality

**Minimum for Publication: 6**
**Weight: 1.0x**

### What This Dimension Measures

The article's conclusion does work — it doesn't just stop. It synthesizes the argument, delivers the reader consequence, and leaves the reader with a specific thought or question. The conclusion feels like the article's destination, not its expiration.

### Scoring Criteria

| Score | Criteria |
|-------|----------|
| 1–3 | No conclusion. The article stops mid-argument or trails off. The reader is left wondering if there's a missing paragraph. |
| 4–5 | A conclusion exists but does no work. It restates the topic without adding anything. "In conclusion, this is a significant transaction." |
| 6 | The conclusion summarizes the article's main point and delivers at least one specific takeaway. It provides closure. |
| 7 | The conclusion synthesizes rather than summarizes. It doesn't repeat the article's points — it shows what they add up to. It delivers a specific reader consequence. |
| 8 | The conclusion earns the article's final paragraph. It delivers an insight that could only come after the full analysis. The reader feels the article built toward this. |
| 9 | The conclusion is the strongest paragraph in the article. It crystallizes the thesis, delivers the consequence, and leaves the reader with a thought they'll carry into their work. |
| 10 | The conclusion is quoted. It is the paragraph a reader copies and sends to a colleague. It is the takeaway that becomes the reader's own opinion. |

### Common Failure Mode

The article ends with a paragraph that could be appended to any article: "As the market continues to evolve, participants will need to stay informed and adapt to changing conditions." This is not a conclusion. It is a signal that the writer ran out of things to say. Score 1.

### Conclusion Test

Remove the article's final paragraph. Does the article feel incomplete? If yes, the conclusion is doing its job. If no, the conclusion was filler.

---

## 18. Composite Score Calculation

### 18.1 Formula

Each dimension score (1–10) is multiplied by its weight. The weighted scores are summed and divided by the sum of weights to produce a weighted average:

```
Composite = Σ(dimension_score × weight) / Σ(weight)
```

### 18.2 Weights

| Dimension | Weight |
|-----------|--------|
| 1. Factual Accuracy | 2.0 |
| 2. Financial Understanding | 1.8 |
| 3. Analytical Originality | 1.5 |
| 4. Thesis Strength | 1.5 |
| 5. Incentive Analysis | 1.3 |
| 6. Use of Numbers | 1.2 |
| 7. Market Context | 1.2 |
| 8. Narrative Structure | 1.1 |
| 9. Opening Quality | 1.1 |
| 10. Sentence Quality | 1.0 |
| 11. Originality of Language | 1.0 |
| 12. Intellectual Honesty | 1.5 |
| 13. Reader Utility | 1.2 |
| 14. Conclusion Quality | 1.0 |
| **Total Weight** | **18.4** |

### 18.3 Example Calculation

An article scores:
- Factual Accuracy: 9 × 2.0 = 18.0
- Financial Understanding: 8 × 1.8 = 14.4
- Analytical Originality: 8 × 1.5 = 12.0
- Thesis Strength: 7 × 1.5 = 10.5
- Incentive Analysis: 7 × 1.3 = 9.1
- Use of Numbers: 8 × 1.2 = 9.6
- Market Context: 7 × 1.2 = 8.4
- Narrative Structure: 8 × 1.1 = 8.8
- Opening Quality: 9 × 1.1 = 9.9
- Sentence Quality: 7 × 1.0 = 7.0
- Originality of Language: 7 × 1.0 = 7.0
- Intellectual Honesty: 9 × 1.5 = 13.5
- Reader Utility: 7 × 1.2 = 8.4
- Conclusion Quality: 7 × 1.0 = 7.0

Sum of weighted scores = 143.6
Sum of weights = 18.4
Composite = 143.6 / 18.4 = **7.8**

All individual thresholds met (minimums: 9, 7, 7, 6, 6, 6, 6, 6, 7, 6, 6, 9, 6, 6). Composite 7.8 > 7.0. **PUBLISH.**

### 18.4 Hard Floor vs. Composite

An article must meet BOTH conditions:
1. Every dimension ≥ its individual minimum
2. Composite ≥ 7.0

A single below-threshold dimension blocks publication even if the composite is above 7.0. A composite below 7.0 blocks publication even if every dimension meets its individual threshold.

---

## 19. Scoring Process and Calibration

### 19.1 Automated Scoring Protocol

The LLM scorer receives:
1. The full article text
2. The scored rubric (this document)
3. The analytical brief (for factual accuracy verification)
4. Scoring instructions: "Score each dimension 1–10. For each score, provide a one-sentence justification that references specific content in the article. Do not produce impressionistic scores."

### 19.2 Human Calibration

Every 30 days, a human editor scores 10 randomly selected articles using the same rubric. The human scores are compared to the automated scores. If average absolute deviation across dimensions exceeds 1.5 points, the automated scoring prompt is recalibrated.

### 19.3 Score Drift Monitoring

The `scoring_recalibration.py` module tracks:
- Average score per dimension per month
- Score inflation/deflation trends
- Sector-specific scoring biases
- Model-specific scoring tendencies

If a dimension's average score drifts by more than 0.5 points in a month without a corresponding change in content quality (verified by human audit), the scoring weights for that dimension are recalibrated.

### 19.4 Edge Case: Stories With Limited Financial Content

For stories where the transaction has minimal financial disclosure (e.g., a lease renewal with no terms disclosed, a regulatory filing with no dollar amounts), Financial Understanding and Use of Numbers are scored on the article's honest treatment of the limitation:

- Score 6: The article acknowledges what financial information is missing and works with what's available.
- Score 3: The article pretends to analyze finances that aren't disclosed.
- Score 1: The article invents financial analysis.

The article is NOT penalized for missing information. It IS penalized for pretending information exists or ignoring the gap.

---

## 20. Integration with Pipeline Gate System

### 20.1 Editorial Review Stage (Stage 11)

The rubric is applied by the Editorial Review stage of the modular prompt architecture (Document 08). The review output includes the full dimension scoring and flags any below-threshold dimensions.

### 20.2 Final Revision Stage (Stage 13)

After revision, the rubric is reapplied. The article must pass BOTH the initial and post-revision rubrics:

| Gate | Applied By | Threshold | Action on Failure |
|------|-----------|-----------|-------------------|
| Gate 1 (post-draft) | Stage 11: Editorial Review | All dimensions ≥ minimum, Composite ≥ 7.0 | Return to Stage 13 for revision |
| Gate 2 (post-revision) | Stage 13: Final Revision | All dimensions ≥ minimum, Composite ≥ 7.0 | Second revision attempt (max 3) |
| Gate 3 (final) | Stage 13 after max 3 revisions | At least all minimums met; Composite ≥ 7.0 preferred but ≥ 6.5 accepted with flag | Human review if Composite < 7.0 |

### 20.3 Pre-Publication Human Gate

For Tier 1 stories, a human editor reviews:
1. All dimension scores and justifications
2. The three lowest-scoring dimensions
3. The analytical brief vs. the final article
4. A spot-check of 5 fact claims against sources

The human editor can override an automated score by ±2 points with a written justification. The human score replaces the automated score in the composite.

### 20.4 Post-Publication Audit

Published articles are periodically re-scored against the rubric by a different model and (sampled) by a human reader. The re-scoring identifies:
- Scoring model drift (systematic over-scoring or under-scoring)
- Content quality trends over time
- Articles that should be revised or retracted
- Prompt improvements needed for specific dimensions
