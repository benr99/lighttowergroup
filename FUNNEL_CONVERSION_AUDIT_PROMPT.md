# Light Tower Group — Marketing Funnel & Sign-Up Velocity Audit

## How this differs from the existing copy/design audit

[COPY_DESIGN_AUDIT_PROMPT.md](COPY_DESIGN_AUDIT_PROMPT.md) and its
[report](COPY_DESIGN_AUDIT_REPORT.md) already benchmark LTG's homepage against
Krinsky Design's luxury-real-estate client sites on **visual/editorial brand
fit** (hero composition, color system, typography, section rhythm, photography).
Read that report first — do not re-litigate its findings.

This prompt is narrower and more mechanical: **given the brand as it stands
today, how do we get a qualified sponsor from "landed on a page" to "submitted
a deal" in the fewest seconds, clicks, and moments of doubt?** It treats the
site as a lead-generation funnel, not a brand surface, and it ends in a
ranked, testable backlog — not a rewrite.

There is exactly one conversion event on this site: a submitted entry in the
wizard at `#contact` → `POST /.netlify/functions/mandate-submit` (index.html,
lines 2366-2509). Every page and every CTA either feeds that funnel or leaks
a visitor who would have. "Sign up" for LTG means "submit a capital review
request" — treat that as the equivalent of a SaaS sign-up throughout.

## Ground truth to work from (already confirmed in this repo)

- The wizard is 3 steps: (1) pick Debt / Equity / Advisory as a card, (2) two
  required `<select>` dropdowns — Asset Type, Deal Size, (3) five fields —
  Name*, Company*, Email*, Phone, Message — then submit. That's 6 required
  fields plus a card pick across 3 screens before the button that actually
  submits (index.html:2395-2496).
- The hero still carries two competing CTAs — "Request a Confidential Deal
  Review" (primary, → `#contact`) and "View Representative Transactions"
  (ghost, → `#transactions`) — plus a hedge phrase, "Assignments evaluated for
  fit" (index.html:2003-2004, 2017).
- Nav is already consolidated to 5 items + 1 CTA (index.html:1955-1978) — that
  fix from the prior audit shipped. Don't re-flag it.
- `visitor-analytics.js` tracks `page_view`, `engaged_15s/60s`,
  `scroll_50/90`, `outbound_click`, `page_exit` (visitor-analytics.js:173-224)
  but there is **no event fired anywhere for wizard step advance, wizard
  abandon, or successful form submit**. We are flying blind on exactly the
  drop-off we're trying to fix. Confirm this and treat closing it as a
  prerequisite, not a nice-to-have — every recommendation below should be
  framed as a hypothesis to validate once we can see step-by-step drop-off,
  not a change to ship on faith.
- The success state promises a response "within one business day"
  (index.html:2501-2502), and the same promise is repeated in the form intro
  (index.html:2374) and the FAQ. There is no path to same-session scheduling
  (e.g., an embedded calendar) — a qualified, warm sponsor who wants to talk
  now has no faster option than "wait for an email."
- Every service subpage (bridge-financing.html, senior-debt.html,
  agency-lending.html, cmbs.html, construction-financing.html,
  life-company-financing.html, preferred-equity.html, joint-venture-equity.html,
  origination.html, plus transactions.html, about.html, insights.html,
  ideas.html) is a separate funnel entry point. Confirm whether each one links
  its CTA to the same generic `#contact` wizard with no pre-fill, or whether
  any pass context forward (e.g., a bridge-financing visitor should not have
  to re-select "Debt" and re-explain they need bridge capital from scratch).

## Objective

Reduce **time-to-submit** and **submits per qualified visitor**, without
lowering lead quality below what the current 6-field wizard produces. Every
recommendation must state which of those two levers it pulls, and what it
might cost the other one (e.g., cutting fields raises submit rate but may
raise unqualified/junk submissions — say so explicitly).

## Part 1 — Funnel Map

Diagram the actual paths a visitor can take, for at least these three entry
scenarios:
1. Cold organic/search visitor lands on `index.html` homepage.
2. Referral or targeted-ad visitor lands on a specific service page (e.g.
   `bridge-financing.html`) because they searched or were pitched that exact
   product.
3. Warm referral visitor who was told to "just fill out the form" by an
   attorney, broker, or existing contact.

For each, trace every click from landing to submitted form. Count clicks,
fields, and decisions (a dropdown choice counts as a decision). Flag every
point where the visitor could plausibly bounce, and name the reason (unclear
what to do next, asked for information they don't have yet, no way to skip a
step, no reassurance the wait is worth it, etc.).

## Part 2 — Instrumentation Gap (do this before proposing A/B tests)

1. Confirm the absence of wizard/form funnel events in `visitor-analytics.js`
   and `index.html`'s wizard JS.
2. Specify the minimal event set needed to see the funnel: `wizard_step_view`
   (with step number), `wizard_step_complete`, `wizard_abandon` (with last
   step reached), `cta_click` (with which CTA and which page), `form_submit`,
   `form_error`. Reuse the existing `track()` helper and its param allowlist
   (visitor-analytics.js:105-106) rather than inventing a new pipe.
3. Note that `analytics-dashboard.html`/`.js` already exists as a place these
   events could surface — check whether it already expects funnel-shaped
   data or would need a new panel.
4. Deliverable: a short instrumentation spec (event names, params, where each
   `track()` call gets added) that a developer could implement in under an
   hour, landing before any test below ships.

## Part 3 — Qualification Speed ("is this for me?")

The single hardest-to-recover visitor is one who reads for 20 seconds before
realizing they're under the $5M minimum or the wrong sponsor type. Audit:
1. Where does deal-size qualification ($5M+) first appear on each entry path
   (hero, service pages, FAQ)? Cite line numbers.
2. Time/scroll-distance to that information from page load.
3. Propose where a qualification signal could appear **before** the CTA is
   clicked, so unqualified visitors self-select out earlier (saving them
   time, and saving the funnel a doomed wizard start) — e.g., in the hero
   meta bar, in a CTA subhead, or as wizard-step-1 framing.

## Part 4 — CTA & Micro-copy Audit

1. List every CTA sitewide with its exact label, destination, and page(s) it
   appears on (nav, hero primary, hero ghost, sidebar, footer, per-service
   page). Flag any that don't point at the wizard at all.
2. For the two hero CTAs specifically: recommend keep-both vs. collapse-to-one,
   with the tradeoff stated (a secondary "see proof first" path can help
   skeptical visitors, but two equal-weight buttons split intent — say which
   effect likely dominates here and why).
3. Rewrite "Assignments evaluated for fit" (index.html:2017) and any other
   hedge phrasing still live in CTA-adjacent copy — this is copy that sits
   right next to the decision to click, so it carries more weight than hedges
   buried in body paragraphs.
4. Propose 3 button-label variants for the primary CTA optimized for
   perceived speed/ease (current: "Request a Confidential Deal Review") —
   e.g. testing whether naming the effort ("2-minute deal review") or the
   outcome ("Talk to Ben this week") converts faster — and say how you'd
   decide between them (Part 2's instrumentation, or a simple time-boxed
   A/B).
5. Audit anxiety-reducing micro-copy near the CTA and submit button (privacy
   line, confidentiality, "no obligation," response-time promise) for whether
   it's visible at the moment of decision or only after scrolling into the
   form.

## Part 5 — Wizard Friction, Field by Field

Using the ground truth above, go screen by screen:
- **Step 1 (capital-need card):** Does forcing a category pick before showing
  any fields help (progressive disclosure, low-effort first step) or hurt
  (an extra screen before the visitor can even see what's being asked)?
  Argue both sides briefly, then recommend.
- **Step 2 (asset type + deal size, both required selects):** Could either be
  deferred to the message field or made optional without hurting lead
  quality? Note that deal size is probably the single most important
  qualification signal LTG has — don't recommend cutting it without saying
  what replaces that signal.
- **Step 3 (name, company, email required; phone, message optional):** Is
  "Company" a hard blocker for a sponsor who hasn't formed an entity yet or
  is inquiring pre-mandate? Recommend which fields survive a "minimum viable
  submit," which move to a post-submit follow-up ask instead of blocking
  submission, and which stay required.
- **Cross-step:** Confirm whether progress (`wizard-progress-fill`,
  index.html:2388-2393) and back navigation reduce or increase perceived
  effort at this length, and whether autosave/carry-forward on back
  navigation actually works (test it, don't assume).
- Propose 2-3 concrete field configurations to test (e.g., current 3-screen/6-field
  vs. a 1-screen/4-field version vs. a 2-screen version that merges steps 1-2),
  each with the fields it drops and what LTG loses by dropping them.

## Part 6 — Response Speed & Same-Session Conversion

1. Evaluate the "within one business day" promise as a conversion lever: does
   restating it help (reassurance) or hurt (a warm visitor wanted an answer
   now)?
2. Propose whether adding a same-session path — embedded scheduling (e.g., a
   Calendly-style widget) as an alternative to "submit and wait" — would
   convert warmer visitors faster, and where it should sit relative to the
   existing wizard (replacement, parallel option, or post-submit
   confirmation-page upsell to "grab 15 minutes now instead of waiting").
3. Check whether `mandate-submit` triggers any confirmation email to the
   visitor (not just an internal notification) — a visitor who sees a
   generic browser success state with no email receipt may not trust the
   submission went through, and may bounce to the phone/email fallback out
   of doubt rather than genuine preference.

## Part 7 — Cross-Page Funnel Consistency

For each service subpage, confirm:
1. Its CTA(s) exist, are visible without excessive scrolling, and point at
   `#contact`.
2. Whether landing on that page and clicking through carries any context into
   the wizard (e.g., a bridge-financing visitor's Step 1 should arguably
   default to "Debt" rather than ask them to re-declare it) — if not
   currently possible, note it as a backlog item, not a same-day fix.
3. Whether copy tone/offer on that subpage matches what a visitor clicked
   through from (message match) — flag any subpage whose CTA promise doesn't
   match its own body copy.

## Part 8 — Mobile Funnel Speed

On a 375px viewport, check:
1. Tap target size and spacing on the wizard cards and nav CTA.
2. Whether `<select>` dropdowns (asset type, deal size) trigger the native
   mobile picker cleanly, and whether `inputmode`/`autocomplete` attributes
   (already present on name/company/email/phone, index.html:2469-2481) are
   actually speeding up mobile entry or if any field is missing one.
3. Whether the multi-step wizard's back/forward transitions cause layout
   shift or scroll-position jumps that would frustrate a mobile visitor mid-flow.

## Part 9 — Test Roadmap (the actual deliverable)

Produce a stack-ranked backlog. For every item, use this exact shape:

| # | Change | Hypothesis | Lever (speed / rate / quality) | Metric to watch | Effort | Sequence dependency |
|---|---|---|---|---|---|---|

Sequence dependency matters: instrumentation (Part 2) must ship before any
test that needs to be *measured* rather than eyeballed. Group the backlog
into:
1. **Ship now, no test needed** (clear, low-risk copy/micro-copy fixes — e.g.
   removing "evaluated for fit").
2. **Ship behind instrumentation** (field/step changes to the wizard — need
   before/after drop-off data to know if they worked).
3. **Needs a real A/B/n test** (button copy, CTA count, same-session
   scheduling) — state minimum sample size or time window given LTG's
   realistic traffic volume, and what "inconclusive" should mean (don't
   pretend a boutique advisory site gets SaaS-scale traffic).

## Part 10 — Report Structure Expected

1. Executive summary (3-5 sentences: current time-to-submit estimate, biggest
   single leak, first fix).
2. Funnel map (Part 1) with a leak called out at each step.
3. Instrumentation spec (Part 2).
4. Findings for Parts 3-8, each with line citations.
5. The ranked test backlog (Part 9) as the primary deliverable.
6. Explicit list of anything this audit recommends that would conflict with
   COPY_DESIGN_AUDIT_REPORT.md's recommendations, so the two can be
   reconciled before either is implemented.

## Constraints

- Every claim needs a file and line citation, same standard as the prior audit.
- Don't propose changes that require abandoning the wizard's qualification
  data collection wholesale — LTG uses deal size/asset type to route and
  prioritize inbound leads; any friction-reduction recommendation must say
  what replaces that signal if it removes a field that currently captures it.
- Assume real traffic here is modest (boutique advisory firm, not consumer
  SaaS) — recommend qualitative fixes and directional A/B reads over
  statistically-rigorous testing that would need volume this site doesn't have.
