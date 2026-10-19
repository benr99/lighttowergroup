# Light Tower Group — Marketing Funnel & Sign-Up Velocity Audit

*Executed against [FUNNEL_CONVERSION_AUDIT_PROMPT.md](FUNNEL_CONVERSION_AUDIT_PROMPT.md). This is code-grounded: every claim below was verified by reading the actual source, not inferred from a live browser session. Where something would need a browser or production data to confirm, it's flagged as such rather than asserted.*

---

## 1. Executive Summary

LTG doesn't have one funnel — it has **three, unequal ones**, and the least commercially valuable one is the only one built well:

1. **Homepage wizard** (`index.html` `#contact`) — the CTA in the nav, the hero, and every internal anchor link. High intent. **Zero analytics visibility and zero lead-record persistence.** It fires tracking events that the backend silently discards, and its own submit handler never stores a lead — it only emails Ben.
2. **Service-page chat widget** (`bridge-financing.html`, `senior-debt.html`, and 7 other product pages) — the CTA a visitor sees if they search "bridge financing" and land directly on that page. **Highest-intent traffic, weakest lead capture**: it depends on a regex guessing whether the visitor happened to type an email and a deal signal into a free-text chat, with no explicit "leave your info" step.
3. **Capital Diagnostic** (`capital-diagnostic.js`, embedded in article/insights pages) — the CTA a visitor sees at the bottom of a blog post. Lowest intent of the three. **This is the only one that's fully instrumented**: tracked funnel (impressions → starts → completes → contact submit), persisted to a lead store, scored, and rendered in `analytics-dashboard.html`.

The practical effect: Ben can currently answer "how many people started the capital diagnostic after reading an article this month?" with a number. He cannot answer "how many people started the deal-review wizard from the homepage this month, and where did they drop off?" at all — that data doesn't exist anywhere, not even in aggregate. The fix isn't a redesign; it's wiring the two high-intent paths into the measurement system the low-intent path already has.

**First fix, in order:** (1) add the four wizard event names and two chat event names to the backend's event allowlist so tracking calls stop being silently dropped — 10-line change, see Part 2; (2) make `mandate-submit.js` persist a lead record the same way `capital-diagnostic` leads are persisted, so homepage submissions show up on the lead board — currently they exist only as an email; (3) decide whether service-page visitors should default into the chat widget at all, given it's the weakest-instrumented, most ambiguous capture mechanism for what should be the most qualified traffic on the site.

---

## 2. Funnel Map

### Path A — Homepage wizard (nav CTA, hero CTAs, `/#contact` anchors sitewide)

```
Land on index.html (or any page's #contact anchor)
  → click "Request a Deal Review" / "Request a Confidential Deal Review"
  → Step 1: pick Debt / Equity / Advisory card (auto-advances)          [index.html:2396-2415]
  → Step 2: 2 required <select> dropdowns (Asset Type, Deal Size)      [index.html:2418-2456]
  → Step 3: Name*, Company*, Email*, Phone, Message                    [index.html:2459-2496]
  → POST /.netlify/functions/mandate-submit
  → success screen: "Benjamin will follow up... within one business day" [index.html:2499-2503]
  → Ben gets ONE email via Resend. No lead record. No visitor-facing confirmation email. [mandate-submit.js:73-100]
```
**Instrumented?** Client fires `mandate_form_start`, `mandate_form_step_1`, `mandate_form_step_2`, `mandate_form_submit` via `window.ltgTrack` (index.html:2617-2618, 2642-2646, 2676-2680). **Server drops all four** — see Part 2.

### Path B — Service-page chat widget (`bridge-financing.html` and 8 sibling pages)

```
Land on bridge-financing.html (e.g. from search for "bridge financing NYC")
  → nav CTA "Discuss Your Deal" / hero CTA — both call openLTGChat()       [bridge-financing.html:104,122,158]
  → chat panel opens, bot asks "what are you working on?"                 [chat-widget.js:256]
  → visitor free-types up to 20 turns, 1000 chars each                     [chat-widget.js:5-7,308-315]
  → shouldNotifyLead() regex-scans the transcript for an email PLUS
    (a deal keyword OR a $-size pattern OR the bot saying a closing phrase) [chat-widget.js:265-274]
  → only if that regex matches: POST /.netlify/functions/deal-notify        [chat-widget.js:277-293]
```
**No structured field capture at all.** There's no explicit moment where the widget says "leave your name and email" — it's entirely dependent on the LLM assistant thinking to ask, and the visitor volunteering it in free text, in a way the regex happens to catch. A visitor who says "I need $30M in bridge debt for a Miami hotel refi, my email is X" triggers it. A visitor who describes the same deal but the bot doesn't get to asking for contact info before the 20-turn cap, or the visitor gives a phone number instead of email, produces **no notification at all** — not even a partial one.

**Instrumented?** `chat_open` fires and *is* in the backend allowlist. `chat_message_sent` and `chat_lead_captured` (chat-widget.js:280,323) are **not** in the allowlist — dropped. There is no page-level CTA click event distinguishing "Discuss Your Deal" (nav) from "Discuss Your Deal" (hero) beyond the `source` param, which is itself discarded since the whole event is rejected.

### Path C — Capital Diagnostic (embedded in insights/article pages via `capital-diagnostic.js`)

```
Reader finishes an article
  → diagnostic widget replaces the old CTA block                          [capital-diagnostic.js:524-532]
  → diagnostic_impression → diagnostic_start → per-question diagnostic_step
    (step_id, step_number) → diagnostic_complete (outcome, lead_route)    [capital-diagnostic.js:635,713]
  → diagnostic_contact_submit → lead written to `ltg-capital-diagnostic-leads` blob store
  → surfaces in analytics-dashboard.html funnel widget and lead board
```
**Fully instrumented, fully persisted, fully visible.** This is the reference implementation — it's the pattern Paths A and B should be matching, not a separate thing to leave alone.

---

## 3. Instrumentation Gap — Confirmed, and More Specific Than Assumed

The original prompt assumed the wizard had *no* tracking. That's wrong — it has tracking calls; they're just discarded server-side. That's a more precise (and cheaper-to-fix) problem.

`netlify/functions/_shared/analytics-core.js:3-32` defines `EVENT_NAMES`, a hard allowlist. `visitor-track.js:104-112` calls `normalizeEvent()`, which returns `{ error: 'Unsupported analytics event.' }` for anything not in that set, and the handler responds `400`. The client's `deliver()` in `visitor-analytics.js:144-152` sends via `fetch(...).catch(() => {})` — **it never inspects the response status**, so a rejected event fails completely silently. Nothing logs, nothing retries, nothing tells you it happened.

Events currently sent by the site but **missing from `EVENT_NAMES`** (i.e., silently dropped every time):

| Event | Fired from | Would tell you |
|---|---|---|
| `mandate_form_start` | index.html:2617 | Wizard opened / step 1 selected |
| `mandate_form_step_1` | index.html:2618 | Which capital type was picked |
| `mandate_form_step_2` | index.html:2642 | Reached step 2, asset/size chosen |
| `mandate_form_submit` | index.html:2676 | Completed the whole wizard |
| `chat_message_sent` | chat-widget.js:323 | Chat engagement depth (turn count) |
| `chat_lead_captured` | chat-widget.js:280 | Regex detected a qualified lead in-transcript |

**Fix:** add these six strings to `EVENT_NAMES` in `analytics-core.js:3-32`. That alone makes the wizard funnel and the chat funnel start appearing in the events store — no frontend changes needed, since the tracking calls already exist and are already correctly named. This is close to a one-line-per-event fix and should ship before anything else in this report, because every other recommendation here is a hypothesis you currently have no way to check.

**Second, larger gap:** even once those events are accepted, `analytics-core.js:438-446`'s `funnel` array is hardcoded to the diagnostic funnel's steps (`sessions → engaged → impressions → starts → completes → submits → leads`, all reading `diagnostic_*` counters). Accepting the wizard events doesn't automatically add a wizard funnel row — that array needs a second block (or a page-scoped variant) for `mandate_form_start/step_1/step_2/submit`, or the events will be recorded but still invisible on the dashboard.

**Third gap — no lead persistence for Path A at all:** `mandate-submit.js` never writes to `ltg-capital-diagnostic-leads` or any other store (compare to `capital-diagnostic.js`'s handler, which does). It only sends one email via Resend (mandate-submit.js:91-100), to `notifyEmail` (default `ben@lighttowergroup.co`), with no persisted copy. If that email is missed, filtered to spam, or the inbox changes, the lead has no other record anywhere in the system — not even a raw JSON blob. `report.kpis.leads` and `visitor_to_lead_rate` (analytics-core.js:434,436) are therefore undercounting real leads by excluding every homepage wizard submission.

**Fourth gap — no referrer on the one channel that supports it:** `mandate-submit.js:63` reads `fields.ref || fields.page` to record "Referring Page" in the notification email — but the wizard's `<form>` (index.html:2461-2496) never populates a `ref`/`page` field. Every email Ben receives says "Referring Page: not specified" regardless of whether the lead started from the hero, a `/#contact` anchor on a service page, or `/transactions.html`. This is a two-line fix (one hidden input, one line of JS setting it to `location.href` before submit) that would retroactively make Part 2's per-page attribution answerable even before the dashboard funnel work lands.

---

## 4. CTA Inventory & Copy

| CTA text | Location | Destination | Path |
|---|---|---|---|
| "Request a Deal Review" | Nav, desktop + mobile (index.html:1964, 1976) | `/#contact` | A |
| "Request a Confidential Deal Review" | Hero primary button (index.html:2003) | `/#contact` | A |
| "View Representative Transactions" | Hero ghost button (index.html:2004) | `/#transactions` | (deflects from A) |
| "Discuss Your Deal" | Nav + hero, service pages (bridge-financing.html:104,122,158, and 8 sibling pages) | `openLTGChat()` | B |
| Email / phone links | Form intro (index.html:2375) | `mailto:` / `tel:` | bypasses both |

The hedge phrase flagged in the prior Krinsky audit is **still live**: "Assignments evaluated for fit" (index.html:2017), sitting inside the hero sidebar next to the primary CTA. Since this audit is specifically about the moment of click-decision, this is worth re-flagging here even though it's not new: copy immediately adjacent to a CTA carries more conversion weight than the same phrase buried in body text, so this specific hedge should be first in line among the copy fixes, not just one of many.

More consequential than any single phrase: **the two highest-intent entry points on the site (hero, service pages) use two different, unequally-instrumented mechanisms**, and a visitor has no way to know that clicking "Request a Deal Review" gets them a structured, trackable form while clicking "Discuss Your Deal" on a service page gets them an unstructured chat with weaker lead capture. That's an operational inconsistency, not just a copy one.

---

## 5. Wizard Friction, Screen by Screen

- **Step 1 (capital-need card, auto-advance):** Low friction — one tap, no typing, advances itself after 220ms (index.html:2619 equivalent in the wizard JS). This screen is not the problem.
- **Step 2 (2 required selects — Asset Type: 12 options, Deal Size: 5 ranges):** Both block progress (`wizardNext`, JS lines 2622-2649 — inline error text if either is empty). Deal Size is almost certainly LTG's single most useful qualification signal (it's the number that determines whether this is a $5M deal or a $250M one) — don't cut it. Asset Type is used for routing/context but is more deferrable; consider whether it could move into the free-text message field for a "fast path" variant without losing the signal entirely (a sponsor describing "Miami hotel refi" already states asset type in prose).
- **Step 3 (Name*, Company*, Email*, Phone, Message):** Company is required. That's a plausible blocker for a first-time sponsor or someone inquiring pre-entity-formation who would otherwise convert. Recommend testing Company as optional, captured instead in the follow-up call rather than gating submission.
- **Progress + back nav:** `wizard-progress-fill` and step counter exist and update correctly (index.html:2388-2393, JS lines 2584-2606); hidden fields carry step 1-2 answers into step 3's form (index.html:2463-2465, JS lines 2639-2641) — carry-forward does work, confirmed by reading the assignment logic, not just assumed.
- **Total to submit:** 1 tap (step 1) + 2 required decisions (step 2) + 3 required fields (step 3) = 6 required inputs across 3 screens before the submit button. That count matches the prior Krinsky audit's finding; nothing has changed here since that report.

**Test to run once instrumentation lands (Part 3, above):** compare current 3-screen/6-field flow against a variant with Company made optional and Asset Type folded into the message field. Don't test blind — the point of fixing Part 2 first is exactly to make this comparison possible instead of guessed.

---

## 6. Response Speed & Same-Session Conversion

- The "within one business day" promise appears three times: form intro (index.html:2374), success screen (index.html:2501-2502), and the homepage FAQ. Repeating a wait-time promise doesn't speed anything up — it just restates the wait. For a warm, ready-to-act sponsor this is pure friction with no offsetting reassurance value beyond the first mention.
- **No visitor-facing confirmation email exists.** `mandate-submit.js`'s Resend call sends one email, to `notifyEmail` (Ben), with `reply_to: [lead.email]` (mandate-submit.js:92-95) — that reply-to means Ben *can* reply directly to the lead, but the lead themselves receives nothing confirming their submission went through. A visitor who isn't 100% sure the AJAX submit succeeded (index.html:2658-2691 shows the success state only swaps DOM visibility client-side — no email lands in their own inbox as independent confirmation) has no artifact to point to if they follow up by phone asking "did you get my form?"
- **No same-session scheduling exists anywhere in the funnel.** All three paths converge on "someone will follow up later" — there's no embedded calendar for a visitor who'd rather grab 15 minutes right now than wait a day for an email.

---

## 7. Cross-Page Consistency

Confirmed by reading `bridge-financing.html`, `senior-debt.html`, `agency-lending.html`, `cmbs.html`, `construction-financing.html`, `life-company-financing.html`, `preferred-equity.html`, `joint-venture-equity.html` (all 172 lines, near-identical templates) and `origination.html` (221 lines):

- **None of the 9 service pages link to the homepage wizard as their primary CTA.** All route "Discuss Your Deal" through `openLTGChat()` instead (e.g. bridge-financing.html:104, 122, 158). The `#contact` wizard is only reachable from these pages via the small text link in the footer line (bridge-financing.html:163), not as a primary action.
- This means the visitor most likely to convert well — someone who searched a specific product term and landed on the matching page — is funneled into the weakest-instrumented, least-structured capture mechanism on the site (Path B), while a homepage visitor with a vaguer intent gets the structured wizard (Path A).
- No service page passes any context (which product page the visitor came from) into the chat widget beyond the `source` tag on `openLTGChat()`, which — per Part 3 — is currently discarded server-side along with the rest of the event.

---

## 8. Mobile — Code-Level Read Only

*Not verified in a live browser this session — the following is read from CSS/media queries only, and should be spot-checked on an actual device before treating it as confirmed.*

- `.wizard-cards` collapses to 1 column under 560px (index.html CSS ~line 978); `.wizard-fields` collapses to 1 column under 600px (~line 1035) — both look correctly single-column on phone widths.
- Name/Company/Email/Phone fields carry `autocomplete`/`inputmode` attributes (index.html:2469-2481), which should engage the right mobile keyboard per field.
- The chat panel goes full-screen under 480px (chat-widget.js:139-145), which is reasonable, but a full-screen takeover triggered by a header/nav button on a product page is a heavier interaction than a mobile visitor may expect from a single tap — worth a real-device check on whether it feels appropriate.

---

## 9. Ranked Test/Fix Backlog

| # | Change | Hypothesis | Lever | Metric to watch | Effort | Sequence dependency |
|---|---|---|---|---|---|---|
| 1 | Add the 6 missing event names to `EVENT_NAMES` (analytics-core.js:3-32) | Wizard/chat funnel data starts accumulating immediately, no frontend change needed | (enables measurement) | Event counts appear in `ltg-analytics-events` store | Trivial | None — do first |
| 2 | Persist a lead record from `mandate-submit.js` (mirror `capital-diagnostic.js`'s store write) | Homepage submissions stop being invisible to the dashboard/lead board | (enables measurement) | `leads`, `visitor_to_lead_rate` KPIs include Path A | Small | None — do first |
| 3 | Add hidden `ref`/`page` field to the wizard form, populate with `location.href` pre-submit | Ben can see which page/CTA produced each lead without waiting on dashboard work | (enables measurement) | "Referring Page" field populated in notification emails | Trivial | None — do first |
| 4 | Add a `mandate_*` funnel block to `analytics-core.js`'s `funnel` array | Step-by-step wizard drop-off becomes visible on the dashboard, same as diagnostic today | (enables measurement) | New funnel rows render with real counts | Small | After #1 |
| 5 | Remove "Assignments evaluated for fit" hedge next to hero CTA (index.html:2017) | Removes a doubt-inducing phrase at the exact moment of the click decision | rate | A/B or before-after CTA click-through | Trivial | None — ship now |
| 6 | Route service-page CTAs to the structured wizard (or a pre-filled variant of it) instead of/alongside the chat widget | Highest-intent traffic gets the higher-fidelity capture mechanism instead of the weakest one | rate, quality | Path A submissions attributable to service pages (needs #3) | Medium | After #3 |
| 7 | Make "Company" optional in wizard step 3; require it only as a soft ask post-submit | Removes a plausible blocker for pre-entity sponsors without losing the lead | rate vs. quality (state both — may raise unqualified submits) | Step-3 completion rate before/after (needs #1) | Small | After #1 |
| 8 | Send a visitor-facing confirmation email on wizard submit (separate from the internal Resend notification) | Visitors trust the submission went through, reducing duplicate phone/email follow-ups out of doubt | anxiety/trust, not directly measurable as a rate | Qualitative — support/follow-up volume | Small | None |
| 9 | Add same-session scheduling (embedded calendar) as an alternative to "wait a day," on the wizard success screen and/or as a wizard alternative | Warm visitors convert to a booked call instead of an open-ended wait | speed | Bookings vs. submits-with-no-booking (needs #1/#2 for baseline) | Medium | After #1, #2 |
| 10 | A/B primary CTA label ("Request a Confidential Deal Review" vs. 2 alternatives naming effort/outcome) | Perceived effort/speed changes click-through independent of the form itself | rate | CTA click-through (needs #1's `service_cta_click` equivalent wired for hero button — confirm it's tracked) | Small | After #1 |

**Sequencing note:** items 1-4 are not optional polish — they're the precondition for every rate-based claim in items 5-10 being verifiable rather than guessed. Given LTG's realistic traffic volume (boutique advisory, not consumer SaaS), treat 5-10 as directional reads over 4-8 week windows, not statistically-powered A/B tests — there likely isn't enough monthly volume for a clean split test on any single CTA-label change. Prioritize the qualitative/no-test-needed items (5, 7, 8) alongside the instrumentation work, and reserve real before/after comparison for the ones with real design tradeoffs (6, 9, 10).

---

## 10. Conflicts With the Prior Copy/Design Audit

None outright, but one point of emphasis differs: [COPY_DESIGN_AUDIT_REPORT.md](COPY_DESIGN_AUDIT_REPORT.md) recommends consolidating to "exactly 2 CTAs sitewide" as a brand-clarity move. This audit agrees on the hero (collapse "View Representative Transactions" as a competing button) but flags that the *bigger* problem isn't CTA count — it's that the two intent-matched CTAs that already exist (wizard vs. chat) point at two different, unequally-built systems. Fixing CTA count without fixing which system each CTA leads to would still leave service-page traffic in the weaker path. Recommend sequencing this report's items 1-4 and 6 alongside, not after, any hero copy consolidation work.
