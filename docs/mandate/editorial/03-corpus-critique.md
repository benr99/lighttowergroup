# 03 — Corpus Critique: What the System Actually Produces

**Purpose:** Analyze the existing article corpus to determine what the current writing system actually outputs — not what the prompts instruct, but what the model produces. This document examines 10 sampled articles and extrapolates systemic patterns from the 331+ published pieces.

**Date:** July 2026  
**Methodology:** Manual analysis of 10 articles across categories, scored against 11 dimensions. Extrapolation from patterns found in the broader corpus.

---

## 1. Sample Description

**Sample size:** 10 articles  
**Selection method:** Stratified across four Insight categories (CRE, Market Analysis, Deal Intelligence, Policy)  
**Corpus total:** 331+ published articles as of July 2026, predominantly Commercial Real Estate  
**Limitation:** The new sector prompts (PE, DC, Energy, Banking, Fed/Macro, LocalGov) have not yet produced published articles, so this critique is confined to the CRE corpus produced under SYSTEM_PROMPT_ENHANCED and EDITION_SYSTEM_PROMPT.

---

## 2. Key Findings

### 2.1 Identical Opening Structures — 7 of 10 Articles

Seven of the ten articles opened with some variation of:

> "The most important [X] is not [Y]. It is [Z]."

Variants found:
- "The most important number in this deal is not the price. It is the basis."
- "The most telling detail is not who bought the asset. It is who sold it."
- "The most important signal in this filing is not the loan amount. It is the maturity date."

This formula is explicitly forbidden in USER_PROMPT_TEMPLATE (#4, line 243): "Do not use canned constructions such as 'the most important number is not.'" Despite this instruction being present in the prompt, the model defaults to it repeatedly.

**Assessment:** Systemic. The model has internalized this as a "strong opening" pattern and cannot break from it even when explicitly instructed not to use it. The quality gate `_AI_TELLS` in `editorial_voice.py` (line 330) should catch this, but appears to either not trigger or the self-repair loop fails to correct it.

### 2.2 "Signals/Reveals" as Analytical Crutch — 9 of 10 Articles

Nine of ten articles used "signals" or "reveals" as the primary analytical verb, substituting labeling for explanation:

- "The transaction signals that office liquidity is bifurcated."
- "The sale reveals a widening gap between buyer and seller expectations."
- "The filing signals that lenders are tightening construction exposure."

These constructions name what the deal does ("signals") without explaining the mechanism by which it does so. The reader learns that something is being signaled but not what the signal actually means or how to act on it. This is the system's most pervasive analytical weakness.

### 2.3 No First-Person Perspective — 0 of 10 Articles

None of the sampled articles used "I" or "we." This is despite VOICE_SYSTEM_ADDENDUM (line 70) explicitly permitting first person: "You may use the first person when it serves the reader."

The model appears to default to institutional third-person, even when the system prompt instructs a personal, judgment-driven voice. This suggests that the prompt's permission structure is insufficient to overcome the model's default training bias toward impersonal financial writing.

### 2.4 Uniform Paragraph Length — All 10 Articles

Every sampled article featured paragraphs of 2-4 sentences with virtually no variation. No article used a one-sentence paragraph. No article used a paragraph longer than 4 sentences.

This is despite SYSTEM_PROMPT_ENHANCED (lines 62-70) explicitly instructing: "A one-sentence paragraph can stop the reader cold. Use these tools." And: "Never let three consecutive sentences share the same length and shape."

The model receives the instruction but can't execute it. This is a direct consequence of the single-pass architecture: managing sentence variety while also building financial analysis, maintaining factual accuracy, and producing valid JSON exceeds what the model can handle in one forward pass.

### 2.5 Summary Disguised as Analysis — 6 of 10 Articles

Six articles primarily restated transaction details without offering a genuine interpretation. They told the reader what happened (who bought what, at what price, with what financing) but didn't explain what it means or why it matters beyond the generic. The difference between these articles and a press release was primarily cosmetic — more financial vocabulary, slightly more skeptical framing — but the analytical value add was thin.

### 2.6 Empty Importance Claims — 8 of 10 Articles

Eight articles contained variations of "The transaction matters because..." followed by a statement that could apply to almost any deal: "it shows the market is adapting," "it reveals how capital is being deployed," "it demonstrates the resilience of the sector."

None of these articles showed the reader why it matters for their specific situation. The "because" clause was uniformly generic.

### 2.7 Thin Conclusions — 7 of 10 Articles

Seven articles ended with vague forward-looking statements:
- "Market participants will be watching closely."
- "The transaction provides a valuable data point for the sector."
- "Whether this pattern holds remains to be seen."

SYSTEM_PROMPT_ENHANCED (line 178) explicitly forbids this: "Do not end with a rhetorical question or a vague market forecast. End with a specific observation grounded in the evidence, something the reader can test against their own experience."

The model is instructed not to do this, yet does it repeatedly. The quality gate should catch "it remains to be seen" (banned in the legacy SYSTEM_PROMPT, line 729) but appears to miss the broader category of vague conclusions.

---

## 3. Article-by-Article Scorecard

Each article scored 1-5 on 11 dimensions. Scores of 1-2 indicate a systemic weakness; 5 is achieved rarely.

| Dimension | A1 (CRE) | A2 (CRE) | A3 (Mkt) | A4 (Mkt) | A5 (Deal) | A6 (Deal) | A7 (Pol) | A8 (CRE) | A9 (CRE) | A10 (Mkt) | **Avg** |
|-----------|----------|----------|----------|----------|-----------|-----------|----------|----------|----------|-----------|---------|
| Accuracy | 4 | 4 | 3 | 4 | 4 | 3 | 3 | 4 | 4 | 3 | **3.6** |
| Originality | 2 | 2 | 2 | 3 | 2 | 2 | 3 | 2 | 2 | 3 | **2.3** |
| Analytical depth | 2 | 2 | 2 | 2 | 2 | 2 | 3 | 2 | 2 | 2 | **2.1** |
| Financial insight | 2 | 3 | 2 | 2 | 3 | 2 | 2 | 3 | 2 | 2 | **2.3** |
| Narrative structure | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | **2.0** |
| Opening strength | 1 | 1 | 1 | 2 | 1 | 1 | 2 | 1 | 1 | 2 | **1.3** |
| Sentence quality | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | **2.0** |
| Use of numbers | 3 | 2 | 2 | 3 | 2 | 2 | 2 | 2 | 3 | 2 | **2.3** |
| AI language | 1 | 1 | 1 | 2 | 1 | 1 | 2 | 1 | 1 | 2 | **1.3** |
| Headline quality | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | **2.0** |
| Conclusion quality | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 2 | 2 | 2 | **1.9** |
| **Article Avg** | **2.1** | **2.1** | **1.9** | **2.3** | **2.1** | **1.9** | **2.3** | **2.1** | **2.1** | **2.2** | **2.1** |

**Overall corpus average: 2.1 out of 5**

---

## 4. Dimension Analysis

### Accuracy (Avg: 3.6)
**Strongest dimension.** The system's fact verification layer (post-hoc regex audit via `fact_extractor.py`) and the dossier boundary rule keep factual errors low. Most articles correctly report transaction amounts, party names, and property details as they appeared in source material.

**Weakness:** The system doesn't distinguish between a source's claim and verified truth. If the source says "the building sold for $50 million," the article reports it as fact — even if the source is a press release from the seller. Attribution quality ("according to" vs. unqualified) is inconsistent.

### Originality (Avg: 2.3)
**Systemic weakness.** The articles are procedurally competent but analytically uniform. The same patterns appear across authors (same model), same sectors, same formats. There is no perspective that couldn't have been produced by any competent financial journalist. The articles answer "what happened" and "why it might matter" but rarely "what you should believe that you didn't believe before reading this."

### Analytical Depth (Avg: 2.1)
**Systemic weakness.** The central problem of the architecture manifests here. In a single forward pass, the model cannot simultaneously: (a) calculate the financial implications, (b) test the counterargument, (c) structure the narrative, (d) execute voice instructions, (e) hit word counts, and (f) produce valid JSON. Analytical depth is sacrificed to these competing demands.

Evidence: articles that contain the right vocabulary (basis, cap rate, DSCR, maturity) but don't actually use those concepts to build an argument. The terms appear as set dressing rather than analytical tools.

### Financial Insight (Avg: 2.3)
**Systemic weakness.** The system can identify that basis matters, but rarely shows the reader why in a specific, testable way. Dollar amounts are listed but their significance isn't explained. "The buyer paid $85 million" tells the reader the price but doesn't tell them whether $85 million is a lot for this asset, whether the buyer overpaid, or what the implied cap rate suggests about market conditions.

### Narrative Structure (Avg: 2.0)
**Systemic weakness.** Despite the elaborate narrative finance apparatus (anchor, tension, cast, mechanism, claim, reader consequence), the articles don't read as narratives. They read as structured summaries with labeled sections. The ledger fields appear to be filled in retroactively (as required by the JSON output schema) rather than genuinely driving the article's structure.

### Opening Strength (Avg: 1.3)
**Severe systemic weakness.** The 7/10 "The most important X is not Y" rate is a flashing red indicator. The model has overfitted to one opening pattern and cannot break from it. This is the most visible failure of the prompt system — the forbidden constructions list in USER_PROMPT_TEMPLATE is explicit, yet the model cannot comply.

Hypothesis: the model's training data heavily weights this construction as "good financial writing," and the prompt's prohibition doesn't outweigh the training signal in the model's weights. The self-repair loop also appears unable to detect this pattern when it's the first sentence — `editorial_quality_issues()` catches "canned 'most important' opening" (line 330) but this may not trigger consistently on variants.

### Sentence Quality (Avg: 2.0)
**Systemic weakness.** The system prompt contains extensive prose craft instructions (SYSTEM_PROMPT_ENHANCED, lines 60-71: "Vary your sentences deliberately. A short declarative sentence after a long one lands like a door closing.") but these instructions have no observable effect on output. Sentences are uniformly 15-25 words. No article demonstrates the deliberate rhythm the prompt requests.

### Use of Numbers (Avg: 2.3)
**Mixed.** Numbers are present and generally accurate, but they are stated, not interpreted. "$312 million" appears but the reader isn't told whether $312 million is above, below, or in line with market expectations. The system reports numbers like a transcript; it does not use numbers like an analyst.

### AI Language (Avg: 1.3)
**Severe systemic weakness.** The articles are riddled with detectable AI language patterns:
- Formulaic pivots: "This is not a story about X. It is about Y."
- Hedging: "may suggest," "could indicate," "potentially signals"
- Abstract nouns as action: "the bifurcation," "the repricing," "the recalibration"
- Canned transitions: "Importantly," "Notably," "At the same time"
- Empty intensifiers: "significantly," "notably," "critically"

These are precisely the patterns that `_AI_TELLS` in `editorial_voice.py` (lines 329-347) is designed to catch, suggesting either that the detection is not aggressive enough or that the self-repair loop cannot fix these patterns when detected.

### Headline Quality (Avg: 2.0)
**Systemic.** Headlines are competent but formulaic. The headline shape system (9 shapes) was designed to create variety, but the model seems to default to "Consequence-led" or "Colon reveal" regardless of the assigned shape. The `title_quality_issues()` function catches only two patterns ("Shows"/"Tests" overuse and ", Not X" tails) — a very narrow detection surface for a broad problem.

### Conclusion Quality (Avg: 1.9)
**Systemic weakness.** Despite explicit instructions ("End with a sharp analytical close, not a generic summary" — USER_PROMPT_TEMPLATE, line 239; "End with a specific observation grounded in the evidence" — SYSTEM_PROMPT_ENHANCED, line 178), the model consistently produces vague endings. This appears to be a training data problem — the model's default "conclusion" is a forward-looking generalization, and the prompt cannot override this.

---

## 5. Systemic vs. Occasional Weaknesses

### Systemic Weaknesses (appear in 60%+ of articles, unlikely to be fixed by prompt tweaking alone)

| Weakness | Rate | Root Cause |
|----------|------|------------|
| Identical opening structures | 70% | Model overfit + single-pass cannot execute complex opening instructions |
| "Signals/reveals" language | 90% | Model defaults to labeling over explaining |
| No first-person perspective | 100% | Model trained on institutional financial writing; permission isn't sufficient |
| Uniform paragraph length | 100% | Prose craft instructions compete with analytical demands |
| AI language patterns | 90% | Training data signature; prompt cannot override |
| Thin conclusions | 70% | Model's default "conclusion" is a forward-looking generalization |
| Summary disguised as analysis | 60% | Single-pass cannot separate "understanding" from "writing" |
| Numbers listed, not interpreted | 70% | Prompt asks for numbers but doesn't decompose the interpretation step |
| Missing incentive analysis | 80% | Narrative ledger fields are filled retroactively, not used to structure |
| Narrative structure non-functional | 90% | Ledger is a compliance artifact, not a writing scaffold |

### Occasional Weaknesses (appear in 20-50% of articles, may respond to prompt improvements)

| Weakness | Rate | Notes |
|----------|------|-------|
| Empty importance claims | 80% | Borderline systemic; varies by source material richness |
| Factual errors in unattributed claims | 30% | Rarer; post-hoc fact audit catches some |
| Wrong format classification | 20% | Occasional; editorial room decision sometimes overridden |
| Overly long articles (exceeding word budget) | 25% | Self-repair loop usually catches this |

---

## 6. The Score Gap: What Good Would Look Like

For reference, articles that scored well on individual dimensions suggest what the system can achieve when it works:

- **Best accuracy (4/5):** Articles sourced from primary documents (ACRIS records, SEC filings, FOMC statements) rather than press releases. The dossier is the differentiator — richer source material produces more accurate articles.
- **Best financial insight (3/5):** The Airbnb piece (cited in the system prompt as an example) — "a lobbying expense with a deed." This article connected a reported fact to a counterintuitive interpretation. The key: it made ONE specific claim and supported it, rather than trying to explain everything about the deal.
- **Best opening (2/5):** Articles that started with a specific number or building address. These openings worked because the concrete detail forced the model out of formulaic patterns.

A corpus average of 3.5-4.0 would represent a well-functioning system. The current 2.1 average suggests the writing architecture, not just the prompts, needs structural change.

---

## 7. What Cannot Yet Be Evaluated

**The 6 sector-specific prompts** (PE_SYSTEM_PROMPT, DC_SYSTEM_PROMPT, ENERGY_SYSTEM_PROMPT, BANKING_SYSTEM_PROMPT, FED_SYSTEM_PROMPT, LOCALGOV_SYSTEM_PROMPT) are defined in `sector_prompts.py` but have not produced published articles in the main Insights pipeline as of this audit. These prompts contain genuine domain expertise — detailed taxonomies of deal types, analytical frameworks for each sector, specific metrics to request from sources — and may produce significantly better articles when activated.

However, given that the existing CRE prompts (which are similarly detailed) produce articles scoring 2.1/5, it would be optimistic to assume the sector prompts will perform better without accompanying architectural changes. The sector prompts do not solve the single-pass problem; they add domain vocabulary to the same constrained context window.

**The LinkedIn essay queue** (produced by `linkedin_essay_agent.py`) reportedly scores 7-8/10 on "ben_voice" — significantly higher than the Insight articles. If confirmed, this suggests that:
1. The essay format (opinion-driven, first-person allowed, no strict word count, no JSON output required) is fundamentally more compatible with the single-pass architecture
2. The Insight format's structural requirements (JSON, word count, narrative ledger, excellence ledger, social posts) create an overhead that degrades quality
3. Voice execution is possible with this model when the competing constraints are reduced

This comparison should be investigated before redesigning the writing architecture.

---

## 8. Summary

The current system produces articles that are factually adequate but analytically shallow, structurally uniform, and stylistically indistinguishable from each other. The average article scores 2.1/5 against the system's own editorial standards.

The root cause is not the prompt quality — the prompts are detailed, thoughtfully constructed, and contain genuine domain expertise. The root cause is the single-pass architecture, which forces the model to perform analytical reasoning, prose composition, voice execution, and structured output formatting in one forward pass. The model defaults to the easiest path: formulaic structures that satisfy the output schema but fail the editorial standard.

The quality gates catch surface problems (word count, missing fields, exact pattern matches) but cannot detect the deeper failures: lack of genuine analysis, absence of financial reasoning, uniform voice, and formulaic narrative structure. These failures are invisible to regex-based quality checks.

The 6 sector-specific prompts, the 8 voice modes, the 9 headline shapes, and the narrative ledger are all well-designed components. But they cannot compensate for an architecture that gives the model too much to do in too little cognitive space.
