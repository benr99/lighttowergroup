# Light Tower Group — Full Copy, Design & Conversion Audit
## Benchmarked against Krinsky Design client project websites

**Sites studied:** bayharbortowers.com, tower77bk.com, 110coffey.com, cahope.com (Casa Hope), and the case study portfolios for Onyx Residences, Bay Harbor Towers, OneTen Coffey, Tower 77

---

## 1. Executive Summary

LTG's current site has strong bones — the dark editorial palette, the wizard-based contact flow, the transaction tombstones, and Ben's direct principal involvement story are all genuine assets. But the site buries them under too much text, too many competing CTAs, and a navigation that overwhelms before a sponsor can decide to trust.

Krinsky's client work (Bay Harbor Towers, Tower 77, OneTen Coffey) proves that luxury real estate audiences respond to: one dominant image, one clear headline, minimal nav, short editorial subheads, and exactly two CTAs. Every Krinsky project opens with a full-bleed architectural photograph and a few words of confident positioning. Everything else is secondary.

The gap: LTG uses 10+ nav items where 5 would suffice. The hero packs 4 competing content zones where 1 would convert better. The copy hedges where it should declare. And the visual evidence that would make a sponsor trust the firm — photographs of financed properties, maps of deal coverage, lender logos — is missing entirely.

**First fix:** Rewrite the hero copy. Replace the multi-zone hero with one photograph, one confident headline, and one CTA. Then cut the nav to 5 items. Everything else follows from there.

---

## 2. Principle-by-Principle Gap Analysis

### Principle 1: The hero is a photograph, not a paragraph
**Krinsky benchmark:** Full-bleed architectural rendering, property name in massive display serif, one positioning line. Bay Harbor Towers opens with a waterfront rendering and "A collection of forty-four private residences, marking the arrival of a new waterfront icon." That's it.

**LTG current state (index.html lines 1983-2038):** The hero contains:
1. A hero picture (capital architecture diagram — abstract, not photographic)
2. A meta bar: "Commercial Real Estate Capital Advisory · New York · Nationwide"
3. A kicker: "Debt · Equity · Recapitalization"
4. A headline in `award-title`: "Debt and equity capital for commercial real estate."
5. A 22-word summary paragraph
6. Two CTA buttons
7. An "Engagement Profile" sidebar with 3 numbered items
8. A 3-column footer bar with service categories
9. A scroll-down arrow

**Gap grade: D.** Eight content zones compete for attention. A sponsor must scan the entire hero to understand what LTG does. Krinsky delivers that in 3 seconds.

**Fix:** Collapse to: 1 full-bleed photograph → 1 firm name → 1 positioning line → 1 CTA + phone.

---

### Principle 2: Navigation earns its place
**Krinsky benchmark:** 4-7 items, single-word labels, no dropdowns. Bay Harbor: 8 items (Vision, Residences, Lifestyle, Neighborhood, Floorplans, Press, Team, Inquire). Tower 77: 7 items. All one or two words.

**LTG current (index.html lines 1955-1978):** 10 distinct links in the main nav on the observatory version: Expertise, Transactions, Process, Intelligence, About, "Request a Deal Review" CTA — plus additional links on other pages (Practice, Advantage, Executions, Leadership, FAQ, Ideas, Buildings, Services, Contact). On subpages like `services.html` (line 110-121), the nav balloons further.

**Gap grade: F.** The nav changes between pages. Some pages show 10+ items. No sponsor needs "Ideas" AND "Intelligence" AND "Buildings" AND "Insights" in the main nav.

**Fix:** Consolidate to: **Expertise · Transactions · Intelligence · About · Contact** + one CTA button. Move Ideas, Buildings, FAQ, Leadership, Process sections to within-page anchors or the footer. The content stays — the nav just stops shouting it all at once.

---

### Principle 3: Copy is editorial, not explanatory
**Krinsky benchmark:** "Bay Harbor islands most coveted waterfront address." "Where Culture and Community Intersect." "Architectural excellence meets interior design perfection." Every headline is a claim that evokes feeling, not a functional description.

**LTG current headlines (all functional):**
- "Selected debt and equity assignments" (line 2045)
- "Debt, equity, and recapitalization advisory" (line 2131)
- "A three-step capital process" (line 2212)
- "What to know before requesting a review" (line 2297)

**Gap grade: C-.** These are accurate descriptions. They are not editorial claims that make a sponsor want to keep reading. They sound like section labels in a PPM, not a brand.

**Rewrite candidates (editorial style):**
| Current | Krinsky-style rewrite |
|---|---|
| "Selected debt and equity assignments" | "Deals closed. Terms delivered." |
| "Debt, equity, and recapitalization advisory" | "Every layer of the capital stack." |
| "A three-step capital process" | "Structure first. Source second." |
| "What to know before requesting a review" | "What you should know before we talk." |

---

### Principle 4: Sections follow a consistent rhythm
**Krinsky benchmark:** Full-bleed image → eyebrow label → editorial headline → 1-2 sentence description → CTA link. Alternating light/dark backgrounds. Same pattern, every section.

**LTG current:** The homepage mixes tombstone grids (6-up, line 2047), advantage grids (4-up, line 2102), service rows (3 numbered items, line 2133), advantage grids again (3-up, line 2187), process columns (3-up, line 2214), a split-grid leadership section (line 2236), an FAQ accordion (line 2299), and a wizard-based form grid (line 2366). No two sections share the same layout pattern.

**Gap grade: D.** The page is a layout sampler, not a rhythm. A sponsor feels cognitive fatigue halfway through.

**Fix:** Adopt one section pattern and repeat it 6 times. The Krinsky pattern (image → eyebrow → headline → short copy → CTA) adapts perfectly to LTG's content. See Section 6 for the proposed flow.

---

### Principle 5: Color is a system, not decoration
**Krinsky benchmark:** Black/charcoal, white/cream, one metallic accent. Usually 3 colors total. Bay Harbor uses dark blue/black backgrounds with cream text and gold accents.

**LTG current:** The CSS contains 3+ layered design systems (legacy light theme, dark observatory, Capital After Dark 2026 with `experience-2026.css`). The `site.css` file alone (line 1091-1104) overrides everything with a new palette: `--ltg-bg: #f3efe7`, `--ltg-accent: #795a2d`, `--ltg-accent-action: #b9975a`, plus separate `--x26-signal`, `--x26-wine`, `--x26-slate`, `--x26-mist`, `--x26-oxblood` tokens. The net effect is an identity that hasn't decided what color it is.

**Gap grade: D.** There are at least 15 color tokens in active use across competing stylesheets.

**Fix:** Pick one palette and retire the others. Recommended: the dark/observatory foundation with one warm metallic accent (the current `#c9a96a` is solid). Remove the light-mode fallback entirely — institutional capital advisory doesn't need a cream background.

---

### Principle 6: Typography hierarchy uses massive contrast
**Krinsky benchmark:** Display serif headlines at 5-8rem. Restrained body text. 3-4 font size tiers total. Bay Harbor Towers' "Bay Harbor Towers" hero text is enormous.

**LTG current:** The site uses golden-ratio-based sizing (phi-1 through phi-5, CSS lines 194-199) creating 5+ size tiers plus responsive variants, plus observatory-specific overrides (lines 1793-1803), plus experience-2026 overrides. The hero headline uses `clamp(4.1rem, 7.3vw, 8.5rem)` (line 1793) — that's actually good. But the rest of the hierarchy is fragmented: eyebrow labels, section heads, subheads, card labels, meta text, form labels, and footer text all sit at different sizes with no clear relationship.

**Gap grade: C+.** The hero typography is actually strong — the headline scale is correct. The problem is everything below it.

**Fix:** Collapse to 4 tiers: Display (hero, 4-8.5rem), Section Headline (subheads, 2-3.2rem), Body (1-1.3rem), Label (eyebrows/nav/CTAs, 0.62-0.68rem). Remove the phi-based system which creates too many intermediate steps.

---

### Principle 7: The CTA is binary and prominent
**Krinsky benchmark:** Phone number at top-right + one "Inquire" or "Apply Now" button. That's the entire CTA system. OneTen Coffey embeds the form directly on the homepage.

**LTG current:** 7 competing CTAs:
1. "Discuss Your Deal" (nav button, line 1964)
2. "Request a Confidential Deal Review" (hero, line 2003)
3. "View Representative Transactions" (hero ghost, line 2004)
4. "Start a confidential review →" (sidebar link, line 2028)
5. Email link (line 2375)
6. Phone link (line 2375)
7. Chat widget (line 2775)

**Gap grade: F.** A sponsor doesn't know which action to take first. The 3-step wizard adds more friction: pick a card, pick two dropdowns, fill 5 fields. Minimum 8 interactions to submit.

**Fix:** Two CTAs sitewide: "Start a Capital Review" (button → single-step form) + phone number. Embed the form on the page, not behind a 3-step wizard. Kill the wizard or reduce it to a single screen.

---

### Principle 8: Trust is visual, not asserted
**Krinsky benchmark:** Building photography, developer logos in footer, "80% Sold" labels, press mentions. The images communicate trust before words do.

**LTG current:** Trust is asserted through text — anonymized transaction dollar amounts (lines 2051-2089), a FAQ about confidentiality (lines 2299-2361), "Principal-Led" labels. The most powerful visual evidence — real buildings LTG helped finance — is absent.

**Gap grade: D+.** The transaction tombstones are the right idea but they're text-only in a grid. No photography of any property LTG has worked on.

**Fix:** Acquire or license photographs of 3-4 financed properties (with client permission, or use representative skyline/aerial imagery). Place one full-bleed photo in the proof section. Add developer/lender logos if permitted.

---

### Principle 9: Photography sells the outcome
**Krinsky benchmark:** Interior renders, exterior aerials, waterfront views, amenity spaces. Every photo shows what the buyer gets.

**LTG translation:** Show what the sponsor gets — closed deals, financed buildings, real assets. The capital-stack 3D diagram (line 1533-1549) is clever but abstract. A sponsor doesn't want to see a diagram of capital. They want to see evidence that LTG closes.

**Gap grade: D.** The primary visual is an abstract CSS 3D animation. The only real photograph on the page is Ben's portrait (line 2243).

**Fix:** Replace the capital-stack diagram with a full-bleed photograph in the hero. Keep the diagram for an interior page or the services section. The hero should show a building — any building — that signals the scale and seriousness of the work.

---

### Principle 10: Location/coverage is featured visually
**Krinsky benchmark:** Every project has a dedicated neighborhood section with maps, area photography, and local context. "Red Hook, Brooklyn" is part of OneTen Coffey's identity.

**LTG translation:** LTG's coverage is "U.S. commercial real estate — nationwide." This should be shown visually — a map, skyline photography from multiple cities, or a list of markets where deals have closed.

**Gap grade: C-.** Coverage is asserted in text ("New York · Nationwide" in the meta bar, line 1993) but never shown. There's a property-type tag grid mentioned in CSS (line 742-764, `asset-tag` class) but I don't see it rendered in the current observatory layout — it may be legacy.

**Fix:** Add a visual coverage section — either a map showing deal locations, or city skyline photography from key markets (NYC, Miami, Chicago, LA, etc.).

---

## 3. Copy Audit Results

### 3.1 Hedge Words Found (homepage only)

| Line | Current text | Hedge word(s) | Rewrite |
|---|---|---|---|
| 147 (JSON-LD) | "Light Tower Group typically starts at $5 million" | typically | "$5 million minimum." |
| 2017 | "Assignments evaluated for fit" | evaluated for fit | "$5M+ capital needs. Qualified sponsors." |
| 2116 | "with control, economics, and senior debt in view" | in view | "across control, economics, and senior debt terms." |
| 2317 (FAQ) | "We typically evaluate assignments with capital needs of $5 million and above. Fit also depends on the sponsor, property, structure, market, and timing." | typically, depends on | "$5 million minimum. We'll assess fit in the first conversation." |

**Total hedges on homepage copy: 4.** In Krinsky's voice: 0.

### 3.2 Sentences Over 20 Words (homepage body copy)

| Line | Words | Sentence |
|---|---|---|
| 2001 | 22 | "Light Tower Group helps sponsors arrange debt, equity, and recapitalization capital for U.S. commercial real estate transactions of $5 million and above." |
| 2139 | 26 | "Financing for acquisitions, refinancing, construction, bridge, and permanent needs. We define the request, identify relevant lenders, and manage the process through closing." |
| 2153 | 23 | "Joint venture, preferred equity, mezzanine, and co-GP capital for acquisitions, development, and recapitalizations. We evaluate economics, control, and fit before outreach." |
| 2167 | 24 | "Capital-stack analysis when existing debt, sponsor equity, or the business plan no longer align. We compare restructuring, replacement, and new-capital options." |
| 2270 | 27 | "Benjamin Rohr is the Principal and Founder of Light Tower Group. He works directly with sponsors to evaluate capital needs, define the financing strategy, and manage debt, equity, and recapitalization assignments." |
| 2374 | 30 | "Share the property, capital need, timing, and current status. Benjamin Rohr will review the assignment and respond with the appropriate next step within one business day." |

**Longest sentence: line 2374 — 30 words.** Krinsky-style maximum: 12 words per sentence on the homepage.

### 3.3 Jargon Density (homepage body copy above the fold)

The hero summary paragraph (line 2001) contains **5 industry terms in 22 words**: "sponsors," "debt," "equity," "recapitalization," "capital," "commercial real estate transactions." That's one term every 4.4 words. A sponsor may navigate this but a referral source (attorney, accountant, family office) may not.

### 3.4 Redundancy Analysis

The phrase "debt, equity, and recapitalization" (or its variants) appears **7 times** on the homepage alone:
- Line 1998: kicker
- Line 2001: hero summary
- Line 2033: hero footer
- Line 2131: services headline
- Line 2270: leadership bio
- Line 2380: form trust item
- Line 2520: footer description

This is the core offering, but repeating it verbatim 7 times signals uncertainty, not confidence. Krinsky never repeats their positioning line. They state it once and let the work prove it.

---

## 4. Conversion Path Analysis

### 4.1 The 5-Second Test

| Question | Current score | Target | Gap |
|---|---|---|---|
| What does this firm do? | 5/10 | 9/10 | The hero requires reading 3 zones to understand the offer. "Debt and equity capital for commercial real estate" is actually a good headline — it just gets drowned by everything around it. |
| Is it for me? ($5M+, sponsor type) | 4/10 | 8/10 | Buried in the sidebar (line 2017) and FAQ (line 2317). Not immediately visible. Krinsky puts "80% Sold" at the very top of Bay Harbor — immediate qualification. |
| What do I do next? | 3/10 | 9/10 | There are 7 competing CTAs. A sponsor doesn't know whether to click "Discuss Your Deal," "Request a Review," "View Transactions," or scroll to the form. |

### 4.2 Form Friction

Current wizard (lines 2384-2503): 3 steps, 8+ interactions, 5 text fields.

Proposed single-step form:
- Name (required)
- Email (required)
- Phone (optional)
- Brief description (required — "Property, capital need, timeline")
- Submit button: "Request Capital Review"

Total: 4 fields, 1 button, 1 step.

### 4.3 Trust Signal Gaps

| Trust signal | Krinsky clients | LTG current | LTG needed |
|---|---|---|---|
| Property photography | Every page | Photo of Ben only | 3-4 photos of financed properties |
| Institutional logos | Developer logos in footer | None | Lender types or partner categories |
| Social proof | "80% Sold" | Anonymized transactions | Add a live metric (e.g., "$X in assignments reviewed this year") |
| Press mentions | Press section | None | Any media, podcast, or publication mentions |
| Principal presence | N/A (they sell buildings) | Ben photo buried mid-page (line 2243) | Move Ben higher — or add a "From the Principal" sidebar in the hero |

---

## 5. Full Homepage Copy Rewrite (Krinsky-Style)

### Hero Section

**Visual:** Full-bleed photograph of a financed commercial property (NYC skyline, office tower, or multifamily building at dusk).

**Copy:**

```
NEW YORK · NATIONWIDE

Light Tower Group

Debt and equity for commercial real estate.

$5M minimum. Principal-led. One conversation to start.

[REQUEST A CAPITAL REVIEW]    (347) 554-0093
```

**Removed:** The entire engagement profile sidebar, the footer service bar, the capital-stack diagram, the second CTA button, the scroll arrow.

---

### Section 2: What We Do

```
CAPITAL ADVISORY

Every layer of the capital stack.

Senior debt. Bridge and construction financing. Joint venture and preferred
equity. Mezzanine and co-GP capital. Recapitalization. We structure the full
stack, then run the process through closing.

[VIEW ALL SERVICES →]
```

**Replaces:** Current "What We Do" section (lines 2128-2179) with 3 accordion-like service items and 9+ service tags. The services detail pages stay — the homepage just stops listing every sub-service inline.

---

### Section 3: Proof (Transactions)

```
REPRESENTATIVE ASSIGNMENTS

Deals closed. Terms delivered.

$47M  Multifamily Portfolio  —  Brooklyn, NY  ·  Senior Debt
$61M  Ground-Up Development  —  Brooklyn, NY  ·  Construction
$38M  Office Conversion     —  Manhattan, NY  ·  Bridge Financing
$23M  Mixed-Use Development —  Manhattan, NY  ·  JV Equity
$18M  Multifamily Recap     —  Queens, NY     ·  Preferred Equity
$14M  Industrial Conversion —  Bronx, NY      ·  Mezzanine

[VIEW ALL TRANSACTIONS →]
```

**Replaces:** The tombstone grid (lines 2047-2091) with a tighter list format. Current grid spacing is generous but wastes vertical space on mobile.

**Add:** One full-bleed photograph above the transaction list — a building that was financed through LTG, or a representative architectural image.

---

### Section 4: Why Light Tower Group

```
WHY US

Direct access to the principal. A capital plan before the market sees
the deal. Outreach that targets the right lenders — not every lender.

Benjamin Rohr leads every engagement from the first review through
closing coordination. No junior handoffs. No generic blasts.

[ABOUT BEN →]
```

**Replaces:** The "Why Light Tower Group" section (lines 2182-2206) with its 3 advantage cards and the process section (lines 2209-2233). Combines "Why" and "How" into one tight section. The 3-step process detail stays on an interior page.

---

### Section 5: Markets & Coverage

```
COVERAGE

Commercial real estate across the United States.

Multifamily · Office · Industrial · Retail · Hospitality · Mixed-Use ·
Self-Storage · Student Housing · Medical Office · Data Center · Development

New York · Miami · Chicago · Los Angeles · Dallas · and nationwide.

[START A CAPITAL REVIEW →]
```

**Replaces:** The missing coverage section. Currently coverage is only asserted in the meta bar ("New York · Nationwide") and the FAQ.

---

### Section 6: Contact

```
START THE CONVERSATION

A confidential review of your deal. No retainer. No obligation.

Share the property, the capital need, and the timeline. Benjamin Rohr
responds within one business day.

[EMBEDDED FORM: Name · Email · Phone · Description · SUBMIT]

Prefer to call? (347) 554-0093
ben@lighttowergroup.co
```

**Replaces:** Current contact section (lines 2366-2509) with its 3-step wizard, form intro, trust items, and separate email/phone links. Single form replaces the wizard.

---

## 6. Navigation Proposal

**Current (observatory, index.html lines 1959-1964):**
Expertise | Transactions | Process | Intelligence | About + "Request a Deal Review"

**Current (services.html, lines 110-121):**
Practice | Advantage | Executions | Leadership | FAQ | Intelligence | Ideas | Buildings | Services | About | Contact + "Discuss Your Deal"

**Proposed (sitewide, 5 items + CTA):**

| Nav item | Maps to |
|---|---|
| **Expertise** | Current Services page + all individual service pages |
| **Transactions** | Current transactions page (moves tombstone detail here) |
| **Intelligence** | Current Insights + Ideas combined under one archive |
| **About** | About page + Leadership section |
| **Contact** | Anchor to bottom form |

**CTA button:** "Start a Capital Review" → scrolls to contact form

**Moved to footer:** Buildings, FAQ (or folded into About/Contact pages), Process (folded into Expertise), Privacy, RSS

---

## 7. Design Enhancement Backlog (Priority-Stacked)

### Immediate (under 2 hours each)

| # | Change | Impact | Effort |
|---|---|---|---|
| 1 | Rewrite hero copy following Section 5 above | High | Small |
| 2 | Remove hedge words (4 instances, see 3.1) | High | Small |
| 3 | Consolidate to 2 CTAs: "Start a Capital Review" + phone | High | Small |
| 4 | Replace 3-step wizard with single-step form (4 fields) | High | Medium |
| 5 | Cut nav to 5 items + 1 CTA sitewide | High | Small |
| 6 | Remove redundant "debt, equity, recapitalization" repeats — keep 2 instances max | Medium | Small |
| 7 | Simplify section headlines using editorial rewrites (see Principle 3) | Medium | Small |

### This week

| # | Change | Impact | Effort |
|---|---|---|---|
| 8 | Find or commission hero photograph (financed property, city skyline, or institutional image) | High | Medium |
| 9 | Restructure homepage to 6 alternating sections (see Section 5 flow) | High | Medium |
| 10 | Collapse typography to 4 tiers (see Principle 6) | Medium | Medium |
| 11 | Add single-step embedded form to contact section | High | Medium |
| 12 | Consolidate CSS — retire legacy light-mode variables, keep dark/observatory palette | Medium | Medium |

### Next sprint

| # | Change | Impact | Effort |
|---|---|---|---|
| 13 | Source 3-4 financed-property photographs for proof section | High | Medium |
| 14 | Add lender/institutional partner category section (logos if permitted) | Medium | Medium |
| 15 | Add visual coverage map or city photography for Markets section | Medium | Medium |
| 16 | Move Ben's photo and bio higher on the page (or into hero sidebar) | Medium | Small |
| 17 | Consolidate Ideas + Insights into single Intelligence archive | Medium | Medium |
| 18 | Mobile audit: test form, hero, nav at 375px width | Medium | Small |

### Longer-term

| # | Change | Impact | Effort |
|---|---|---|---|
| 19 | Acquire client-permitted case studies with building photography | High | Large |
| 20 | Add press/media section if any coverage exists | Medium | Small |
| 21 | Animate section transitions (Krinsky uses subtle fade-in on scroll) | Low | Medium |
| 22 | A/B test "Start a Capital Review" vs "Submit Your Deal" vs "Request Review" | Medium | Small |

---

## 8. Voice & Tone One-Pager

### The 4 Rules

1. **State, don't explain.** "Senior debt, bridge, construction — structured and closed." Not "We evaluate financing options and identify relevant lenders."

2. **One idea per sentence.** If a sentence has a comma and an "and," split it. Current example (line 2167): "Capital-stack analysis when existing debt, sponsor equity, or the business plan no longer align. We compare restructuring, replacement, and new-capital options." → Rewrite: "When the stack no longer works, we restructure it. Debt. Equity. Both."

3. **Cut every hedge.** Replace "typically," "depending on," "evaluated for fit," "in view" with declarative language. The sponsor wants to know if LTG can help, not under what conditions LTG might consider helping.

4. **Lead with outcome.** Not "Benjamin Rohr leads the engagement" but "You work directly with Benjamin Rohr. First call to closing."

### Words to Retire

| Eliminate | Replace with |
|---|---|
| typically | (remove — just state the fact) |
| depending on | "subject to" (if qualification needed) or remove |
| evaluated for fit | "Qualified sponsors only" |
| in view | "across" or remove |
| appropriate | (remove — if it's appropriate, just do it) |
| may / can (when hedging) | "will" or restructure sentence |
| manage the process | "close the deal" or "run through funding" |
| identify relevant | "target" |
| capital-provider outreach | "the process" or "market engagement" |

### Words to Lead With

Close. Structure. Deliver. Direct. Terms. Timing. First conversation. Confidential. Principal-led. One business day. Qualified. Institutional. Nationwide.

---

## 9. Quick Wins (Under 2 Hours, Ranked by Impact)

1. **Rewrite hero (15 min):** Replace current hero copy with the rewrite in Section 5.
2. **Kill hedge words (10 min):** Run find/replace on the 4 hedges in 3.1.
3. **Cut nav to 5 items (30 min):** Update nav on index.html, services.html, about.html, and all sub-pages.
4. **Consolidate CTAs (15 min):** Remove "View Representative Transactions" ghost button from hero. Keep one primary CTA + phone.
5. **Remove redundancy (10 min):** Delete "debt, equity, and recapitalization" from 5 of its 7 appearances. Keep it in the hero kicker and the footer.

---

## 10. Open Questions

1. Are there client-permitted photographs of financed properties available? (This is the single highest-leverage design improvement.)
2. Does LTG have permission to name any institutional lenders or partners? Even generic categories ("Life Companies," "Debt Funds," "Regional Banks") would add trust.
3. Is there press coverage, podcast appearances, or conference speaking that can be cited?
4. Has the single-step form been tested against the wizard? (The wizard collects good qualification data — consider keeping it but collapsing to 1 screen.)
5. Should "Intelligence" and "Ideas" be separate archives, or merged? They serve similar audiences.

---

*Audit completed. The site is better than most boutique advisory firm websites. The gap is not quality — it's discipline. Fewer words, fewer choices, fewer sections, and one clear path from landing to conversation. That's the Krinsky way, translated to capital advisory.*
