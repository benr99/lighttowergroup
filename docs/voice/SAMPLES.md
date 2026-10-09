# Voice engine: prototype samples and what they teach

Generated 2026-10-09 by `outputs/voice/prototype.py` with the real writer (DeepSeek) and the real fact gate, on stories from our August retrieval cache. Facts are plain and every one passed the quote check and two model passes. `[take]` and `[voice]` are the opinion layer, each checked by the voice gate. Headlines and excerpts fall back to the story's own headline when the writer's version fails (in this harness the fallback headline is a URL slug, which is a test artifact: in production it is the real headline).

## How we got here (four runs)

| Run | Change | Result |
|---|---|---|
| 1 | First prompts; the old rule that facts may be colourful | Hooks fused two facts and used words like *just* and *only*. The fact gate correctly deleted them. Output: dry 50 to 80 word remnants |
| 2 | **Two-Layer Rule:** facts plain, colour in separate sentences; one retry | 7 to 14 verified facts, 1 to 2 takes, a real hook. Readable (grade 9 to 11) |
| 3 | Audit of run 2 found the voice layer leaking: *distressed*, *lower basis*, an owner's *decision*, a sweeping claim about "capital concentrating" | Tightened the voice gate: loaded labels, attributed decisions, sweeping claims, context lines must derive from their bank entry. 16 tests |
| 4 | Re-run with the tightened gate | The leaked takes are now cut. Output below |


---

## ejs-group-jv-secures-138m-refi-for-brooklyn-community (tier_c)

**What the brief chose:** shape *The Price Tells the Truth*, lens *capital cycle*. Protagonist: 12 Halsey, a 240-unit apartment building in Bedford-Stuyvesant, Brooklyn. Tension: The refinancing replaces a $108.2 million construction loan with a $137.5 million loan, but the new loan is only for three years and floating-rate, leaving the sponsors exposed to interest rate swings and a near-term maturity.

**Significance the brief wanted to claim:** This deal may illustrate lenders' willingness to provide floating-rate debt on newly delivered multifamily in Brooklyn, even as the market absorbs a wave of new supply.

### New engine, kept after the gate

Developers EJS Group and Hope Street Capital have secured a $137.5 million refinancing loan for 12 Halsey, a 240-unit community in Brooklyn’s Bedford-Stuyvesant neighborhood. **[voice]** That is a lot of new money against a building that just opened.

The refinancing retires a construction loan package amounting to $108.2 million, issued in 2023 by Bank OZK and CanAm Enterprises. AllianceBernstein issued the three-year, floating-rate debt package in a transaction arranged by Walker & Dunlop.

The property came online last year. **[take]** I read this as a lender willing to bet on a newly delivered building, but only for three years and at a floating rate.

Under New York’s affordable housing program 421-a, 12 Halsey features 72 income-restricted units. The property has studio, one- and two-bedroom layouts ranging from 481 to 1,207 square feet, along with 2,400 square feet of ground-floor retail space.

**[take]** This may be an early sign of how lenders are pricing newly delivered multifamily in Brooklyn—more flexible debt, but with a near-term maturity and floating rate.

**[voice]** What will the sponsors do when the three-year loan matures?

_6 facts · 2 takes · 2 voice lines · 1 sentences deleted · 179 words · 19.1 words per sentence · reading grade 10.0_

**Deleted by the gate:**

- *take* "The price tells the truth: the sponsors get more debt, but they also get a short fuse and rate exposure." → a take must be first person or plainly framed as opinion

### The old writer, same story (first three paragraphs)

Developers EJS Group and Hope Street Capital have secured a $137.5 million refinancing loan for 12 Halsey, a 240-unit community in Brooklyn’s Bedford-Stuyvesant neighborhood. AllianceBernstein issued the three-year, floating-rate debt package in a transaction arranged by Walker & Dunlop. The refinancing retires a construction loan package amounting to $108.2 million, issued in 2023 by Bank OZK and CanAm Enterprises.

The two-building community rises 10 stories and came online in 2025. Under New York’s affordable housing program 421-a, 12 Halsey features 72 income-restricted units. The property has studio, one- and two-bedroom layouts ranging from 481 to 1,207 square feet, along with 2,400 square feet of ground-floor retail space. Shared amenities include a fitness center, swimming pool, community room and a 59-spot subterranean p...

The refinancing suggests continued lender appetite for newly delivered Brooklyn multifamily assets, even as the loan replaces a smaller construction facility with a larger floating-rate package. Recent noteworthy multifamily refinancing deals in Brooklyn include the $370 million bridge loan The Carlyle Group and Property Markets Group received for the 517-unit Society Brooklyn in Gowanus, and the $374 million Barings...

_352 words · 26.6 words per sentence · reading grade 15.0 · 4 sentences the audit judged unsupported_


---

## prp-buys-downtown-office-building-from-tishman-speyer (tier_c)

**What the brief chose:** shape *The Price Tells the Truth*, lens *capital cycle*. Protagonist: PRP Real Assets, a D.C.-based investment firm that just bought 900 19th St. NW, a 117K SF office building that is roughly 60% vacant.. Tension: The building is 60% vacant, yet PRP bought it and will put more money in. The tension is between the current owner's unwillingness to reinvest and PRP's bet that a 'good building, bad balance sheet' can be turned around. There is no explicit clock, but the vacancy and need for lease-up create urgency.

**Significance the brief wanted to claim:** This deal may be an early sign of a broader pattern: investors with capital are buying distressed office buildings at low prices to reposition them, betting on lease-up in a market where some owners are unwilling to reinvest.

### New engine, kept after the gate

A downtown office building that’s roughly 60% vacant has a new owner with a lease-up and small-scale improvement plan.

D.C.-based investment firm PRP Real Assets on Tuesday closed on a 117K SF office building at 900 19th St. NW. The firm paid around $30M for the building, PRP Chief Investment Officer Jon McAvoy told Bisnow.

**[take]** I read the price as an admission that the old basis no longer works.

The 1979-era office building was sold by Tishman Speyer, which had owned it since 2006 and completed a substantial renovation in 2017. McAvoy called the deal a “basis reset” and said that gave the firm the opportunity to reinvest.

The 60% vacancy is concentrated on three empty floors, each 16K SF, which would position the building for an anchor tenant opportunity. McAvoy said PRP is assessing all interest.

PRP plans to infuse six figures into modifications within the next year.

**[voice]** If the building is good, what does that say about the balance sheet?

_8 facts · 1 takes · 1 voice lines · 3 sentences deleted · 164 words · 16.7 words per sentence · reading grade 8.4_

**Deleted by the gate:**

- *take* "That price is the whole story." → a take must be first person or plainly framed as opinion
- *fact* "McAvoy said PRP is interested in replicating the deal at other properties in the city." → fact rejected by the fact check
- *take* "I read this as an early sign that capital is starting to buy distressed office buildings at low prices to reposition the" → uses loaded labels the cited facts do not use: distressed

### The old writer, same story (first three paragraphs)

D.C.-based investment firm PRP Real Assets closed Tuesday on a 117K SF office building at 900 19th St. NW, paying around $30M, according to PRP Chief Investment Officer Jon McAvoy. The 1979-era building, sold by Tishman Speyer, is roughly 60% vacant. Tishman confirmed the sale closed but declined to comment on the transaction.

Tishman Speyer had owned the property since December 2006, when it paid $11.3M to Carr Properties, deed records show. The seller completed a substantial renovation in 2017. PRP plans to infuse six figures into modifications within the next year. McAvoy described the deal as a "basis reset" that gives the firm an opportunity to reinvest. The vacancy is concentrated on three empty floors of 16K SF each, which PRP says ...

The acquisition fits a stated PRP strategy of finding buildings where current owners may not be interested in reinvesting. McAvoy called the model "good building, bad balance sheet" and said PRP is looking to replicate it at other D.C. properties. The firm's larger recent presence includes its 2024 purchase of Market Square, the twin Pennsylvania Avenue properties surrounding the Navy Memorial, for $323M. The new ass...

_291 words · 19.7 words per sentence · reading grade 11.2 · 2 sentences the audit judged unsupported_


---

## brookfield-asset-management-q2-2026 (tier_b)

**What the brief chose:** shape *The Number That Doesn't Fit*, lens *capital cycle*. Protagonist: Brookfield Asset Management. Tension: The tension is between scale and execution. Brookfield raised a record $77 billion, but deploying that capital wisely—especially in new areas like AI infrastructure—while integrating Oaktree and managing a much larger asset base is a challenge. The sources show no explicit constraint, but the implicit tension is whether the firm can sustain its growth without stumbling.

**Significance the brief wanted to claim:** The concentration of capital in a single quarter at Brookfield may illustrate how the largest alternative asset managers are absorbing a disproportionate share of investor commitments, especially into AI infrastructure.

### New engine, kept after the gate

Brookfield Asset Management raised a company record $77 billion in the second quarter of 2026, bringing its assets under management to more than $1 trillion.

Year-to-date, the investor has brought in $98 billion, more than half of what Brookfield raised for all last year. It also deployed $21 billion this past quarter.

Brookfield secured $5 billion in commitments for its first AI Infrastructure Fund. Brookfield increased its financing framework with Bloom Energy for AI infrastructure power projects to $25 billion, up from the $5 billion commitment announced in October 2025. Brookfield also completed its purchase of Oaktree, buying the remaining 26 percent stake for about $3 billion.

Brookfield’s seventh flagship private equity fund raised $6.7 billion during the quarter. Its sixth flagship infrastructure fund brought in $9.3 billion. Both are on pace to become the largest funds of their respective vintages.

On the real estate front, Brookfield raised $4.3 billion across segment funds and deployed $5.2 billion. It bought a privately held U.S. manufactured-home portfolio and took an outdoor industrial storage portfolio private.

Net income grew to $1.17 billion this past quarter, almost double from a year prior. Fee-related earnings climbed 20 percent year-over-year to $808 million. Distributable earnings grew to $707 million, up by 15 percent year-over-year.

_14 facts · 0 takes · 0 voice lines · 6 sentences deleted · 214 words · 15.9 words per sentence · reading grade 8.7_

**Deleted by the gate:**

- *take* "I read that as a staggering amount of trust placed in one firm in ninety days." → a view or action may not add figures: 90
- *take* "That gap between raising and deploying is the whole tension." → a take must be first person or plainly framed as opinion
- *voice* "The obvious read is that scale is everything." → Asserts a substantive claim that scale is everything, which could be true or false.
- *take* "But I think the real story is how Brookfield is using that scale to push into AI infrastructure and consolidate credit." → attributes a private state or decision (wants, fears, decided, knows...) to a party the facts do not support
- *take* "I think this quarter shows the largest alternative asset managers are absorbing a disproportionate share of investor com" → Makes a broad comparison about largest alternative asset managers not supported by the cited facts.
- *voice* "The question is whether Brookfield can deploy that capital as effectively as it raised it." → voice lines may not name anyone or anything

### The old writer, same story (first three paragraphs)

Brookfield Asset Management reported a company record $77 billion in capital raised during the second quarter of 2026, lifting its assets under management above $1 trillion, according to an earnings call covered by Commercial Observer. The result matters because it signals accelerating institutional demand across Brookfield's private equity, infrastructure, credit, and real estate strategies at a time when the firm i...

The quarter's mechanics were broad-based. Brookfield's seventh flagship private equity fund raised $6.7 billion, while its sixth flagship infrastructure fund brought in $9.3 billion, putting both on pace to become the largest funds of their respective vintages. The firm also secured $5 billion in commitments for its first AI Infrastructure Fund and increased its financing framework with Bloom Energy for AI infrastruc...

The evidence comes from a single full-text secondary source, Commercial Observer, which reported on Brookfield's earnings call. The article quotes Sikander Rashid, Brookfield's global head of AI infrastructure, who said the firm can "source and entitle power land, develop and operate large-scale AI factories, deliver behind-the-meter and baseload power, provide contracted compute, and pursue partnerships with some of...

_632 words · 33.1 words per sentence · reading grade 18.0 · 10 sentences the audit judged unsupported_


---

## What the samples prove

1. **The mechanism works.** A piece can have a hook, a turn, a point of view, a meaning paragraph and a kicker, while every factual sentence stays traceable to a quote and every opinion is machine-checked. Nothing in the old writer's output could say that.
2. **The gate does real work on the voice.** In run 2 it let through *"distressed buildings at a lower basis"* and an owner who *"decides not to reinvest"*. Both were unsupported. After tightening, both are deleted. That is exactly the failure that would have embarrassed us.
3. **The takes are honest but generic.** *"I read this as a lender willing to bet on a newly delivered building"* is fair and safe, and it is also what any analyst would say. The voice has the right shape but not yet the spark.
4. **The most ambitious meaning gets cut.** The brief wanted to claim larger patterns (capital concentrating in mega-managers, distressed buying). The sources do not support them, so the gate removes them and the piece falls back to plain facts. That is correct, and it is the ceiling of what one article can honestly say.
5. **Kickers are the weakest part.** Lines like *"If the building is good, what does that say about the balance sheet?"* are cryptic. This is a prompt and editor-pass problem, not a gate problem.
6. **It is slow.** 100 to 290 seconds per story with two attempts and reasoning-mode checks. At 70 stories a day that does not fit the current window; tier it (full engine for flagships and analyses, light path for briefs) before turning it on.

## What it will take to reach the standard you described

The prompt gets us a readable, structured, voiced, truthful piece. To get to *prize-worthy*, three inputs matter more than any further prompt tuning:

1. **Richer raw material.** A single trade article gives a deal. A story needs two or three sources, the primary document (the filing, the order, the loan record), and a human quote. Stage 6 (read the articles) should fetch more, and the dossier should say when the story is thin so the piece stays short.
2. **Your own material.** Ten to fifteen real notes in `ben-notes.json`, and a handful of your best past posts to calibrate the voice (few-shot, used for rhythm and attitude, never for facts). Without them the "I" can only judge and react, never remember.
3. **Verified context.** A first batch of 20 entries in `context-bank.json` (history, policy, macro background, each with a source). This is what gives a Brooklyn refinance its place in a larger story without inventing history.

After that: the editor pass (score on the ten-point scorecard, one rewrite), then the LinkedIn A/B.
