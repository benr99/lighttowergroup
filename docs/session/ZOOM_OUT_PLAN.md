# Zooming out: what it takes to make the newsroom smooth and working

Written 2026-10-09 after Ben asked to pause going live and look at the whole picture.

## Ben's decisions (2026-10-09)
- **Do not push or go live yet.** Get the whole system smooth first.
- **DeepSeek only.** No OpenAI. Remove OpenAI from every provider chain so nothing tries it, fails and wastes a call.
- **Turn off the old "LTG Daily News Agent" Windows task.** Approved; needs Ben to run one administrator step (Windows refused the change without admin rights).

## How the writing work evolved (so nothing is lost)

| When | Who | What | What happened to it |
|---|---|---|---|
| Jul 30 | Codex | A deep writing study in `docs/mandate/editorial/` (10 documents): a critique of the articles, a voice guide, the "five convictions", eight voice modes, a 15-stage writing design, a scoring rubric | Built into the v3 writer (`editorial_pipeline.py`, 7 model calls per article). Good writing ideas, but a full day took 44+ minutes and was cancelled |
| Aug 28 | Codex | A "lean rewrite" (`docs/mandate/24`, `26`): one fast model call per article | This is what production runs today. It is fast, but it dropped the voice entirely and has no fact check |
| Aug–Sep | Codex (uncommitted, on this PC) | A rewrite of `scripts/editorial_voice.py` as "Ben Rohr's analytical voice" with convictions and signature moves | Never connected to the live writer. Preserved untouched |
| Oct 8–9 | Claude | A quote-based fact check on the fast writer; a two-step voice engine (`docs/voice/`) that reuses Codex's ideas (convictions, voice modes, first person, hooks) with a gate for opinions | On a local branch; tested on live news; not yet live |

**In one line:** Codex designed the good writing but it was too slow; the fast replacement lost the voice; we now have a way to have speed, accuracy and voice together, but it isn't assembled into one writer yet.

## What "smooth and working" needs, in order

### 1. One writer instead of three
Three generations of writing code exist today. Make the fact-checked fast writer the only one, and build the voice into it:
- Merge the best of Codex's voice work (the convictions, the voice modes, the "Ben Rohr" persona) into the single voice prompt in `docs/voice/prompts/`.
- Two model calls per story (find the story, then write it), plus the fact and voice checks. Measured at about 2 to 5 minutes per story.
- Full voice for flagships and analyses; a lighter, quicker version for short briefs so the day stays fast.
- Retire the old writers once the new one has run cleanly for a while.

### 2. Dependable on DeepSeek alone
- Remove OpenAI from the writer and the fact-checker.
- Patient retries when DeepSeek is slow or busy; if it is truly down, skip the day cleanly and say so, rather than publishing anything half-checked.
- Enforce the daily spending limit (today it is not enforced).
- One failed story must not block the rest of the day (today it does).

### 3. Better story picking
- Stop administrative notices and off-topic items from being chosen.
- Fix the two scoring measures that do not work on live data.
- Fill the thin sectors (six of seven fell short in the test).

### 4. Easy for Ben to oversee
- A one-page daily digest: every published sentence next to the source quote it came from, plus what was cut and why.
- The Friday wrap stays in preview until Ben switches it on.
- A short daily health note (stories written, held back, any problems).
- A weekly five-minute spot check of random sentences.

### 5. Clean house
- Move the page-building code out of the old 2,872-line file so publishing no longer depends on it.
- Park the legacy code; tidy the docs; turn off old local tasks.

### 6. Dress rehearsal, then go live
- Run the complete system every morning for about a week in preview mode (nothing published). Ben reads the digest.
- When it reads well and checks out, go live with one supervised day.

## What changes in the session plan
- Iteration 02 ("go live") is **on hold** until steps 1–5 are done and the rehearsal week passes.
- The backlog is reordered to follow the six steps above (see `OPERATING_PROMPT.md`).
