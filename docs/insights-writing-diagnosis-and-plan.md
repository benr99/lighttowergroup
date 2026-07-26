# Why the Insights Articles Feel Repetitive — Diagnosis and Improvement Plan

Prepared by reviewing the actual generation code (`enhanced_prompts.py`, `editorial_voice.py`, `bucketed_editorial.py`, `editorial_scoring.py`, `daily_news_agent.py`) and the real published output (141 live article titles pulled from `insights.json`, plus full article bodies).

## The short version

Your instinct is right, and it's fixable without rebuilding anything. The underlying writing instructions are actually well thought out — there's a genuine "no generic CRE language" system already in place. The sameness comes from four specific, identifiable things, not a lack of effort in the prompt. Two are headline-level, one is prose-level, one is volume-level. All four are things I can go fix directly in the prompt files once you've reviewed this and tell me to proceed.

## The evidence

I pulled every title currently on the site (141 articles) and ran the numbers:

| Pattern | Count | Share |
|---|---|---|
| Title contains the word "Shows" | 78 | 55% |
| Title contains "Shows" or "Tests" | 92 | 65% |
| Title starts with `[Company]'s $[Amount]...` | 70 | 50% |
| Title ends in a ", Not X" / ", But X" contrast tail | 47 | 33% |
| The exact phrase "picking its/the spots" | 9 | — |
| The exact template "A Bet on X, Not Y" | 4 | — |

And a genuine problem beyond phrasing: at least five pairs of articles cover the *same underlying transaction* published days apart under different headlines and slugs — the automated near-duplicate check didn't catch them because it only compares titles, not the deal itself. Examples: "Intercontinental's $69.5M Buy Shows Grocery-Anchored Retail Still Commands a Premium for Stability" (7/17) and "...Still Clears at the Right Basis" (7/20) are the same $69.5M Lakeland Town Center purchase written up twice. "Airbnb's $81.5M Office Buy: A Lobbying Investment, Not a Real Estate Bet" and "...Is a Political Bet, Not a Real Estate One" are the same story too. That's a real brand-credibility risk if a reader ever notices — it looks like the outlet doesn't know what it already published.

## Root cause 1: the prompt's own examples are training the model to repeat itself

This is the biggest lever. In `scripts/enhanced_prompts.py`, the section that tells the model how to write headlines gives exactly two worked examples:

> Weak: "SL Green Sells Midtown Office Building"
> Strong: "SL Green's $312M Sale Shows Office Liquidity Is Back Only at the Right Basis"
>
> Weak: "Walker & Dunlop Leads Fannie Mae Lending"
> Strong: "Walker & Dunlop's Fannie Mae Lead Shows Multifamily Is Refinancing, Not Buying"

Both "good" examples are `[Company]'s $[Amount] [Noun] Shows [Thesis]`. When a language model is shown a small number of examples in a prompt, it treats their *shape*, not just their spirit, as the target — even while a hundred lines of surrounding instructions say "be specific" and "avoid generic phrasing." This is exactly what happened: 50% of real headlines match that literal skeleton, and 65% use "Shows" or "Tests" as the connective tissue. The fix isn't "tell it to vary more" (the prompt already does, implicitly) — it's to stop handing the model a single-shape example set. This is a five-minute fix with an outsized payoff.

The same mechanism explains the "X, Not Y" contrast tail showing up in a third of headlines and repeatedly inside article bodies (including twice in one article I read in full — "This is not philanthropy. It is a negotiated community benefit..." followed later by "The market signal is not that a $1 billion project is being planned. It is that..."). The `VOICE CALIBRATION` section of the same prompt gives four back-to-back "Bad: X. Better: not-X-but-Y." examples, and the suggested closing lines ("Use endings like...") are five more sentences in that identical shape. The device is a good tool used well *sometimes* — the prompt just never tells the model to ration it, so it becomes the default gear for every close.

## Root cause 2: nothing checks headlines the way the system already checks bodies

`editorial_voice.py` is genuinely well-built for the *body* of the article: it rotates through eight distinct narrative voice modes ("Basis autopsy," "Lender's-eye memorandum," "Time as a cost of capital," etc.), deterministically avoiding whichever mode was used most recently, and it has a regex-based "AI tells" checker that flags canned phrases like "the real story is" and "this is not a story about" before publish. That machinery simply never touches the `title` field. There's no equivalent check asking "have the last 10 headlines all used the word 'Shows'?" or "does this headline follow the same skeleton as the last 5?" It's a gap in an otherwise-careful system, not a missing capability — the pattern-detection code already exists for the body and just needs a sibling for the headline.

## Root cause 3: unlimited volume flattens everything to the same size and weight

The scheduled run uses `--selection-mode bucketed-volume --no-limit`, and `bucketed_editorial.py` explicitly says it "deliberately has no category quota or final ranking cap." Combined with a 700–1,050-word length requirement applied uniformly, this means a $7M loan on a single industrial building in Pataskala, Ohio gets the same word count, the same "make one arguable interpretive claim" instruction, and the same dramatic-close treatment as a $5.2 billion industrial take-private. Small, genuinely minor stories forced into that mold produce headlines like "A $7M Loan in Pataskala Tests Which Industrial Assets Still Attract Bank Debt" — a single small regional loan being asked to "test" something market-wide, because the template demands a market-level claim regardless of how much the story can actually support one. That template-stretching is a second, independent source of the sameness (and, honestly, of overclaiming that could undercut credibility with a sophisticated reader).

## Root cause 4: duplicate-story detection is too narrow

`_deduplicate()` and `near_duplicate_matches()` in `daily_news_agent.py` compare title strings against each other (SequenceMatcher ratio > 0.72). That catches *near-identical wording*, but not *the same deal covered twice with different wording* — which is exactly what happened with the Intercontinental and Airbnb examples above. The check needs to compare the underlying facts (entities, dollar amount, address/asset) against the full published archive, not just recent title text.

## The plan, in priority order

**1. Replace the headline examples with a rotating bank of 10+ shapes, not 2.** Instead of two examples that are both `[Company]'s $[Amount] [Noun] Shows [Thesis]`, give the model a bank spanning genuinely different shapes — a question headline, a colon/subhead headline, a "verb-first" headline, a number-led headline, a contradiction headline, a plain declarative — and instruct it to actively avoid whichever shape was used in the last 3–5 published headlines (mirroring exactly how `editorial_voice.py` already rotates the eight body voice modes). I'd build this the same way: a deterministic hash-based rotator, not a random one, so it's auditable and repeatable.

**2. Cap the "Shows"/"Tests"/contrast-tail" constructions explicitly, the same way the forbidden-phrase list already caps "game changer" and "robust demand."** Add headline-specific and closing-paragraph-specific entries to the existing `_AI_TELLS` regex list in `editorial_voice.py` so a headline that leans on "Shows," "Tests," or a ", Not X" tail more than once every few articles gets flagged the same way a canned phrase does today. The infrastructure for this already exists — it's a data addition, not new architecture.

**3. Tier story depth by story size, instead of one word count for everything.** Give small/minor stories (single loans under some threshold, single-property sales below a size cutoff) a shorter target — say 350–550 words — and reserve the full 800–1,050-word, full-interpretive-claim treatment for stories that can actually support it. This removes the pressure that's currently forcing thin stories into artificially dramatic templates, and it would also read better: readers can tell when 900 words are justified and when they're padding.

**4. Tighten duplicate detection to compare deals, not just title text.** Extend `near_duplicate_matches()` to also check overlap on extracted entities (buyer, seller, address, dollar amount) against the full historical `insights.json`, not just recent titles. This is the fix for the Intercontinental/Airbnb double-coverage problem.

**5. Consider trimming daily volume.** Not essential, but worth a real conversation: publishing everything that clears a 65/100 score with no cap is producing a lot of small, forgettable stories that dilute the strong ones. A tighter daily cap (even just returning to a ranked top-N mode some days) would let the genuinely good analysis — and there is good analysis here, the Hudson Landing piece I read in full was well-reasoned — stand out instead of getting buried in volume.

## What I'd leave alone

The body-writing instructions themselves are not the problem and don't need a rewrite. The voice-mode rotation system, the "narrative-finance ledger" requiring the model to separate reported fact from interpretation, the forbidden-phrase list, and the specific "Weak/Strong" calibration examples in the *body* (as opposed to the headline) are all doing real work — the Hudson Landing article I read end to end had genuine, specific, well-grounded analysis (brownfield tax credits, debt-yield thresholds, JV risk-sharing logic), not filler. This is a case of fixing four specific mechanisms, not starting over.

## Next step

If this diagnosis matches what you're seeing, I can implement items 1–4 directly in `scripts/enhanced_prompts.py`, `scripts/editorial_voice.py`, and `scripts/daily_news_agent.py` — writing the actual replacement headline-example bank, the new `_AI_TELLS` entries, the tiered length logic, and the stronger dedup check — the same way I'd approach any other code change here: test it in isolation, show you exact before/after examples on a few real recent stories, and only then have you commit it. Want me to go ahead and build it?
