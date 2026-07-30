# 06 — Editorial Voice Guide: Current Definition and Proposed Refinements

**Purpose:** Document the Light Tower Group editorial voice as currently specified, assess where it succeeds and fails in practice, and propose refinements for a voice that can actually be executed given the system's architectural constraints.

**Date:** July 2026  
**Sources:** `VOICE_SYSTEM_ADDENDUM` (editorial_voice.py), `SYSTEM_PROMPT_ENHANCED` sections on voice and point of view (enhanced_prompts.py), corpus analysis of 10 Insight articles, reported LinkedIn essay queue performance

---

## 1. The Current Voice Specification

### 1.1 The Core Standard (VOICE_SYSTEM_ADDENDUM)

The Light Tower editorial voice is defined in `VOICE_SYSTEM_ADDENDUM` (`editorial_voice.py`, lines 38-91). It specifies:

**Authority through proximity:**
> "Write like you were in the room when the decision got made. Put the reader there with you."

**Prose authority:**
> "The prose should feel like someone who actually does this for a living — someone who has walked the asset, read the OM, sat through the lender call, and came away with an uncomfortable question the spreadsheet couldn't answer."

**Sentence rhythm:**
> "Vary your sentences the way a good conversation varies. Short. Then longer, building across a series of clauses that accumulate evidence before landing on a claim the reader didn't see coming. Let some paragraphs be one sentence. Let others run. The rhythm should breathe."

**Opening moves:**
> "Start in the middle of something real: a number that surprised the market, a sponsor who had to choose between two bad options, a building that traded at a price nobody predicted, a lender who said yes when everyone else said no."

**Financial mechanics explained:**
> "Explain complex financial mechanics by walking through them. If a deal involves a mezzanine piece, explain what the mezz lender was underwriting that the senior lender wasn't. If the basis tells the real story, show the reader the two numbers side by side and let them feel the spread."

**First person:**
> "You may use the first person when it serves the reader. 'I'd watch this lender's next deal' or 'My read is that the buyer is pricing in a rate cut' is acceptable when followed by a source-grounded reason. The first person is a shortcut to accountability — use it to claim your judgment, not to decorate the prose."

**Fabrication prohibition:**
> "Do not manufacture a site visit, a client call, a confidential conversation, a personal memory, or deal involvement. Do not imitate a named writer. Your voice is your own: informed, direct, unpretentious, occasionally dryly amused by the gap between what the press release said and what actually happened."

**Non-negotiable reporting rule:**
> "Put the reader there" means use a reported fact with vivid precision. It never means pretending to have seen the building, heard a call, read a private document, or known what an unquoted person thought."

**Lunch-break rhythm:**
> "Give the reader the point by paragraph three. Prefer clean verbs and concrete nouns to adjectives. Vary sentence length, use short paragraphs when they create pace, and explain unavoidable jargon on first use. The goal is pleasurable clarity, never theatrical color."

### 1.2 The Five Convictions (SYSTEM_PROMPT_ENHANCED)

The voice is also shaped by five editorial convictions that define the desk's worldview (SYSTEM_PROMPT_ENHANCED, lines 122-139):

1. **Time as cost:** "Time is not a backdrop to a capital decision. It is often the most expensive ingredient in it. Every deal has a clock. Find it."

2. **Basis as truth:** "Basis tells the truth before management does. What someone paid for an asset is the most honest statement they will ever make about what they think it's worth. Everything after that is narrative."

3. **Structure over optimism:** "Structure survives cycles. Optimism does not. The loan that worked at 3% SOFR might not work at 5%. Show the reader the math."

4. **Liquidity as permission:** "Liquidity is not a market condition. It is a permission someone with capital decides to grant, or not. When a lender says no, ask what they were protecting. When they say yes, ask what they had to believe."

5. **The "if" in every "yes":** "Every 'yes' from a lender is actually 'yes, if.' The interesting part is always the 'if.'"

### 1.3 The Voice Spectrum (8 Voice Modes)

The system defines 8 specific voice modes (`editorial_voice.py`, lines 143-184), each with a distinctive opening move and analytical stance:

| # | Mode | Opening Move | Stance |
|---|------|-------------|--------|
| 1 | Underwriting margin | Open on the specific assumption the deal required someone to believe | Walk through the underwriting the way a sponsor or credit officer would |
| 2 | Basis autopsy | Open on the spread between two prices — what someone paid and what someone sold for | Trace what the change in basis transferred between buyer, seller, and lender |
| 3 | Lender's-eye memorandum | Open on the question a credit committee would have asked — the uncomfortable one | Treat the lender as a risk manager making a specific bet |
| 4 | Counterparty map | Open on two people who need opposite things from the same deal | Map the incentives — who has leverage, time, alternatives |
| 5 | City in the balance sheet | Open on a physical fact — shadow, vacancy, old signage | Connect physical condition to the capital required to change it |
| 6 | Consensus under cross-examination | Open with what everyone said when the deal was announced, then produce the number that makes consensus uncomfortable | Test the market's reading against the numbers |
| 7 | Time as a cost of capital | Open on a clock: maturity date, deadline, rate lock expiration | Show how time — not rate, not basis — is the scarce resource |
| 8 | Operator's field note | Open with a plain, source-grounded observation a practitioner could make to a colleague | State the read plainly, walk through the reported mechanics |

---

## 2. Where the Voice Works

### 2.1 LinkedIn Essay Queue (Reported: 7-8/10 on "ben_voice")

The LinkedIn essay queue (`linkedin_essay_agent.py`) reportedly scores 7-8/10 on voice execution. If accurate, this is significant because it suggests the voice specifications *can* produce good output under different conditions.

**Why the essays may work better:**
1. **No JSON output requirement.** The essay format doesn't demand structured fields, narrative ledgers, or excellence ledgers. The model can focus on prose.
2. **Opinion-driven format.** LinkedIn essays are designed for first-person, judgment-driven writing. The "you may use first person" permission becomes an expectation, not just a permission.
3. **No strict word count.** The essay format has length guidelines, not hard constraints. The model doesn't expend cognitive effort managing word count.
4. **Single-focus writing.** An essay makes one argument. The model doesn't have to simultaneously produce an article, a narrative ledger, an excellence ledger, data points, source attribution, and social posts.
5. **Different prompt structure.** The essay prompt likely has fewer competing instructions, allowing the voice instructions to carry more weight.

**Implication:** The voice specification is sound. The problem is not what the voice asks for but the environment in which it's asked. The Insight article format imposes structural demands that crowd out voice execution.

### 2.2 Occasional Bright Spots in the Insight Corpus

The corpus analysis found occasional articles that partially achieved the specified voice:
- Articles that opened with a specific building address had more concrete, grounded prose
- Articles sourced from primary documents (ACRIS, SEC filings) rather than press releases had more analytical texture
- Articles in the Deal Tape format (0-80 words) often had sharper, more specific language than full-length pieces — suggesting that compression forces discipline

### 2.3 The Prompts Themselves

The voice prompts are well-written. They demonstrate the very qualities they ask for: concrete nouns ("the building at 350 Park Avenue"), specific scenarios ("the sponsor who needed another six months"), varied sentence rhythm ("Short. Then longer."), and dry wit ("occasionally dryly amused by the gap between what the press release said and what actually happened").

If the model wrote as well as the prompts are written, the system would produce excellent articles. The prompts are a good specification of the desired voice. They are not a good instruction set for an LLM operating under competing constraints.

---

## 3. Where the Voice Fails

### 3.1 The Corpus Reality (Insight Articles: ~2/10 on Voice)

The 10 analyzed Insight articles uniformly failed to achieve the specified voice. The evidence:

| Voice specification | What the articles actually did |
|--------------------|-------------------------------|
| "Write like you were in the room when the decision got made" | All articles used institutional third person; none conveyed proximity to the decision |
| "Vary your sentences the way a good conversation varies" | All articles had uniform 15-25 word sentences in 2-4 sentence paragraphs |
| "Let some paragraphs be one sentence" | Zero one-sentence paragraphs across 10 articles |
| "Start in the middle of something real" | 7/10 opened with "The most important X is not Y" — a formula, not a specific detail |
| "Explain complex financial mechanics by walking through them" | Articles named financial concepts without walking through them |
| "You may use the first person when it serves the reader" | Zero first-person usage |
| "The goal is pleasurable clarity, never theatrical color" | Articles achieved neither clarity nor color — they achieved formulaic competence |
| "Prefer clean verbs and concrete nouns to adjectives" | Articles used abstract nouns as agents: "the bifurcation," "the repricing" |
| "Show the reader the two numbers side by side and let them feel the spread" | Numbers were listed but not juxtaposed; the reader never "felt" a spread |
| "Your voice is your own: informed, direct, unpretentious" | All articles shared the same voice — institutionally competent, not personally distinct |

### 3.2 The Key Gap: Why Good Instructions Don't Produce Good Voice

The voice specification tells the model *what* to sound like but not *how* to achieve it under constraints. The model receives:

1. **Voice instructions** (~550 words): Be proximate, varied, concrete, personal, dryly amused
2. **Format instructions** (~200 words): Produce specific JSON, hit word count, include 15+ fields
3. **Analytical instructions** (~800 words): Build a narrative ledger, identify tension, trace mechanism, make a bounded claim
4. **Constraint instructions** (~300 words): Don't use these 14+ constructions, distinguish fact from inference, don't invent
5. **Structural instructions** (~400 words): Follow headline shape, follow voice mode, use this opening move

**In a single forward pass, the model must satisfy all five categories simultaneously.** The categories that have hard verification (JSON format, required fields, word count, forbidden constructions) crowd out the categories that have soft verification (voice quality, prose rhythm, analytical depth, financial reasoning).

The model doesn't choose to ignore the voice instructions. It literally cannot attend to them all at once. The hard constraints (valid JSON, all fields present, word count met) consume the cognitive budget. Voice is the residual — whatever prose style happens to satisfy the hard constraints fastest.

### 3.3 The Mode Selection Problem

The voice mode system (8 modes) and headline shape system (9 shapes) are designed to create variety. But in practice:

- The model doesn't appear to meaningfully differentiate between modes. Articles assigned "Underwriting margin" read similarly to articles assigned "Basis autopsy."
- The headline shape is rarely reflected in the actual headline. "Consequence-led" shapes produce headlines indistinguishable from "Colon reveal" shapes.
- The mode/headline selection is context-based (matching story features to mode characteristics), which is better than random assignment but still doesn't guarantee the model will actually execute the assigned mode

**Why mode execution fails:**
1. The mode instructions arrive as JSON text in the user prompt — one more piece of context competing for the model's attention
2. There's no quality gate that checks whether the article actually follows the assigned voice mode (no programmatic way to verify "does this sound like a basis autopsy?")
3. The mode instructions ask for specific rhetorical moves ("open on the spread between two prices") that the model may not be able to execute if the dossier doesn't provide the right data for that move

---

## 4. Proposed Refined Voice Parameters

The following refinements are designed to make the voice specification more executable given the system's architectural constraints. They do not change the desired outcome; they change how the outcome is requested.

### 4.1 Reduce the Voice Specification to 3 Non-Negotiable Rules

Instead of 550 words of aspirational voice instruction, give the model 3 concrete rules that can be mechanically verified:

**Rule 1: First sentence must contain a specific number, name, address, or date from the dossier.**
- NOT: "The most important signal in CRE debt markets right now is..."
- YES: "350 Park Avenue just signed a tenant at $120 a foot."
- Verifiable: Check if first sentence of body_html contains a number or named entity from the dossier.

**Rule 2: One paragraph must be exactly one sentence.**
- Forces the model to actually vary paragraph length rather than just being told to.
- Verifiable: Check if any paragraph in body_html contains exactly one sentence.

**Rule 3: One sentence must express a personal judgment using "I" or "we."**
- NOT: "The transaction suggests that the market is bifurcating."
- YES: "I'd watch this lender's next office deal." or "Our read is that the buyer is pricing in a rate cut."
- Verifiable: Check if body_html contains "I" or "we" followed by a judgment verb (read, think, watch, question, doubt).

**These three rules are:**
- Concrete (not abstract instructions like "vary your sentences")
- Verifiable (quality gates can check them programmatically)
- Behavior-changing (they force the model to do things it currently doesn't do)
- Compatible with the current architecture (they don't increase cognitive load — they replace vague instructions with specific ones)

### 4.2 Separate Voice from Format

Currently, voice instructions and format instructions arrive in the same context window, competing for the model's attention. A refined approach:

- **Pass 1 (Structure):** Give the model ONLY the format requirements (word count, required fields, JSON schema) and ask it to produce a structured outline — headlines, section headers, key data points, central claim
- **Pass 2 (Voice):** Give the model the outline plus the voice instructions and ask it to write the prose that fills the outline, following the 3 rules above
- **Pass 3 (Verify):** Quality gates check both structure and voice

If multi-pass generation isn't architecturally feasible, a lighter-weight approach:
- Put voice instructions FIRST in the system prompt (currently they're at position 6 of 8 sections)
- Reduce total voice instruction length by 60%
- Make voice rules concrete rather than aspirational

### 4.3 Make Voice Mode Selection Actually Matter

Currently the 8 voice modes are selected contextually but weakly enforced. To make them matter:

- **For each voice mode, add one mandatory structural element** — not an abstract "opening move" but a required sentence position:
  - Underwriting margin: Sentence 3 must use the word "underwriting" in an analytical claim
  - Basis autopsy: Paragraph 2 must contain two dollar amounts in the same sentence
  - Lender's-eye memorandum: Paragraph 1 must contain a question (interior to the paragraph, not the rhetorical opening)
  - Counterparty map: By sentence 7, two parties with opposing needs must be named
  - City in the balance sheet: Paragraph 1 must contain a physical detail (address, unit count, building year, vacancy date)
  - Consensus under cross-examination: Paragraph 2 must contain "but" as a contrast pivot with a specific number on each side
  - Time as a cost of capital: Paragraph 1 must contain a date (maturity date, deadline, expiration)
  - Operator's field note: Paragraph 2 must contain a sentence using "I" or "we"

### 4.4 Use First Person as a Default, Not a Permission

The current approach: "You may use the first person when it serves the reader." (permissive)
Proposed: "Your default perspective is first person. Write as 'we' or 'I.' Only use third person when first person would be distracting." (prescriptive)

This shifts the default. The model currently defaults to third person because that's its training bias. Changing the default to first person forces the model to overcome its training bias, which is harder to ignore than a permission.

### 4.5 Establish a Voice Quality Gate

Currently there is no voice quality gate. The proposed 3 rules from section 4.1 become the foundation of a voice gate:

```python
def voice_quality_issues(article: dict, dossier: dict) -> list[str]:
    issues = []
    body = html_to_text(article.get("body_html", ""))
    
    # Rule 1: First sentence must contain a dossier-sourced specific
    first_sentence = re.split(r'(?<=[.!?])\s+', body)[0] if body else ""
    has_specific = bool(re.search(r'\$[\d,]+|\d+ (?:Park|Avenue|Street|Broadway|Square)|'
                                   r'\b(?:January|February|March|April|May|June|'
                                   r'July|August|September|October|November|December)\b',
                                   first_sentence))
    if not has_specific:
        issues.append("voice gate: opening sentence lacks a specific number, name, address, or date")
    
    # Rule 2: Must have at least one one-sentence paragraph
    paragraphs = re.split(r'\n\s*\n', body)
    has_one_sentence = any(
        len(re.findall(r'[.!?](?:\s|$)', p)) <= 1
        for p in paragraphs if p.strip()
    )
    if not has_one_sentence:
        issues.append("voice gate: article has no one-sentence paragraph")
    
    # Rule 3: Must contain at least one first-person judgment
    has_first_person = bool(re.search(
        r'\b(?:I|we)\b.{0,30}\b(?:read|think|watch|question|doubt|bet|expect)\b',
        body, re.IGNORECASE
    ))
    if not has_first_person:
        issues.append("voice gate: article contains no first-person judgment")
    
    return issues
```

### 4.6 Reduce Forbidden Constructions to 3

The current forbidden constructions list (14+ patterns in `_AI_TELLS` plus explicit prohibitions in the prompt) creates a "don't do this" list that's too long for the model to remember. Reduce to 3 absolute prohibitions:

1. **No "most important X is not Y" openings.**
2. **No "signals/reveals/highlights" as the primary analytical verb.**
3. **No rhetorical questions at the end.**

Three rules the model can remember. Three rules the quality gates can check reliably. Everything else is handled by the positive voice rules ("do this") rather than negative ones ("don't do this").

### 4.7 The Voice Target: A 3-5 Sentence Example

Give the model a voice target — not instructions about voice, but an example of the voice it should produce:

> **Voice target example:**
>
> "350 Park Avenue just signed a tenant at $120 a foot. The building at 383 Madison, three blocks away, is still half empty and the lender hasn't been paid since March.
>
> Same market. Same block. Two completely different buildings — and two completely different lenders.
>
> The lender at 350 Park can tell their credit committee they're in the right deals. The lender at 383 Madison can't tell their credit committee anything because their loan has been in special servicing for eight months and the last appraisal came in 30% below the loan balance.
>
> I'd watch what happens at 383 Madison. If that building finds a tenant — any tenant — at a number that pencils, the whole submarket reprices. If it doesn't, the lender takes a loss and the market gets another data point about what office debt is actually worth."

This example demonstrates:
- **Concrete opening:** A specific address and number
- **Varied sentence length:** "Same market. Same block." (short) vs. the long sentence about the lender
- **First-person judgment:** "I'd watch what happens at 383 Madison."
- **Walking through the mechanism:** The lender's situation explained through specific facts
- **Contrast without formula:** Two buildings, two lenders, two outcomes — shown, not announced
- **Sharp ending:** A specific, testable claim about the submarket repricing

---

## 5. Voice Specification: Summary Comparison

| Dimension | Current Spec | Proposed Refinement |
|-----------|-------------|-------------------|
| **Length** | ~550 words of voice instruction | 3 concrete rules + 1 example (~200 words) |
| **Style** | Aspirational ("write like you were in the room") | Prescriptive ("first sentence must contain a number, name, or address") |
| **Verifiability** | None — quality gates can't verify voice | 3 rules are mechanically verifiable |
| **First person** | Permissive ("you may use") | Prescriptive ("default is first person") |
| **Paragraph variety** | Instructed ("let some paragraphs be one sentence") | Required ("one paragraph must be exactly one sentence") |
| **Forbidden constructions** | 14+ patterns + explicit list | 3 absolute prohibitions |
| **Voice mode enforcement** | Modes assigned, weakly followed | Each mode gets one mandatory structural element |
| **Target example** | None | 3-5 sentence example of the target voice |

---

## 6. Implementation Considerations

### 6.1 What's Achievable Now (Without Architectural Change)

The 3 concrete voice rules (section 4.1) and the voice quality gate (section 4.5) can be implemented immediately. They replace aspirational instruction with verifiable requirements and add detection where there is currently none.

**Expected impact:** Moderate. The rules will force the model to vary paragraph length, use first person, and start with concrete details. But they won't make the model a better financial thinker — they'll make it a more stylistically varied financial writer. The analytical depth problem remains architectural.

### 6.2 What Requires Architectural Change

True voice execution — the quality of sounding like one informed person with judgment — requires the model to have enough cognitive budget to attend to prose quality. This requires:
- Separating analytical reasoning from prose generation (so the model isn't trying to "understand" and "write" simultaneously)
- Reducing the number of simultaneous output requirements (separate article generation from ledger generation from social post generation)
- Allowing the model to focus on one thing at a time

### 6.3 What the LinkedIn Essay Performance Suggests

If the essay queue genuinely scores 7-8/10 on voice while Insight articles score ~2/10, the most impactful change would be:

**Adopt the essay format's architectural characteristics for Insight articles:**
- First-person default (not permission)
- Opinion-driven (one claim, well-supported, not comprehensive coverage)
- Flexible word count (target not constraint)
- No simultaneous structured data requirements (generate the article first, extract metadata after)

The Insight articles don't need to be LinkedIn essays. But the conditions that make the essays work — focused attention, fewer competing demands, first-person default — should inform how the Insight format is structured.

---

## 7. The Voice Gap Visualized

```
 VOICE TARGET (what the prompts ask for)
 ────────────────────────────────────────
 │                                       │
 │  "Write like you were in the room     │
 │   when the decision got made."        │
 │                                       │
 │  "Short. Then longer. Building        │
 │   across clauses that accumulate      │
 │   evidence."                          │
 │                                       │
 │  "Your voice is your own: informed,   │
 │   direct, unpretentious, dryly        │
 │   amused."                            │
 │                                       │
 │  "Show the reader two numbers         │
 │   side by side and let them feel      │
 │   the spread."                        │
 ────────────────────────────────────────
              │
              │  THE GAP: Single-pass generation
              │  cannot execute voice + analysis
              │  + structure + format simultaneously
              │
              ▼
 ────────────────────────────────────────
 │                                       │
 │  "The most important signal in this   │
 │   transaction is not the price.       │
 │   It is the basis."                  │
 │                                       │
 │  "The deal signals that the market    │
 │   continues to face headwinds."      │
 │                                       │
 │  "Market participants will be         │
 │   watching closely."                 │
 │                                       │
 │  [All paragraphs: 2-4 sentences.]    │
 │  [Zero first-person.]                │
 │  [Zero one-sentence paragraphs.]     │
 │                                       │
 ────────────────────────────────────────
 VOICE REALITY (what the model produces)
```

The gap is not a failure of the voice specification. It is a failure of the architecture to give the model enough cognitive space to execute the specification.
