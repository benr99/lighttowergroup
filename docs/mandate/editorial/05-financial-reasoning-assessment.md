# 05 — Financial Reasoning Assessment: Does the System Understand Finance?

**Purpose:** Assess whether the current writing system actually reasons about finance — not whether it uses financial vocabulary, but whether it demonstrates genuine financial understanding in its output. This document distinguishes between financial literacy (using the right words) and financial reasoning (drawing defensible conclusions from financial data).

**Date:** July 2026  
**Assessment method:** Analysis of prompt design, output patterns, and the gap between what the system is instructed to do and what it can actually do in a single forward pass.

---

## 1. What "Understanding Finance" Would Mean for This System

For an automated writing system covering capital markets, genuine financial understanding would mean:

1. **Numeracy:** The ability to calculate financial metrics from reported data (cap rate from NOI and price, implied appreciation from purchase and sale prices, DSCR from NOI and debt service) and use those calculations to support claims.

2. **Causal reasoning:** The ability to trace a change in one variable (rate hike, zoning change, tenant departure) through the capital structure to its consequence for each party.

3. **Incentive analysis:** The ability to identify what each party in a transaction needs, fears, and is betting on, and to explain how the deal structure reflects those incentives.

4. **Benchmarking:** The ability to compare a specific number (cap rate, basis, LTV, spread) against a relevant benchmark (submarket average, historical range, peer transactions) and explain the significance of the deviation.

5. **Risk identification:** The ability to identify who bears what risk, in what amount, and under what conditions — and to explain why a particular risk allocation matters.

6. **Counterfactual reasoning:** The ability to ask "what would have happened if X were different?" and use the answer to sharpen the analysis.

---

## 2. Current System Capabilities: Strengths

### 2.1 The Narrative Ledger Forces Some Structure

The narrative ledger (anchor, tension, cast, mechanism, claim, reader consequence) is genuinely useful. It forces the model to identify six analytical components that a purely free-form article might skip:

- **Anchor** forces the model to ground the article in a specific reported fact — which prevents the most common failure mode of financial commentary (abstract generalization without evidence)
- **Tension** forces the model to identify what made this decision difficult — the pressure that makes the story worth telling
- **Cast** forces the model to name specific parties and their constraints — which should prevent "the market decided" abstractions
- **Mechanism** forces the model to name the specific financial tool or structure — which should prevent "because of market conditions" vagueness
- **Claim** forces the model to make a specific, bounded interpretation — which should prevent articles that say nothing
- **Reader consequence** forces the model to give the reader something testable — which should prevent empty conclusions

When the model genuinely uses the ledger to structure its thinking (rather than filling it in retroactively as a compliance requirement), the articles are better. The Airbnb piece cited in the system prompt ("a lobbying expense with a deed") is an example of the ledger working: the anchor is a reported filing, the tension is the gap between the physical use and the legal strategy, the cast is the owner and the city, the mechanism is property tax classification, the claim is that the owner is playing a jurisdictional game, and the reader consequence is that other owners in similar situations should examine their own classifications.

### 2.2 The Dossier Provides Source Facts for Verification

The research dossier (`build_research_dossier()` in `research_dossier.py`) extracts structured facts from source text: dollar amounts, percentages, company names, addresses, direct quotations. These facts are traceable to source URLs, which means:

- The model is not hallucinating numbers from its training data
- Every factual claim in the article should map to a dossier source
- The post-hoc fact audit (`audit_article_facts()` in `fact_extractor.py`) can verify this mapping

This is a genuine strength. Many automated content systems generate numbers freely; this one is constrained by source evidence.

### 2.3 The Editorial Room Asks for Angle and Skepticism

The editorial room prompt (`run_editorial_room()` in `editorial_room.py`) explicitly asks for:

- "materially different angles" (forces the model to consider multiple interpretations)
- "strongest skeptical objections" (forces the model to identify weaknesses in its own preferred angle)
- "human or institutional stakes" (forces the model to identify who is affected)
- "one source-grounded concrete detail" (forces the model to anchor the article in something real)

These are the right questions. The problem (as documented in Pattern 12) is that the answers to these questions are advisory — the writing model may or may not use them.

### 2.4 Some Articles Show Genuine Financial Insight

The corpus analysis found occasional flashes of genuine financial reasoning:

- The Airbnb article correctly identified a tax classification strategy as a financial optimization
- An article on a loan extension correctly noted that the extension preserved equity value that a forced sale would have destroyed
- An article on a basis play correctly identified that the buyer was pricing in a rate cut that the seller wasn't — and that this different assumption explained the price

These examples suggest that the model *can* reason financially when the conditions are right — specifically, when the dossier provides rich factual material, the editorial room plan is specific enough to guide the writing, and the article format doesn't impose excessive structural demands.

---

## 3. Current System Capabilities: Weaknesses

### 3.1 No Explicit Calculation of Financial Metrics

The system never calculates financial metrics. Not once in the analyzed corpus did an article contain a sentence like:

> "At $85 million and $5.1 million of trailing NOI, the implied cap rate is 6.0% — 75 basis points inside the submarket average of 6.75%."

Instead, articles report the numbers separately ("The property sold for $85 million. Net operating income was approximately $5.1 million.") without doing the arithmetic that connects them.

**Why this matters:** Financial analysis is fundamentally computational. The cap rate isn't a separate fact — it's the relationship between two facts. An article that reports the price and the NOI without computing the implied cap rate hasn't done financial analysis; it has done data transcription.

**Why it doesn't happen:**
1. The prompt doesn't ask the model to calculate. It asks the model to "explain the economics" but doesn't decompose "explain" into specific calculations
2. The model can do arithmetic, but in a single forward pass, computation competes with all the other demands on the model's attention
3. The dossier provides the raw numbers but not the calculated metrics — the model would need to identify which numbers to combine and perform the calculation itself
4. There's no quality gate that checks whether articles contain calculated metrics — the system doesn't know it's missing this

### 3.2 No Distinction Between Reported Figures and Calculated Ones

The system's fact/inference/unknown distinction (SYSTEM_PROMPT_ENHANCED, lines 143-158) addresses only the source of information, not the nature of the number:

- **REPORTED FACT:** "The property sold for $85 million." (from the press release)
- **INTERPRETATION:** "The seller took a loss." (inference from the reported facts)
- **OPEN QUESTION:** "The filing does not disclose the cap rate." (what the source doesn't say)

What's missing is a fourth category:

- **CALCULATED METRIC:** "At the reported sale price and trailing NOI, the implied cap rate is approximately 6.2%." (derived from two reported facts)

This category isn't reported (no source directly states the cap rate), isn't strictly interpretation (it's arithmetic, not judgment), and isn't an open question (the calculation is possible). It's a form of analysis that the system's epistemological framework doesn't accommodate.

### 3.3 Incentive Analysis Is Often Missing or Superficial

Articles name the parties but don't explain their incentives:

| What the article says | What a financially literate reader needs |
|----------------------|------------------------------------------|
| "The sponsor extended the loan for 12 months." | What was the sponsor avoiding (a forced sale at a loss? a capital call? a covenant breach?) and what did the extension cost? |
| "The lender agreed to the modification." | What did the lender get in exchange (a higher rate? a partial paydown? additional collateral? a personal guarantee?)? What was the lender's alternative (foreclose at a loss?)? |
| "The buyer is a joint venture." | What does each partner contribute (capital, expertise, deal flow, tenant relationships)? What conflicts are embedded (different hold periods, different return targets, different liquidity needs)? |

**Why it doesn't happen:**
1. The dossier rarely contains information about internal decision-making (which is correct — the system shouldn't invent motives)
2. But the system also doesn't do the analytical work of reasoning from reported structure to likely incentives
3. The narrative ledger's `cast` field asks for "Party: its need, constraint, or clock" but the model typically fills this with "Sponsor: needed to refinance" — a restatement, not an analysis
4. Incentive analysis requires the model to think about what each party *would have done* in alternative scenarios — a counterfactual reasoning task that's difficult in a single pass

### 3.4 Risk Transfer Is Not Traced Through the Capital Stack

When an article describes a transaction with a complex capital structure (senior debt, mezzanine, preferred equity, common equity), it typically reports each layer as a fact:

- "The capital stack includes $50M of senior debt, $15M of mezzanine, and $20M of equity."
- "The senior loan carries a rate of SOFR+275. The mezzanine piece was priced at 12%."

But it doesn't trace how risk flows through this structure:

- If occupancy drops 10%, who gets hurt first? (The equity, then the mezzanine, then the senior — but at what occupancy level does each tranche get impaired?)
- If rates rise 100bps, which tranche feels it? (The floating-rate senior — but the mezzanine is fixed, so the rate risk is concentrated in the senior lender)
- If the property sells at a loss, who absorbs how much? (The equity first, then the mezzanine — but is the mezz lender's recovery dependent on the senior lender's cooperation?)

**Why it doesn't happen:**
1. Tracing risk through a capital stack requires multi-step reasoning: condition → cash flow impact → tranche impact → party consequence
2. Each step requires domain knowledge (how mezzanine intercreditor agreements work, what triggers a springing guarantee, when a special servicer can block a mezzanine foreclosure)
3. The single-pass generation cannot handle this chain of reasoning while also managing prose, voice, and format

### 3.5 Market Context Is Generic

Most articles provide market context that could apply to any deal, in any market, at any time:

- "The transaction comes as the market continues to face headwinds."
- "Lenders remain cautious in the current environment."
- "The deal reflects the ongoing repricing of commercial real estate assets."

These statements are not false. They are true of every CRE transaction in 2024-2026. But they don't help the reader understand *this specific transaction* in *this specific market* at *this specific time*.

**What specific market context would look like:**
- "This is the third office sale above $200/ft in the Midtown submarket this quarter, compared to zero in Q2 2025. The submarket's average cap rate has compressed 50bps over that period, from 7.0% to 6.5%."
- "The lender's CRE concentration was 285% of total risk-based capital as of Q1 2026 — 15 points below the 300% threshold that typically triggers enhanced regulatory scrutiny. This loan brings the concentration to 292%."

**Why it doesn't happen:**
1. Specific market context requires data the dossier rarely contains (submarket cap rate trends, lender concentration ratios, comparable transactions)
2. The system correctly avoids inventing market statistics — but it doesn't fetch them either
3. The dossier is transaction-focused (facts about this specific deal) rather than market-focused (facts about the market this deal exists in)

### 3.6 The Central Financial Question Is Rarely Identified Before Writing

Every financial story has one question that matters most:

- For a sale: Did the seller make money or lose money on a risk-adjusted basis?
- For a refinancing: Did the new loan terms improve or worsen the sponsor's position?
- For a distress event: Who is absorbing the loss and how much is it?
- For a policy change: Who benefits, who pays, and by how much?
- For a fundraise: What does the LP commitment rate tell us about institutional appetite for this strategy?

The system has all the pieces to identify this question (the editorial room asks for angle and thesis, the narrative ledger asks for tension and claim) but the question is rarely stated explicitly in the article. Instead, the article describes the event and gestures at its significance, leaving the reader to figure out what they should actually conclude.

**Why it doesn't happen:**
1. The prompt asks the model to "lead with tension" and "state the hidden market signal" but doesn't ask "what's the one financial question this article answers?"
2. The editorial room's `favored_thesis` field is the closest thing to a central question, but it's often filled with a general observation rather than a specific question
3. Identifying the central question requires the model to prioritize — to decide that "did the seller lose money?" matters more than "what does this say about the market?" — and the single pass doesn't give the model room to prioritize

### 3.7 The "Why Now" Analysis Is Weak

SYSTEM_PROMPT_ENHANCED (line 30) asks: "Why did it happen now, and not six months ago or six months from now?"

This is an excellent question. But the articles rarely answer it well:

**Typical "why now" answer:** "The transaction comes as lenders are increasingly selective about office exposure."
**Why it's weak:** Lenders have been selective about office exposure for three years. Why did *this* lender fund *this* deal *this month*?

**A strong "why now" answer would be:** "The lender's Q2 earnings call revealed that its CRE portfolio's weighted average risk rating had improved for two consecutive quarters — the first time since 2022. The improvement gave the credit committee enough confidence to approve a new office loan, but only at the conservative 55% LTV that reflects the ongoing uncertainty."
**Why it's strong:** Specific institution, specific data point, specific mechanism (improved risk ratings → credit committee confidence → deal approval), specific constraint (55% LTV cap).

**Why it doesn't happen:**
1. Temporal analysis requires information the dossier rarely contains (prior quarter data, earnings call transcripts, credit committee policies)
2. The prompt asks "why now" but the model fills it with the most available answer (general market conditions) rather than a specific one
3. This is another instance of the single-pass satisfice problem: a generic answer is easier than a specific one, and the quality gates can't tell the difference

### 3.8 Counterarguments Are Rarely Acknowledged

The editorial room asks for "strongest skeptical objections" and the EDITION_USER_PROMPT_TEMPLATE requires "a counterargument." But in practice:

- Counterarguments appear in the excellence_ledger (as required by the JSON schema) but not in the article body
- When they do appear in the body, they're typically one sentence inserted near the end: "Of course, one transaction does not make a market."
- Genuine engagement with a counterargument — stating it fairly, examining the evidence for and against, and explaining why the article's interpretation is more likely — is almost entirely absent

**Why it doesn't happen:**
1. A genuine counterargument would require the model to argue against itself — a cognitively demanding task
2. The article format rewards certainty (thesis, evidence, conclusion) rather than genuine uncertainty (thesis, counterargument, reconciliation)
3. The prompt asks for a counterargument but doesn't specify where or how it should be integrated into the article's structure

---

## 4. What the System Prompt Gets Right About Finance

The SYSTEM_PROMPT_ENHANCED demonstrates genuine financial understanding on the part of its human authors. The five convictions (lines 122-139) are sophisticated financial insights:

> "Time is not a backdrop to a capital decision. It is often the most expensive ingredient in it."
> "Basis tells the truth before management does."
> "Structure survives cycles. Optimism does not."
> "Liquidity is not a market condition. It is a permission someone with capital decides to grant, or not."
> "Every 'yes' from a lender is actually 'yes, if.'"

These are genuine insights from someone who understands capital markets deeply. The problem is that the prompt can transmit these insights to the model as context, but the model cannot operationalize them — it can echo the philosophy but cannot apply it to a specific transaction.

The prompt also correctly identifies the specific metrics that matter for different story types:

- **Refinancings:** old rate, new rate, DSCR at each level (line 77)
- **Sales:** basis — what the seller paid, when, what they put in, what they sold for (line 82)
- **Distress:** maturity date, occupancy, debt yield, last appraisal (line 87)
- **Policy:** what one provision does to one specific deal (line 92)

These are the right analytical frameworks. But they are described, not operationalized. The prompt says "walk through the borrower's math" but doesn't tell the model how to structure that walk — what the steps are, what format the math should take, or how to ensure the calculation is correct.

---

## 5. What the Sector Prompts Get Right (That the Main Pipeline Doesn't Use)

The 6 sector-specific prompts (`sector_prompts.py`) contain significantly more domain-specific analytical instruction than the main SYSTEM_PROMPT_ENHANCED:

| Sector Prompt | What It Teaches the Model That the Main Prompt Doesn't |
|--------------|------------------------------------------------------|
| **PE_SYSTEM_PROMPT** | How to analyze fund close terms (hard cap, re-up rate, predecessor returns), deal-level metrics (entry multiple, quality-of-earnings adjustment, management rollover), exit analysis (holding period, MOIC, IRR, entry/exit multiple spread), and incentive structures (earnout triggers, promote waterfalls, GP commit percentages) |
| **DC_SYSTEM_PROMPT** | How to analyze power as the binding constraint (interconnection queue position, transmission upgrade requirements, utility timeline risk), how to distinguish spec development from build-to-suit from stabilized asset, and how to trace capital costs through different developer types |
| **ENERGY_SYSTEM_PROMPT** | How to analyze the spread between PPA price and cost of capital, how to model regulatory changes as counterparty actions, how to connect energy stories to CRE/banking/PE/datacenter implications |
| **BANKING_SYSTEM_PROMPT** | How to analyze bank portfolio metrics (CRE concentration, construction concentration, ACL, NPA, charge-off rate, CET1), how to trace regulatory actions through arithmetic to capital cost impact, how to distinguish bank lending from private credit economics |
| **FED_SYSTEM_PROMPT** | How to calculate the transmission of rate changes to cap rates, refinancing costs, construction loan interest carry, and bank balance sheets — with specific arithmetic for each channel |
| **LOCALGOV_SYSTEM_PROMPT** | How to translate zoning changes into revised pro forma assumptions (buildable square footage, FAR, height limits), how to calculate tax abatement NPV impact, how to identify whose spreadsheet needs updating and by how much |

**These are excellent prompts.** They contain the domain-specific analytical frameworks that the CRE-focused main prompt lacks. The banking prompt's instruction to "walk through the mechanism, show the reader the arithmetic" (line 302) is exactly the kind of instruction that would produce genuine financial reasoning rather than financial vocabulary.

**The tragedy:** These prompts are defined but not active in the main Insights pipeline. They exist in the codebase as unused potential. Even if they were activated, they would still face the same single-pass constraint — adding more domain instruction to the prompt might improve vocabulary specificity but wouldn't solve the fundamental problem that the model can't do multi-step financial reasoning in one forward pass.

---

## 6. The Financial Reasoning Ceiling

Given the current architecture, the system's financial reasoning ceiling is approximately:

| Financial reasoning task | Ceiling | Why |
|-------------------------|---------|-----|
| Report financial facts accurately | 4/5 | Dossier constraint + fact audit work well |
| Identify which facts are most significant | 2/5 | Model can flag important numbers but can't explain why they're important |
| Calculate derived metrics from reported facts | 1/5 | Not asked to, and single pass doesn't support it |
| Trace causal chains through capital structures | 1/5 | Requires multi-step reasoning the architecture doesn't provide |
| Compare specific numbers to relevant benchmarks | 1/5 | Benchmarks not in dossier, model can't fetch them |
| Identify who bears what risk in what amount | 2/5 | Can name parties, struggles to quantify exposure |
| Form a defensible, contestable financial conclusion | 2/5 | Can state a claim, rarely supports it with mechanism |
| Acknowledge and address counterarguments | 1/5 | Counterarguments are compliance artifacts, not genuine engagement |

**Overall financial reasoning score: 1.8/5**

This score reflects not the system's financial vocabulary (which is 4/5 — it uses the right terms) but its ability to perform the cognitive operations that constitute financial analysis: calculation, causal reasoning, benchmarking, risk tracing, and counterfactual testing.

---

## 7. The Gap Between Prompt Intent and Model Output

The prompt authors clearly understand finance deeply. The five convictions, the sector-specific analytical frameworks, the specific metrics for each story type — these are the work of someone who has analyzed real deals and knows what questions to ask.

The problem is that the model receives these sophisticated instructions in the same context window where it must also:
- Follow 9 headline shape instructions
- Follow 8 voice mode instructions
- Build a 10-field narrative ledger
- Build an 8-field excellence ledger
- Hit a specific word count
- Avoid 14+ forbidden constructions
- Maintain fact/inference/unknown distinction
- Produce valid JSON with 15+ fields
- Generate social posts

In that environment, "walk through the borrower's math" becomes just one more instruction among many — and not the one that will cause a JSON parsing error if ignored. The model prioritizes hard constraints over soft instructions, and financial reasoning is the softest instruction of all — because the quality gates can't detect whether it actually happened.

---

## 8. Summary

**What the system does well:**
- Reports financial facts accurately and with source attribution
- Uses correct financial vocabulary
- Identifies the analytical components of a financial story (via the narrative ledger)
- Contains prompt-level understanding of what matters in different transaction types

**What the system does poorly:**
- Calculates financial metrics from reported data
- Traces risk through capital structures
- Provides specific (rather than generic) market context
- Identifies and supports a central financial question
- Explains "why now" with specificity
- Engages with counterarguments genuinely
- Distinguishes reported figures from calculated metrics
- Performs the multi-step reasoning that constitutes financial analysis

**The root cause is architectural, not prompt-level.** The prompt contains excellent financial instruction. But the single-pass architecture gives the model too many competing demands, and financial reasoning — being the hardest demand to verify automatically — is the first thing sacrificed.

**The most promising path to improvement** is not better financial prompts (the prompts are already good) but an architecture that separates financial reasoning from prose generation — allowing the model to "think" about the financial meaning before it "writes" about it. This would mean: a dedicated reasoning step that calculates metrics, identifies the central financial question, traces incentives, and tests counterarguments — producing a structured analytical brief that the writing step then translates into prose.
