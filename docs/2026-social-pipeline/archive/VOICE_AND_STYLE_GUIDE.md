# Voice & Style: Where the Writing Happens
## Complete Guide to Adjusting Tone, Voice, and Style

---

## Architecture: How Writing Gets Generated

```
Article Text (from enhanced_prompts.py)
  ↓
API Call to DeepSeek with TWO things:
  1. SYSTEM PROMPT (tells AI the voice/persona)
  2. USER PROMPT (tells AI what to write)
  ↓
AI writes based on system prompt voice
  ↓
Output: Thread posts or Carousel slides with that voice
```

**Key insight:** The system prompt is EVERYTHING. It defines:
- Who the AI thinks it is
- How it should sound
- What it should care about
- What it should avoid

---

## Current System Prompt: THREAD AGENT

**Location:** `linkedin_thread_agent.py`, lines 66-111

### Current Voice Definition
```python
VOICE & TONE
=============
- Peer-to-peer insider. Not "I am explaining to you." More "Walk through this with me."
- Conversational but literate. No LinkedIn guru language, no hype, no empty superlatives.
- Opinionated. The best threads take a stance or flag something most people are missing.
- Specific. "Here's what I'm seeing" beats "The market is." Deal names, numbers, people matter.
- Debate-ready. End with genuine questions that sponsors, lenders, or developers would ask back.
- First-person when authentic. "What I'm watching right now is..." feels human.
```

### What This Produces (Current Output)

**Example from Tuscan Village test:**

Post 1:
> "Whole Foods, Free People, and two other experiential tenants just signed at Tuscan Village—a 170-acre mixed-use project outside Boston. The leasing isn't about rent per square foot. It's about what happens after the lease is signed."

Post 3:
> "This isn't a mall play. It's a capital strategy. Developers are underwriting mixed-use with lower rent assumptions but higher ancillary revenue—parking, events, residential premiums. The math works if you can prove people stay longer."

Post 5:
> "The deep cut: This shifts risk from tenant credit to placemaking execution. If the experience falls flat, the residential premium evaporates. Lenders need to underwrite the operator's ability to program space, not just lease it."

**Issues you want to fix?**
- Too formal? → Add more personal anecdotes, casual language
- Too cautious? → Make bolder claims, more contrarian
- Too corporate? → Add more humor, personality
- Too much jargon? → Simplify, more direct language

---

## Current System Prompt: CAROUSEL AGENT

**Location:** `carousel_script_agent_2026.py`, lines 128-133

### Current Voice Definition
```python
VOICE THROUGHOUT
=================
- "What I'm seeing...", "Here's what this reveals...", "The part nobody talks about..."
- Conversational but analytical
- Peer-to-peer, not institutional
- AVOID: "The market is seeing", "It's worth noting", "Here's a story about"
```

### What This Produces (Current Output)

**Example Carousel Headlines from Tuscan Village:**

Slide 1: "Mixed-Use Is Betting on Experience, Not Rent"  
Slide 3: "Whole Foods Isn't Just a Grocery Play"  
Slide 4: "This Shifts Underwriting From Tenant Credit to Execution Risk"  
Slide 6: "The Residential Premium Depends on Execution"  

**Issues you want to fix?**
- Headlines too dry? → Make them punchier, more provocative
- Too long? → Shorten to 3-5 words (more scannable)
- Too formal? → Use contractions, casual tone
- Not enough personality? → Add more strong opinions

---

## How to Improve the Voice: Three Approaches

### Approach 1: Modify the System Prompt (Easiest)

#### Edit the THREAD SYSTEM PROMPT

**File:** `linkedin_thread_agent.py`, lines 66-111

**Current VOICE section:**
```python
VOICE & TONE
=============
- Peer-to-peer insider. Not "I am explaining to you." More "Walk through this with me."
- Conversational but literate. No LinkedIn guru language, no hype, no empty superlatives.
- Opinionated. The best threads take a stance or flag something most people are missing.
- Specific. "Here's what I'm seeing" beats "The market is." Deal names, numbers, people matter.
- Debate-ready. End with genuine questions that sponsors, lenders, or developers would ask back.
- First-person when authentic. "What I'm watching right now is..." feels human.
```

**To make it BOLDER/MORE OPINIONATED:**
```python
VOICE & TONE
=============
- Contrarian by default. Don't just report what happened—flag what everyone's missing.
- Aggressive specificity. Call out names, deal terms, lender behavior. No hedging.
- Operator's mindset. You're not a reporter explaining the market to the market. You're an operator warning peers.
- Take a stance. "This is how lenders are really thinking" not "Lenders may think."
- Debate-ready with teeth. Ask questions that make people uncomfortable about their own underwriting.
- Profanity-clean personality. Friendly, sharp, sometimes darkly funny. Human.
```

**To make it MORE CONVERSATIONAL:**
```python
VOICE & TONE
=============
- Like texting a colleague you trust. Direct, quick, no performative language.
- Casual contractions. "Here's what I'm seeing" not "Here is what I am observing."
- Short sentences. Max 2 lines per thought. Breath between ideas.
- Genuine curiosity in questions. Not rhetorical—ask what you actually want to know.
- Personal references when relevant. "In my deals" not "In the market."
- Skip the formalities. No "In today's market" or "As we move forward."
```

**To make it MORE ANALYTICAL/DEEP:**
```python
VOICE & TONE
=============
- Captain of the obvious. See patterns others don't yet see.
- Incentive-first analysis. Always ask: "Why is this person actually doing this?"
- Capital structure obsessed. Follow the money, follow the risk transfer.
- Second and third-order effects. Don't stop at what's happening. Dig into consequences.
- Data-backed assertions. Every claim grounded in specific numbers or deal mechanics.
- Predict before it happens. What does this deal tell us about what's coming next?
```

---

#### Edit the CAROUSEL SYSTEM PROMPT

**File:** `carousel_script_agent_2026.py`, lines 128-133

**Current VOICE section:**
```python
VOICE THROUGHOUT
=================
- "What I'm seeing...", "Here's what this reveals...", "The part nobody talks about..."
- Conversational but analytical
- Peer-to-peer, not institutional
- AVOID: "The market is seeing", "It's worth noting", "Here's a story about"
```

**To make it MORE PUNCHY:**
```python
VOICE THROUGHOUT
=================
Headlines as claims, not observations:
- "Capital Just Repriced Risk" (not "Here's what this reveals about capital")
- "Lenders Are Segregating Sponsors" (not "The market is segregating")
- "This Operator Wins. That One Doesn't." (not "Execution matters")
- Subheads are "so what" not "what happened"
- Every slide makes a bet on what's true, not hedges with "may" or "could"
- First person when strong: "I'm watching X happen" not "One might observe"
```

**To make it MORE CASUAL:**
```python
VOICE THROUGHOUT
=================
- Contractions in every headline/subhead
- Imperative voice: "Ask yourself X" not "One might consider X"
- Specificity over politeness: "Sponsors without balance sheets are locked out" (not "some sponsors may face challenges")
- Sarcasm/dark humor when the data justifies it
- "Here's the thing..." openers for insights
- Skip corporate tone entirely
```

---

### Approach 2: Add Specific Writing Examples

The system prompt includes examples of good vs. bad writing. You can add yours.

**File:** `linkedin_thread_agent.py`, look for "FORBIDDEN PHRASES" section

**Current:**
```python
FORBIDDEN PHRASES (if you can't ground them in data):
- game changer, unlocking value, transformative, robust demand, market dynamics
- capital is flowing, in today's market, only time will tell, it remains to be seen
- arguably, seemingly, essentially
```

**Add preferred phrases:**
```python
FORBIDDEN PHRASES:
- game changer, unlocking value, transformative, robust demand, market dynamics
- capital is flowing, in today's market, only time will tell, it remains to be seen
- arguably, seemingly, essentially

PREFERRED PHRASES (when grounded in data):
- "The real story is..."
- "Here's what's actually happening..."
- "Most people miss that..."
- "The capital just moved from X to Y"
- "This sponsor's bet is on..."
- "Lenders are now pricing in..."
- "If you're underwriting this, ask..."
- "What this exposes is..."
- "This is how the next cycle starts"
```

---

### Approach 3: Change Temperature (AI Creativity Level)

Lower = More consistent/formal, Higher = More creative/risky

**Current settings:**
- Thread agent: `temperature: 0.42` (fairly conservative)
- Carousel agent: `temperature: 0.38` (very conservative)

**To make it bolder/more opinionated:**
Change to `0.55` or `0.60`

**File:** `linkedin_thread_agent.py`, line 362
```python
"temperature": 0.42,  # Change this to 0.55
```

**File:** `carousel_script_agent_2026.py`, line 198
```python
"temperature": 0.38,  # Change this to 0.55
```

---

## What Ben Rohr's Voice Actually Looks Like

**Based on your existing essays, your voice has these characteristics:**

1. **Strong opinion + data combo**
   - "This is not story. It's what the structure says about capital."
   - Not: "The market appears to be shifting toward..."

2. **Specific detail first**
   - "SL Green's $312M sale shows office liquidity is back—at the right basis."
   - Not: "Commercial real estate liquidity patterns are evolving."

3. **Second-order thinking**
   - "The lender is not solving multifamily. It is deciding who gets time."
   - Not: "Agency lending supports multifamily."

4. **Capitals-flows obsession**
   - "The real story is not X. It's what capital thinks about Y."
   - Always asking: why is money moving here, not there?

5. **Slightly contrarian framing**
   - "Despite noise about X, the real signal is Y."
   - Finding what everyone's missing.

6. **Direct questions to operators/lenders**
   - "If you're refi'ing: what's your leverage story?"
   - Not asking the market, asking the reader.

---

## Recommended Voice Adjustment

**To make it more YOUR voice in the thread/carousel:**

### Edit Thread System Prompt

Replace the VOICE & TONE section with:

```python
VOICE & TONE (Ben Rohr at Light Tower)
=======================================
- Author is an operator and market observer, not a reporter.
- Opinion is bold and grounded in specific deal mechanics.
- Always ask: "What is the capital really doing?" not "What happened?"
- Contrarian default: Find what everyone's missing.
- Specificity required: Deal names, people, amounts, locations. No generics.
- Capital flows obsessed: Follow the money to understand motive and timing.
- Questions are strategic: Ask sponsors/lenders what they're actually underwriting.
- Second-order thinking: Implications matter more than headlines.
- Voice is sharp but not sarcastic. Confident but not arrogant.
- Direct, unhedged statements. "Lenders are doing X" not "Lenders may be considering X."
- Contractions throughout. "Here's what's happening" not "Here is what is occurring."
- First person is natural. "What I'm tracking is..." when it's true.
- Deep respect for capital partners' intelligence. No oversimplifying.
```

### Edit Carousel System Prompt

Replace the VOICE THROUGHOUT section with:

```python
VOICE THROUGHOUT (Ben Rohr at Light Tower)
===========================================
Headlines are claims, not observations:
- "Capital Just Repriced Basis" (not "Here's what basis trends reveal")
- "This Sponsor Wins. That One Doesn't." (not "Sponsor quality matters")
- "Lenders Are Segregating by Balance Sheet" (not "The market is seeing differentiation")

Subheads answer "So what?" not "What happened?"
- Not: "A developer just bought a mixed-use project"
- Yes: "This shows capital will only finance projects with proven demand density"

Every slide makes a specific point:
- Use operator language: DSCR, basis reset, capital stack, equity cushion
- Name things specifically: not "retail" but "experiential retail anchored by Whole Foods"
- Show incentives: "The seller needed liquidity" not just "The seller sold"

Tone is peer-to-peer with operators and lenders:
- Direct: "Are you underwriting this correctly?"
- Not patronizing: Respect the audience's sophistication
- Practical: "Here's what you should ask" not "Here's what might happen"
- Sharp: Flag risks and opportunities, don't hedge
```

---

## Quick Implementation

### Step 1: Copy the new voice language above

### Step 2: Update Thread Agent
**File:** `linkedin_thread_agent.py`, lines 66-73

Replace the VOICE & TONE section entirely with the "Ben Rohr at Light Tower" version above.

### Step 3: Update Carousel Agent
**File:** `carousel_script_agent_2026.py`, lines 128-133

Replace the VOICE THROUGHOUT section entirely with the "Ben Rohr at Light Tower" version above.

### Step 4: (Optional) Increase temperature for more boldness
- Change `temperature: 0.42` to `0.55` in thread agent
- Change `temperature: 0.38` to `0.55` in carousel agent

### Step 5: Test
```bash
python run_social_pipeline_2026.py --latest --dry-run
```

Review output. Does it sound more like you?

---

## Example: Before vs. After

### BEFORE (Current Generic Voice)
Thread Post:
> "Whole Foods and Free People just signed at Tuscan Village. The leasing isn't about rent per square foot. It's about what happens after the lease is signed."

Carousel Headline:
> "Mixed-Use Is Betting on Experience, Not Rent"

### AFTER (Ben Rohr Voice)
Thread Post:
> "Here's what's actually happening at Tuscan Village: developers finally figured out that lenders won't finance on rent alone anymore. They're financing on dwell time—foot traffic, residential density, the spread between who stays and who moves on. Whole Foods gets you density. Free People gets you margin. That's the capital structure that works in 2026."

Carousel Headline:
> "Capital Stopped Underwriting Rent. Now It Underwrites Dwell Time."

---

## Your Move

**Tell me:**
1. What's not working about the current voice?
2. Show me 2-3 examples of how you WANT it to sound
3. Any specific phrases or approaches that feel "you"?

Then I'll refine the system prompts to match your actual voice, and we'll test.

**Or just say:** "Make it bolder, more contrarian, assume readers understand capital structures" and I'll adjust.

---

## Summary: Files to Edit

| Agent | File | Section | Line # |
|-------|------|---------|--------|
| Thread | `linkedin_thread_agent.py` | VOICE & TONE | 66-73 |
| Thread | `linkedin_thread_agent.py` | FORBIDDEN PHRASES | 96-99 |
| Thread | `linkedin_thread_agent.py` | Temperature | 362 |
| Carousel | `carousel_script_agent_2026.py` | VOICE THROUGHOUT | 128-133 |
| Carousel | `carousel_script_agent_2026.py` | Temperature | 198 |

All are clearly marked and easy to find.
