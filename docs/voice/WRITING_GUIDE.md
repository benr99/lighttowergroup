# The Light Tower Writing Guide

How we write stories that get read, liked, shared and remembered, in Ben Rohr's voice, without ever saying anything the sources do not support.

Written 2026-10-09. This is the human-readable companion to the prompts in `docs/voice/prompts/` (`system.txt`, `brief.txt`, `article.txt`) and the code in `scripts/ben_voice.py` and `scripts/voice_gate.py`.

**A note on evidence.** The book lessons below are my distillation of well-known ideas from each book, written in my own words from general knowledge. I did not re-read the books in this session and I do not quote them. The publication measurements are real: I computed them from full articles our own pipeline retrieved lawfully. Three publishers (The Real Deal, GlobeSt, Crain's New York) block automated fetching, so what I say about their voice is general knowledge and headline snippets, not measurement, and I mark it that way.

---

## Part 1. What thirty books on writing agree on

Grouped by what they teach. For each: the idea in a line, and what we take from it.

### The sentence: clarity is a kindness

| # | Book | The idea | What we take |
|---|---|---|---|
| 1 | *On Writing Well*, William Zinsser | Clutter is the enemy; write for one reader as a real person; warmth comes from humanity, not decoration. | One reader in mind (a sharp friend at a lender). Cut every word that is not working. |
| 2 | *The Elements of Style*, Strunk and White | Omit needless words; prefer the concrete; active voice. | Hard cap on filler; verbs do the work. |
| 3 | *Style: Lessons in Clarity and Grace*, Joseph Williams | Make characters the subjects and actions the verbs; put old information first and new information last. | Name who did what. "Lenders pulled back" beats "there was a pullback." |
| 4 | *The Sense of Style*, Steven Pinker | The "classic style": the writer shows the reader something they can see. The curse of knowledge makes experts unreadable. | Explain insider terms in a clause. Show, then say what it means. |
| 5 | *Several Short Sentences About Writing*, Verlyn Klinkenborg | The sentence is the unit of thought; slow down and make each one true and plain. | One idea per sentence. |
| 6 | *Writing Tools*, Roy Peter Clark | Practical moves: put the strong word last, vary sentence length, cut big then small, use the ordinary word. | Sentence-music rules in the prompt (short beside long, strong word at the end). |
| 7 | *How to Write Short*, Roy Peter Clark | Short forms (headlines, captions, posts) are a craft of their own; compress to the one thing. | Headline and LinkedIn-post engines treated as first-class writing. |
| 8 | *Dreyer's English*, Benjamin Dreyer | Modern, relaxed usage; a confident, slightly wry copyeditor's voice; do not be precious. | Contractions yes; stuffiness no; consistent style sheet. |
| 9 | *Draft No. 4*, John McPhee | Structure is a decision made before the first sentence; revision is where the piece is found. | A "brief" step before drafting; an editor pass after. |
| 10 | "Politics and the English Language," George Orwell (essay) | Stock phrases let writers stop thinking; choose the concrete, fresh word. | A banned-phrases list and a "say the thing" test. |

### The story: why people keep reading

| # | Book | The idea | What we take |
|---|---|---|---|
| 11 | *Bird by Bird*, Anne Lamott | Start small, with a real person and a real scene; first drafts are allowed to be bad; honesty is the style. | Start from the human at the centre. |
| 12 | *On Writing*, Stephen King | Be plain; distrust adverbs; the story is found, not planned; cut without mercy. | Adverbs are the first thing the gate removes. |
| 13 | *Story*, Robert McKee | Stories live in the gap between what a person expects and what happens. | Every piece names the expectation and the surprise. |
| 14 | *Save the Cat*, Blake Snyder | A story can be said in a one-line promise (the logline); give the reader someone to root for early. | The brief's "protagonist + tension" line is a logline. |
| 15 | *Wired for Story*, Lisa Cron | The brain follows cause and effect and a protagonist's struggle; open with what is at stake, not background. | Stakes before significance. |
| 16 | *Storyworthy*, Matthew Dicks | Find the one small moment where something changes; begin close to the end. | The "turn" paragraph. Start late, leave early. |
| 17 | *The Anatomy of Story*, John Truby | Desire, opponent, plan, struggle. | Treat counterparties as characters with opposing wants. |
| 18 | *Into the Woods*, John Yorke | Stories are questions and answers; shape comes from raising a question and resolving it. | The hook asks; the kicker answers or hands over a testable question. |
| 19 | *The Art and Craft of Feature Writing*, William Blundell | The Wall Street Journal formula: a human anecdote, then a plain "nut graf" saying why it matters, then the body, then a kicker that returns to the opening. | Our core template for flagships. |
| 20 | *Writing for Story*, Jon Franklin | Narrative nonfiction runs on complication and resolution with an unambiguous point. | Every piece has a clear point stated by paragraph three or four. |

### Truth and craft in nonfiction

| # | Book | The idea | What we take |
|---|---|---|---|
| 21 | *The Elements of Journalism*, Kovach and Rosenstiel | Journalism's first obligation is to truth, discipline of verification, loyalty to the reader. | Verification is part of the craft. This is the accuracy gate. |
| 22 | *Telling True Stories*, ed. Kramer and Call | Narrative journalism: scene, character, reporting detail, restraint. | Use the real detail the source gives; never invent a scene. |
| 23 | *Everybody Writes*, Ann Handley | Web writing must be useful and empathetic; write ugly first, then edit hard; the reader's time is the currency. | Lead with value; edit down. |
| 24 | *Writing Without Bullshit*, Josh Bernoff | In business writing, state the point first; no jargon, no hedging, no throat-clearing. | Point by paragraph three; jargon audit. |
| 25 | *The Psychology of Money*, Morgan Housel | Finance lands when told as short human stories about behaviour; humility beats forecasting. | Tell money as behaviour; no confident predictions. |

### Attention, sharing and the internet

| # | Book | The idea | What we take |
|---|---|---|---|
| 26 | *Made to Stick*, Chip and Dan Heath | Ideas stick when simple, unexpected, concrete, credible, emotional, and told as stories. | Our hook checklist (SUCCES). |
| 27 | *Contagious*, Jonah Berger | People share what makes them look good (social currency), what a trigger reminds them of, strong emotion, what is public, what is useful, and stories. | Shareability test: "does sharing this make my reader look sharp?" |
| 28 | *Hit Makers*, Derek Thompson | Hits are familiar enough to feel safe and surprising enough to feel new; distribution matters as much as quality. | Familiar frame (a deal everyone understands) plus one surprising turn. |
| 29 | *Ogilvy on Advertising*, David Ogilvy | The headline does most of the work; specifics beat superlatives; the reader is not a fool. | Headline engine: three or four candidates, pick on rubric. |
| 30 | *Show Your Work!*, Austin Kleon | Share the process and the thinking, not just the polished result; a personal voice builds an audience. | First-person reasoning is the product; "here is how I read this." |

---

## Part 2. Fourteen laws for writing that gets read online

The synthesis. Each has the idea, the books behind it, how the engine applies it, and how a machine can check it.

1. **Write to one reader, a smart friend with little time.** (Zinsser, Handley, Bernoff.) The prompt names the reader. Check: no sentence needs a footnote to be understood.
2. **Lead with the surprising specific.** (Heath, Ogilvy, Thompson.) First 200 characters carry a fact that does not fit the obvious reading. Check: hook contains a specific number, name or physical detail, and no throat-clearing.
3. **Concrete beats abstract; turn numbers into human consequences.** (Orwell, Pinker, Heath.) "$479 million" becomes what the lender is risking and on whose behalf. Check: every key number is followed by a consequence sentence.
4. **Characters are subjects; actions are verbs.** (Williams.) Check: mean passive-voice rate under 5%, named subjects in most sentences.
5. **Stakes before significance.** (Cron, McKee, Truby.) Say who wins and loses before saying what it means. Check: a "stakes" paragraph precedes "meaning".
6. **Short paragraphs, varied rhythm, white space.** (Clark, King, web norms.) The press we measured runs about 30 to 35 words per paragraph. Check: paragraphs under 55 words and 3 sentences; no three same-length sentences in a row.
7. **The nut graf by paragraph three.** (Blundell, Franklin.) Say plainly what happened and why it matters. Check: a "nutgraf" role by paragraph 3.
8. **Shape the piece around a question and an answer.** (Yorke, McKee.) Pick a shape (Part 5) before writing. Check: the brief names the shape and the turn.
9. **Earn emotion with specifics; never instruct the reader's feeling.** (Lamott, Dicks, Kramer.) Name the human stake with a real detail, then say what it means with restraint. Check: no "heartbreaking", "shocking", "stunning"; no invented scenes.
10. **Be familiar and surprising at once, and make sharing flattering.** (Thompson, Berger, Heath.) A frame everyone knows, one fresh turn, a line the reader would be glad to repeat. Check: rubric item "would a reader forward this?"
11. **Sound like a person, not an institution.** (Zinsser, Dreyer, Kleon.) First person, contractions, candour, light humour. Check: first-person marker present in takes; none of the institutional boilerplate list.
12. **Cut.** (Strunk and White, King, Klinkenborg.) Adverbs, stock phrases, and "very" go first. Check: banned-phrase list; evaluative adverbs are never allowed in facts.
13. **End with a kicker.** (Blundell, Yorke.) Echo the hook, or hand the reader a question they can test on their own deal. Check: last paragraph role "kicker"; never "time will tell".
14. **Truth first.** (Kovach and Rosenstiel.) Every fact is quoted, every claim attributed, qualifiers kept. This is the claim gate, and it is non-negotiable.

---

## Part 3. How the real estate press writes (and where there is room)

### What we measured

Full-text articles retrieved by our pipeline in August 2026, per publisher (small samples, so treat as indicative):

| Publisher | Articles | Words per paragraph | Words per sentence | Reading grade | Numbers per 100 words |
|---|---|---|---|---|---|
| Commercial Observer | 23 | 32 | 27 | 14.5 | 4.4 |
| Bisnow | 8 | 36 | 25 | 13.3 | 4.4 |
| Multi-Housing News | 8 | 33 | 21 | 12.8 | 5.8 |
| Connect CRE | 9 | 32 | 21 | 13.8 | 4.2 |
| HousingWire | 10 | 36 | 26 | 14.0 | 5.6 |
| Gothamist (city desk, for contrast) | 5 | 37 | 24 | 13.6 | 2.0 |
| **Our old writer** | 198 | **100** | **26** | **15.4** | 3.2 |
| **Our new fact-gated writer** | 16 | **41** | **17** | **9.0** | n/a |

Two lessons. The trade press is not easy reading (grade 13 to 14), but it is **always written in short paragraphs of one or two sentences**. Our old pages ran 100 words a paragraph, which is the single biggest gap. And there is room to be *easier* than the trade without being simpler: grade 9 to 10 with the same expertise is where LinkedIn readers live.

### Headline patterns we observed (Commercial Observer, Bisnow, Connect CRE; paraphrased)

- **Party, deal verb, size:** "[Buyer] buys [asset] for [price]". Short active verbs (buys, lands, signs, sells, inks).
- **Lender as subject:** "[Lender] backs [project]" or "[Firm] lands [amount] to refinance [asset]".
- **Numbers as anchors:** compressed units (SF, M, B, "323-unit") placed early so the eye catches them.
- **Series labels:** a colon label tells the reader the format first (deal sheet, five questions, "the plan").
- **Wry or vivid verbs on analysis:** punt, swing, douse, mask, hold off.
- **Quoted jargon as a hook:** an industry phrase in quotation marks signals commentary.
- **Short setup then a qualifier:** a plain statement, then a second sentence that adds doubt.
- **Length:** 6 to 13 words; title case; local tags (city, submarket) do the relevance work.

### What each house sounds like (general knowledge unless measured)

- **The Real Deal** (not measured; blocked): personality-driven, scoop-forward, comfortable with feuds, litigation and ego, wry headlines, a New York insider's tone. The lesson is permission to be about *people*.
- **Commercial Observer** (measured): deal-verb headlines, tight ledes, quotes from principals, a clean institutional voice with occasional wit in columns.
- **Bisnow** (measured): a briefing voice, fragments and short items, strong local tagging, a knowing edge in analysis headlines.
- **GlobeSt** (blocked; headline snippets only): neutral, data- and trend-forward, professional-promotional, high jargon.
- **Connect CRE** (measured): terse deal summaries; buyer, lender, broker credited; little editorialising.
- **Crain's New York** (blocked): neighbourhood, people and money; closer to a city newspaper than a trade sheet.

### The gap we can own

Nobody in this set does **humane, first-person analysis with a point of view and a sense of what the story means for the country**, at scale, with every fact traceable. The trade press reports deals fast. The Wall Street Journal and Financial Times explain meaning, but rarely about the $40 million Brooklyn refinance. That gap is the product: *the speed and specificity of the trade press, the structure and standards of the WSJ and FT, in a voice that sounds like a person.*

---

## Part 4. The standard: Wall Street Journal and Financial Times quality

What those papers do that we will do too:

- **WSJ formula** (Blundell): a human, specific opening; the nut graf; supporting reporting with attributed claims; a kicker that returns to the opening. We use it for flagships.
- **FT habit:** understatement, scepticism, and one dry sentence that lands. "Lex"-style compression: say the thing, stop.
- **Both:** attribute every claim; keep qualifiers; give the other side; label opinion; never hype; precise numbers with their context.
- **Award-quality feature work** (the explanatory and narrative traditions in Kramer and Call, McPhee, Franklin): ordinary people inside large forces; one clear question the piece answers; restraint at the emotional peak; an ending that is earned, not announced.
- **What a prize jury would reject:** invented scenes, composite quotes, borrowed emotion, "this changes everything", certainty about people's inner lives. Our gate rejects the same things mechanically.

---

## Part 5. The craft kit

### Eight story shapes
Each is a way to arrange the *same verified facts*. The brief picks one (`ben_voice.SHAPES`).

1. **The Number That Doesn't Fit**: a figure contradicts the obvious reading.
2. **The Clock**: a maturity, deadline or vote shapes every choice.
3. **The Price Tells the Truth**: what someone paid or lent says more than what anyone said.
4. **Who Blinked**: two parties want opposite things and one gives ground.
5. **The Building as Character**: a place with a physical history is the subject.
6. **The Quiet Signal**: a small deal that may be an early sign of something larger.
7. **The Rule Changed**: a policy or ruling reallocates winners and losers.
8. **The Ritual**: the deal reveals what people value (status, ownership, belonging, legacy).

### Ten macro-cultural lenses (pick exactly one per piece)
Capital cycle · time and patience · trust and institutions · home and belonging · status and ambition · work and cities · power and politics · technology and land · climate and risk · demographic change.

A lens is a way of asking *what is this deal really about?* It is only ever applied with facts the sources show. A $40 million Brooklyn refinance can illustrate the capital cycle; it cannot, on its own, prove a national trend, and the voice says "may be an early sign of" when that is the honest reach.

### Ten hook formulas (the first 200 characters)
1. **Contradiction**: two facts that should not both be true.
2. **Number first**: the figure that does the work, plainly stated.
3. **Person under pressure**: a named party and what they must decide.
4. **Physical detail**: something you could see if you stood there (only if the source gives it).
5. **Reversal**: what it looked like, then what it was.
6. **Scale shock**: the size, stated simply, then what it equals in human terms (only from facts).
7. **The odd detail**: the clause nobody puts in the headline.
8. **Time stamp**: the date that changes the maths.
9. **A genuine question** the piece answers.
10. **Understatement**: a very plain sentence that carries weight.

Every hook is a plain, quoted fact followed by one short reaction. The pull comes from *which* fact and the reaction after it, never from decorating the fact.

### Ten headline formulas
Under 70 characters, specific, one surprise, a person or number early. (a) Subject + sharp verb + number. (b) The contradiction in six words. (c) "[Who] [did what] at [odd detail]." (d) Quoted phrase from the source plus the stakes. (e) A plain question the piece answers. (f) Number as subject. (g) Two short sentences, the second turning the first. (h) The thing everyone missed. (i) Place + stake. (j) The clock. Avoid "X announces Y", "What X means", "Why X matters" unless earned.

### Six kicker types
Echo the hook · the testable question ("If your lender is quoting X, ask Y") · the unanswered detail · the human close · the understatement · the next date to watch.

---

## Part 6. Ben Rohr: the character behind the voice

The astrological and personality details are used here as a **creative character brief**, a lens to make the voice specific and consistent, not as a claim about anyone. The prompt embodies the traits and never mentions astrology or personality types.

| Source | Trait | How it shows on the page |
|---|---|---|
| ENTP | Quick, curious debater; connects far-apart ideas; plays devil's advocate | Argues the other side before settling; "here's the counter-argument I can't dismiss"; sees the pattern across deals |
| Sagittarius Sun | Candid, funny, big-picture, philosophical, restless explorer | Plain speech; a joke that lands; zooms out to what it means; the anthropologist's curiosity about why people do this |
| Cancer Moon | Emotionally perceptive, protective, loves home, memory and belonging | Notices the human stake: the family, the tenant, the neighbourhood; real estate as shelter and memory; warmth under the wit |
| Virgo Rising | Precise, analytical, editorial, helpful, dry-witted | Exact with numbers and qualifiers; trims every sentence; understated humour; useful close |
| Capricorn stellium | Institutional, ambitious, patient, respects structure and time | Reads capital as a promise about time; respects the long cycle; explains status and ambition as forces; calm authority |

**The voice in one line:** a warm, quick, slightly irreverent analyst who treats a loan as a promise about time and a building as the place people keep their lives, and who can tell you why it matters to the country.

**Dials** (0 to 10): formality 4 · warmth 8 · humour 5 (dry, rare) · candour 8 · jargon 3 (always explained) · swagger 2 · emotion 5 (restrained, specific) · certainty 4 (calibrated).

**Signature moves** (use one or two per piece, never all):
- *The other chair*: name the person on the other side of the table and what they wanted.
- *The clock*: find the deadline and say who is running out of time.
- *The price tells the truth*: read what a number admits.
- *The ritual reading*: ask what this act says about what people value.
- *The honest limit*: "The filing does not say; that is the question I would ask."
- *The dry aside*: one understated line, never at someone's expense.

**What Ben never does:** hype, gloat at someone's loss, mock a hardship, claim a call or a site visit he did not make, assert what a named person privately thinks, predict as fact, use "game-changer", "unlock", "navigate the landscape", "poised to", or "it remains to be seen".

**On first person.** The "I" is allowed to *judge*, *react* and *read*. It is not allowed to claim experience (no "I toured", "a lender told me") unless Ben has supplied a real note for it (Part 7).

---

## Part 7. Depth without fabrication

The tension: you want personal voice, cultural meaning and emotional weight. We also require that nothing be made up. The way to have both is a strict separation.

### The Two-Layer Rule
- **Layer 1, facts.** Plain, single-claim sentences, each carrying a verbatim source quote. No colour. This layer is machine-verified exactly as before.
- **Layer 2, voice.** Reactions, readings and meaning, in separate sentences right after the facts they rest on. This layer is checked by a different standard (below).

The rhythm is the oldest one in journalism: fact, fact, reaction.

### Sentence kinds
| Kind | What it is | Check |
|---|---|---|
| `fact` | A plain claim from one or two quotes | Existing gate: quote verbatim, numbers, names, qualifiers, attribution, two model passes |
| `take` | Ben's reading or opinion | First person or plainly opinion; cites the fact ids it rests on; adds no number or name beyond them; no private states attributed to named parties; no experience claims; independent model rubric |
| `voice` | A transition, reaction or light humour | No numbers, no names, no experience claims, short; the rubric confirms it asserts nothing |
| `context` | History or cultural background | Only from the approved Context Bank, by id |
| `ben` | A real experience of Ben's | Only from Ben's Notes, by id |

Anything that fails is deleted. The fact layer's accuracy is not loosened at all.

### The two banks (this is how cultural and personal depth stay honest)
- **Context Bank** (`docs/voice/context-bank.json`): each entry is a short, human-verified claim with a source link, a date checked and who checked it. The writer cites an id and may say nothing beyond the entry. Without entries, no history or macro claims appear. See the starter research list below.
- **Ben's Notes** (`docs/voice/ben-notes.json`): real moments from Ben's career. The `ben` kind is only allowed with one. Prompts to elicit them are below.

### Starter list for the Context Bank (topics to research and verify; these are NOT facts yet)
Each needs a primary source and a human check before it is added.
1. The 2022 to 2023 rate shock and what it did to floating-rate borrowers.
2. The commercial mortgage maturity wall and extend-and-pretend.
3. The history of New York rent regulation and how it shaped ownership.
4. Postwar suburbanisation and its financing.
5. The co-op and condo conversion era and who it served.
6. Why office values and office leasing diverged after 2020.
7. The data-center and power land rush: how electricity became a real estate input.
8. Zoning, entitlement and why supply is slow.
9. The 2008 securitisation vintage and what it taught lenders about structure.
10. Waterfront rezonings in Brooklyn and Queens.
11. The history of REITs.
12. How insurance costs became an underwriting variable.
13. Housing affordability measures and what they leave out.
14. The role of the Fed's balance sheet in mortgage spreads.

### Prompts to draw out Ben's Notes
A deal that taught you something. A time a number surprised you. A building you can still describe. A client conversation that changed how you underwrite (anonymised). A mistake you would not repeat. Something your grandparents' generation would not understand about how real estate works now. Each becomes one short entry, written by you, with a date and whether it can be shared by name.

---

## Part 8. The LinkedIn playbook

**Anatomy of a post** (derived only from verified sentences):
1. **Line one and two (the hook, under 210 characters):** the plain fact plus the reaction. This is what shows before "see more".
2. **Short lines, one idea each,** with white space. A short post is 120 to 220 words; a longer one earns it.
3. **One turn:** what the obvious reading missed.
4. **One take, clearly yours:** first person.
5. **An invitation, not a pitch:** a specific question to answer from experience, or one thing to check on their own deal.
6. **The link in the first comment,** not the body, to the full piece.

**Cadence and formats:** one flagship-style essay a week; two or three short posts from the best verified lines; the Friday wrap as a recurring "what mattered" post. A carousel for the single best chart or number.

**Deal flow:** attention only helps if the right people see it. Write for sponsors and lenders by naming their problems (a maturity, a basis, a rate) in their words, and invite a conversation about the situation, never a hard sell. The call to action is a question a sponsor in that situation wants to answer.

**What not to do:** engagement bait ("Agree?"), fake vulnerability, emoji walls, one-word-per-line pages, hashtags in the body, generic motivation.

**Metrics to watch:** impressions per post, saves and shares per impression, comments from the target audience, profile views, inbound messages that name a deal situation. Compare the new voice against the old on these.

---

## Part 9. The engine

```
sources (verified facts)  →  STORY BRIEF  →  DRAFT  →  GATE  →  EDITOR PASS  →  PUBLISH + LINKEDIN
                              (angle, shape,   (facts +    (facts: quote +        (score vs rubric,
                               lens, hooks,     voice       two model passes;      one rewrite if
                               headlines)       layers)     voice: rubric)         below the bar)
```

1. **Brief** (`brief.txt`): finds the protagonist, tension, why-now, number that matters, lens, shape, four hooks (each from a quoted fact), four headlines. It writes nothing public.
2. **Draft** (`article.txt` with `system.txt`): paragraph roles (hook, stakes, turn, nutgraf, detail, meaning, kicker) and sentence kinds.
3. **Gate** (`claim_verifier.py` for facts, `voice_gate.py` for voice): everything that fails is deleted; one corrective retry.
4. **Editor pass** (planned): scores the surviving piece on the rubric below; if under the bar, one rewrite that may only rearrange and add voice, never add facts; re-gated.
5. **Social derivative** (planned): the LinkedIn post and first comment, built only from kept sentences.

**Tiering for cost:** flagships and analyses get the full engine. Briefs get a light path (hook plus up to one take). The extra brief call and rubric pass add roughly one to two model calls per story; at 70 a day that is a few hundred extra calls, which the budget cap (plan item 1.4) must cover first.

### The read-through scorecard (0 to 5 each; ship at 3.5 average with no criterion under 2)
1. Hook: does the first line make you read the second?
2. Specificity: real names, numbers, a physical or human detail?
3. Clarity: can a smart non-specialist follow it once?
4. Stakes: do you know who wins, who loses, who waits?
5. Turn: is there a moment the obvious reading gives way?
6. Voice: does it sound like one person, with a point of view?
7. Meaning: does it say why it matters, proportionate to the evidence?
8. Emotion: is there a human beat, specific and restrained?
9. Shareability: would a reader look sharp forwarding it?
10. Ending: does the last line stay?

---

## Part 10. What the prototype shows

See `docs/voice/SAMPLES.md` for the actual outputs, the rejections, and what we changed because of them. In short, after four runs on real stories:

- A piece can have a hook, a turn, a point of view, a meaning paragraph and a kicker, with every fact quoted and every opinion machine-checked. The gate also caught its own early leaks ("distressed buildings at a lower basis", an owner who "decides not to reinvest") and now cuts them.
- The result is accurate, structured and readable (grade 9 to 11), but the takes are still generic and the kickers weak. The remaining gap is not a prompt problem: it needs richer source packets, your own notes, a verified Context Bank, calibration on your real writing, and an editor pass.
- It is slow (100 to 290 seconds per story). Tier it before turning it on for all 70.

---

## Decisions this guide needs from you

| # | Decision | Recommendation |
|---|---|---|
| V1 | Allow `take` sentences (opinion) at all, under the strict rules above | Yes: they are the point of the voice; the gate keeps them honest |
| V2 | How much first person on the site versus LinkedIn | First person in takes everywhere; experience claims only from your notes |
| V3 | Context Bank: who verifies entries | You or a researcher; each entry needs a primary-source link |
| V4 | Humour level | Dry, at most one or two light touches; none on hardship |
| V5 | Do we name individuals in takes | Only as the facts name them, never their motives |
| V6 | Roll out | Preview on 10 stories, read them, A/B on LinkedIn for two weeks |
