# 04 — Failure Patterns: Common Writing and Reasoning Failures

**Purpose:** Document the most common and damaging failure patterns in the current writing system, categorized by type, with root cause analysis and prevalence estimates. This is a diagnostic document — it describes what goes wrong and why, not how to fix it.

**Date:** July 2026  
**Basis:** Analysis of 10 sampled articles + extrapolation from system architecture + quality gate logs + prompt behavior analysis

---

## 1. Pattern Taxonomy

The 12 failure patterns documented below are organized from most visible to most structural. Patterns 1-5 are surface-level (visible in the prose). Patterns 6-10 are analytical (visible in the reasoning). Patterns 11-12 are architectural (visible only in the system design).

---

## PATTERN 1: Identical Opening Structures

**Category:** Surface — Prose  
**Prevalence:** 7/10 analyzed articles (70%)  
**Quality gate coverage:** `_AI_TELLS` line 330 catches this pattern, but detection may be failing on variants  

**Description:**
The model defaults to one opening structure and applies it mechanically, even when explicitly instructed not to:

> "The most important [X] is not [Y]. It is [Z]."

**Variants observed:**
- "The most important number in this [deal/filing/transaction] is not [A]. It is [B]."
- "The most telling [detail/signal] is not [who/what]. It is [why/how]."
- "The most significant [aspect/element] of this [event] is not [X]. It is [Y]."

**Why it happens:**
1. The model's training data heavily weights this as "strong financial writing"
2. The instruction structure (paragraph 1: grab attention, paragraph 2: introduce tension, paragraph 3: state thesis) maps naturally to "Here's the surface thing. It's not the real thing. Here's the real thing."
3. The single pass means the model picks the first opening that "works" — satisfies "start with tension/contradiction" — and cannot iterate
4. The self-repair loop's prohibition detection (`_AI_TELLS`) may not trigger on syntactic variants

**Root cause:** The prompt cannot override the model's training bias toward this structure. Even an explicit prohibition ("Do not use canned constructions such as 'the most important number is not'") fails because the model processes the instruction and the pattern in the same forward pass, and the pattern is more deeply weighted.

---

## PATTERN 2: "Signals/Reveals" as Analytical Crutch

**Category:** Surface — Prose / Analytical  
**Prevalence:** 9/10 analyzed articles (90%)  
**Quality gate coverage:** `_AI_TELLS` line 342 catches "X signals/reveals Y" pattern  

**Description:**
The model substitutes labeling verbs ("signals," "reveals," "highlights," "demonstrates," "underscores") for actual explanation. Instead of walking the reader through the mechanism, it names the conclusion:

| What the article says | What it should say |
|----------------------|-------------------|
| "The sale signals that office liquidity is bifurcated." | "The buyer paid $185/ft. Three months ago, a similar building three blocks away traded at $310/ft. The spread between these two transactions — $125 per square foot — suggests lenders are pricing trophy buildings and commodity offices as different asset classes." |
| "The filing reveals a widening gap between buyer and seller expectations." | "The seller listed at $42M. The buyer closed at $31M. The 26% discount from ask — the widest spread in the submarket since Q4 2024 — means either the seller's basis was too high or the buyer's cost of debt made any price above $31M uneconomic." |

**Why it happens:**
1. "Signals" is a one-word analytical shortcut — the model can produce a complete analytical sentence without doing any analysis
2. The pattern is syntactically simple: [Subject] [signals/reveals] [conclusion]. The model can fill this template with any deal + any market observation
3. In the single pass, this is a computationally cheap way to satisfy the "explain what it means" instruction without expending tokens on actual explanation

**Root cause:** The model is incentivized to produce "analytical-sounding" output (to satisfy the prompt) rather than actual analysis (which would require multi-step reasoning the single pass cannot provide).

---

## PATTERN 3: Summary Disguised as Analysis

**Category:** Analytical  
**Prevalence:** 6/10 analyzed articles (60%)  
**Quality gate coverage:** None — regex cannot detect this  

**Description:**
The article restates what happened using financial vocabulary, creating the appearance of analysis without delivering it:

| Summary disguised as analysis | What it really is |
|------------------------------|-------------------|
| "The sponsor secured a $45M refinancing at SOFR+275, reflecting the lender's confidence in the asset's stabilized cash flows." | A restatement of the refinancing event with a motive-attribution wrapper ("reflecting the lender's confidence") that the sources don't support |
| "The acquisition represents a strategic expansion into the Sun Belt, capitalizing on demographic tailwinds." | A restatement of the acquisition with generic strategic rationale |
| "The CMBS delinquency rate declined 15bps, suggesting the special servicing pipeline is absorbing distressed loans faster than new defaults are entering." | A restatement of the data point with a plausible-but-unverified causal chain |

**Why it happens:**
1. The model needs to produce 800-1,050 words. Restating facts with interpretive wrappers fills the word count
2. Genuine analysis would require: identifying which fact matters most, testing alternative explanations, connecting to market mechanics, and drawing a defensible conclusion — all of which exceed what a single pass can do
3. The quality gates check for missing fields (narrative ledger, excellence ledger) but not for whether those fields contain genuine analysis vs. labeled restatement

**Root cause:** The system rewards output that looks complete (all fields filled, word count met) rather than output that actually analyzes. This is an inherent limitation of automated quality gates.

---

## PATTERN 4: No First-Person Perspective

**Category:** Surface — Voice  
**Prevalence:** 10/10 analyzed articles (100%), 331/331+ corpus (inferred)  
**Quality gate coverage:** None — quality gates don't check for first person  

**Description:**
Despite VOICE_SYSTEM_ADDENDUM explicitly permitting first person (line 70: "You may use the first person when it serves the reader"), the articles use zero first-person pronouns. Every article is written in institutional third person.

**What the prompt says:**
> "I'd watch this lender's next deal" or "My read is that the buyer is pricing in a rate cut" is acceptable when followed by a source-grounded reason.

**What the model produces:** Never "I," never "we," never "my read is." Always "the transaction," "the market," "the lender."

**Why it happens:**
1. The model's training data overwhelmingly associates financial writing with impersonal, institutional voice
2. The prompt's permission for first person is buried inside a 550-word addendum, competing with hundreds of other instructions
3. "Sound like one informed person with judgment" (EDITION_SYSTEM_PROMPT) is an abstract instruction; "use first person" is a concrete one — but the model doesn't treat them as equivalent
4. The self-repair loop has no check for "should have used first person" — it's not a quality gate criterion

**Root cause:** Permission is not instruction. The model defaults to its training bias toward impersonal financial writing. A permission buried in the voice addendum cannot overcome that bias.

---

## PATTERN 5: Uniform Paragraph Length

**Category:** Surface — Prose  
**Prevalence:** 10/10 analyzed articles (100%)  
**Quality gate coverage:** None — no paragraph-level rhythm check  

**Description:**
Every sampled article had paragraphs of 2-4 sentences with no variation. No one-sentence paragraphs. No paragraphs longer than 4 sentences. The prose moves at one speed.

**What the prompt says:**
> "A one-sentence paragraph can stop the reader cold. Use these tools." (SYSTEM_PROMPT_ENHANCED, line 65)
> "Vary your sentences deliberately. A short declarative sentence after a long one lands like a door closing." (line 62)
> "Never let three consecutive sentences share the same length and shape." (line 67)

**What the model produces:** Mechanically uniform paragraphs. If the prompt says "1-4 sentences per paragraph" (USER_PROMPT_TEMPLATE, line 277), the model averages 3. If the instruction says "use short paragraphs," the model uses medium-short paragraphs — never actually short.

**Why it happens:**
1. Prose variation requires the model to think about rhythm at the same time as content, format, and accuracy — competing cognitive demands
2. The JSON output format discourages creative paragraph structuring — the model is focused on producing valid `<p>` tags, not crafting rhythm
3. The quality gates don't measure sentence or paragraph variety — it's a blind spot

**Root cause:** Prose craft instructions in the prompt are aspirational; they cannot compete with the model's default prose generation pattern when every other part of the prompt is imposing hard constraints (word count, structure, format, fields, JSON).

---

## PATTERN 6: Empty Importance Claims

**Category:** Analytical  
**Prevalence:** 8/10 analyzed articles (80%)  
**Quality gate coverage:** None — regex cannot detect unsupported importance claims  

**Description:**
Articles assert that something "matters" or "is significant" without showing the reader why or to whom:

- "The transaction matters because it provides a benchmark for the sector."
- "This filing is significant for what it reveals about lender appetite."
- "The deal is notable because of what it says about where the market is headed."

Every deal matters to someone. The question is: to whom, by how much, and through what mechanism? These articles never answer that question. They claim importance without demonstrating it.

**Why it happens:**
1. The prompt asks for "why it matters" — the model can satisfy this with a syntactic placeholder ("it matters because...")
2. Demonstrating importance requires: identifying the affected party, quantifying the impact, describing the mechanism — none of which can be templated
3. The excellence_ledger's `reader_consequence` field asks for "what a market participant should test" but the model often fills this with a generic statement rather than a specific, testable claim

**Root cause:** The model substitutes the form of an importance claim for its substance. "X matters because Y" is syntactically complete but analytically empty.

---

## PATTERN 7: Thin Conclusions

**Category:** Surface — Structure  
**Prevalence:** 7/10 analyzed articles (70%)  
**Quality gate coverage:** The SYSTEM_PROMPT forbids vague endings but no gate checks for them  

**Description:**
Articles end with statements that could conclude any article on any topic:

- "Market participants will be watching closely."
- "The transaction provides a valuable data point."
- "Whether this pattern holds remains to be seen."
- "The coming quarters will reveal whether this represents a genuine shift or a one-off event."

**What the prompt says:**
> "Do not end with a rhetorical question or a vague market forecast. End with a specific observation grounded in the evidence, something the reader can test against their own experience." (SYSTEM_PROMPT_ENHANCED, line 178)

**What the model produces:** Vague forward-looking statements that satisfy none of these requirements.

**Why it happens:**
1. The model's training data treats "what happens next" as the natural conclusion to any analytical piece
2. By the time the model reaches the conclusion, it has already expended its analytical "budget" on the body — the conclusion is an afterthought
3. A specific, evidence-grounded conclusion requires the model to have actually formed a judgment it can defend — which the single pass cannot reliably produce

**Root cause:** The model defaults to the training-data conclusion structure. The prompt says "don't do this" but doesn't give the model an alternative cognitive process for forming a sharp conclusion.

---

## PATTERN 8: AI Language Patterns

**Category:** Surface — Prose  
**Prevalence:** 9/10 analyzed articles (90%)  
**Quality gate coverage:** `_AI_TELLS` regex in `editorial_voice.py` (lines 329-347) — partial coverage  

**Common patterns found in the corpus:**

| Pattern | Example | Why it's AI |
|---------|---------|------------|
| Formulaic pivots | "This is not a story about office distress. It is about capital allocation." | The "not X, but Y" construction is a statistical artifact of LLM training — it's the most common way models learn to introduce contrast |
| Hedging by abstraction | "The transaction may suggest that market participants are reassessing their exposure." | "May suggest" hedges the claim into meaninglessness; "market participants" is an abstraction that names no one |
| Noun-verb reification | "The bifurcation is accelerating." "The repricing has begun." | Abstract nouns ("bifurcation," "repricing") are treated as agents capable of action — the passive voice of financial commentary |
| Canned transitions | "Importantly," "Notably," "At the same time," "In this context" | Filler transitions that signal "I am transitioning" without contributing content |
| Empty intensification | "significantly," "notably," "critically," "fundamentally" | Adverbs that claim importance without demonstrating it |

**Why it happens:**
1. These patterns are statistical artifacts of LLM training on financial journalism — the model learned them as "good writing" from its training corpus
2. The `_AI_TELLS` regex catches exact strings but misses variants (e.g., it catches "the most important" but not "the most significant")
3. Some patterns ("may suggest," "potentially indicates") serve a legitimate function — protecting the model from making unsupported claims — but are overused

**Root cause:** The model's output distribution is shaped by its training data. The prompt's "what not to do" section can suppress specific strings but cannot change the underlying distribution. The model substitutes one AI pattern for another.

---

## PATTERN 9: Numbers Listed, Not Interpreted

**Category:** Analytical  
**Prevalence:** 7/10 analyzed articles (70%)  
**Quality gate coverage:** Fact audit checks number accuracy, not interpretation quality  

**Description:**
Articles report dollar amounts, percentages, and dates accurately but don't explain what they mean:

**Article reports:** "The property sold for $85 million. The seller had acquired it in 2018 for $62 million."
**Article does not say:** Whether $85M represents a gain or loss in real terms, what the implied annual appreciation rate is, how it compares to the submarket average, or what it suggests about the buyer's underwriting assumptions.

**Article reports:** "The loan carries a rate of SOFR+325 with a 65% LTV."
**Article does not say:** Whether 65% LTV is conservative or aggressive for this asset type in this market, what the DSCR looks like at that rate, or what happens to the borrower's equity if cap rates expand 50bps.

**Why it happens:**
1. The prompt asks the model to "use" numbers but doesn't decompose what "using" means: select the most significant number, compare it to a benchmark, calculate the implied assumption, and state the conclusion
2. The model can accurately extract and reproduce numbers from the dossier but cannot, in a single pass, perform the multi-step reasoning required to interpret them
3. Interpretation requires domain-specific calculation (cap rate = NOI / price; implied appreciation = (sale - purchase) / purchase / years) — the model can do the math if instructed, but the prompt doesn't ask for specific calculations

**Root cause:** The system treats numbers as evidence to be reported, not as inputs to be analyzed. The prompt's analytical sections ask for "explain the economics" without specifying which calculation would reveal the economic truth.

---

## PATTERN 10: Missing Incentive Analysis

**Category:** Analytical  
**Prevalence:** 8/10 analyzed articles (80%)  
**Quality gate coverage:** None — no gate checks for incentive analysis  

**Description:**
Articles typically describe what happened without explaining why each party acted as they did:

**Article reports:** "The sponsor extended the loan for 12 months rather than refinancing."
**Article does not say:** What the sponsor's alternatives were, what the extension cost vs. a refi would have cost, whether the extension preserved or destroyed equity value, or whether the lender agreed because the alternative (foreclosure) was worse.

**Article reports:** "The buyer is a joint venture between a regional operator and a pension fund."
**Article does not say:** Why this specific partnership structure, what each party brings (operator: expertise, pension fund: patient capital), what the governance structure implies about decision-making, or what conflicts are embedded in this structure.

**Why it happens:**
1. Incentive analysis requires the model to reason about counterfactuals ("what would X do if Y happened?") — a cognitive operation the single pass doesn't support
2. The narrative ledger's `cast` field asks for parties and their constraints but the model fills it with names, not incentive structures
3. The dossier provides facts about the deal, not the parties' internal decision-making — and the prompt correctly forbids inventing motives. But the result is that incentive analysis simply isn't done.

**Root cause:** The system's evidence boundary (dossier only) is correct journalistically but limits analytical depth. Without the ability to reason from reported facts to likely incentives (clearly labeled as inference), the articles can only report what happened, not why.

---

## PATTERN 11: Single-Pass Generation (Architectural)

**Category:** Architectural  
**Prevalence:** 100% of articles (by design)  
**Quality gate coverage:** Not applicable — this is the architecture, not a bug in it  

**Description:**
The system collapses reasoning and writing into one LLM call. The model receives a complex prompt package and must simultaneously:
1. Understand the financial meaning of the source material
2. Select what matters and what to omit
3. Build a logical argument
4. Execute the assigned voice mode
5. Follow the headline shape
6. Hit the word count
7. Vary sentence structure
8. Avoid forbidden constructions
9. Construct a narrative ledger
10. Produce valid JSON with 15+ required fields

**Consequences:**
- The model satisfices rather than optimizes — it does the minimum on each dimension to produce a passing output
- Analytical depth is the first thing sacrificed because it's the hardest to measure and the least visible in output validation
- Prose variety is the second thing sacrificed because JSON-valid output is the hard constraint
- The result is an article that passes all quality gates (word count, required fields, source URLs) but fails the editorial standard (insight, voice, analytical rigor)

**Why it's a pattern not a feature:**
The prompt system is built as if the model has unlimited cognitive capacity to execute all instructions simultaneously. It does not. Every additional instruction (voice mode, headline shape, narrative ledger, excellence ledger, word count, forbidden constructions, JSON format) consumes cognitive resources that could have gone to analysis.

---

## PATTERN 12: The Editorial Room Plan Is Advisory, Not Structural (Architectural)

**Category:** Architectural  
**Prevalence:** 100% of edition-mode articles  
**Quality gate coverage:** None — the plan is advisory by design  

**Description:**
The editorial room (`run_editorial_room()`) is a separate LLM call that produces a structured plan: angle, thesis, skeptic objections, human stakes, concrete detail. This plan is passed to the writing call as raw JSON text in the user prompt. But the writing model treats it as context, not as structure.

**What the plan provides:**
```json
{
  "angle": "The basis, not the price, reveals the real transaction economics",
  "favored_thesis": "The seller took a loss to solve a maturity problem, not because the asset declined",
  "skeptic_objections": ["The reported price may not reflect the true economic consideration"],
  "human_stakes": "The limited partners in the seller's fund are absorbing a markdown",
  "concrete_detail": "The seller bought at $62M in 2018 and sold at $85M in 2026"
}
```

**What the article does with it:**
- The angle is mentioned in passing rather than used to structure the argument
- The thesis appears somewhere in paragraph 3 but isn't tested throughout the article
- The skeptic objections are mentioned in one sentence and then ignored
- The human stakes are generic ("investors are watching") rather than specific ("the LPs in Fund III are absorbing a markdown on their 2018 vintage")
- The concrete detail is used as the opening fact but then abandoned

**Why it happens:**
1. The plan arrives as text, not as a structural scaffold. The writing model has to "read" the plan and decide how to use it — in the same forward pass where it's also writing the article
2. There's no enforcement mechanism — nothing in the article generation process checks whether the article actually follows the editorial room plan
3. The excellence_ledger's fields (why_now, original_inference, counterargument, concrete_detail, human_stakes) are designed to mirror the plan, but they're filled by the same model that received the plan — creating a circular self-assessment

**Root cause:** The editorial room and the writing model are the same model (`deepseek-chat`), just called separately. The plan has no more authority than any other part of the prompt. The writing model can, and does, deviate from the plan when it finds an easier path to a valid JSON output.

---

## 2. Failure Pattern Interaction Map

These patterns don't operate in isolation. They form a cascade:

```
Single-pass generation (Pattern 11)
    │
    ├── Model satisfices across all dimensions
    │
    ├──► Analytical depth sacrificed first (Pattern 3, 6, 9, 10)
    │       │
    │       └──► "Signals/reveals" used as shortcut (Pattern 2)
    │              │
    │              └──► Empty importance claims (Pattern 6)
    │
    ├──► Prose variety sacrificed second (Pattern 5)
    │       │
    │       ├──► AI language patterns dominate (Pattern 8)
    │       └──► Uniform openings default (Pattern 1)
    │
    ├──► Voice execution sacrificed third (Pattern 4)
    │
    ├──► Structure defaults to training bias (Pattern 7)
    │
    └──► Editorial room plan underutilized (Pattern 12)
```

The cascade explains why prompt improvements alone cannot fix the system. Adding more prose craft instructions to the prompt increases the cognitive load, which worsens the satisficing behavior, which degrades output further. The system is at a local maximum: given the constraints of single-pass generation, the current output quality is about as good as it can get.

---

## 3. What the Self-Repair Loop Can and Cannot Fix

### Can Fix (surface issues detectable by regex or structural checks):
- Word count violations (too short or too long)
- Missing required JSON fields
- Missing narrative ledge fields
- Duplicate paragraph detection
- Exact AI tell matches (e.g., "the most important")
- Mojibake encoding damage
- Missing source URLs

### Cannot Fix (deeper issues requiring judgment):
- Whether the article actually analyzes rather than summarizes
- Whether the "signals/reveals" claim is supported by mechanism explanation
- Whether the conclusion is genuinely sharp or formulaically vague
- Whether numbers are interpreted or merely listed
- Whether incentives are traced or merely named
- Whether the voice sounds like one person or an institution
- Whether the narrative ledge drives the article or is filled in retroactively
- Whether the editorial room plan was followed or ignored

**The self-repair loop is a spell-checker, not an editor.** It catches compliance problems, not quality problems. This is not a bug — it's a limitation of regex-based quality gates operating on structured output.

---

## 4. Prevalence Summary

| Pattern | Prevalence | Detectable by Current Gates | Fixable by Self-Repair |
|---------|-----------|---------------------------|----------------------|
| 1. Identical openings | 70% | Partial (exact match only) | Maybe (if detected) |
| 2. "Signals/reveals" language | 90% | Partial (one pattern) | Limited |
| 3. Summary as analysis | 60% | No | No |
| 4. No first person | 100% | No | No |
| 5. Uniform paragraphs | 100% | No | No |
| 6. Empty importance claims | 80% | No | No |
| 7. Thin conclusions | 70% | No | No |
| 8. AI language patterns | 90% | Partial (exact matches) | Limited |
| 9. Numbers not interpreted | 70% | No | No |
| 10. Missing incentive analysis | 80% | No | No |
| 11. Single-pass generation | 100% | N/A (architectural) | N/A |
| 12. Plan is advisory | 100% | N/A (architectural) | N/A |

**Bottom line:** 4 of 12 patterns are at least partially detectable. 0 of 12 are reliably fixable by the current self-repair loop. The 8 patterns that are entirely invisible to quality gates are the ones that matter most for editorial quality.
