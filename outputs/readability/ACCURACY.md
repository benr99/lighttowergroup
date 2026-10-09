# Accuracy: what was wrong, what changed, what is still not guaranteed

Written 2026-10-08. Supersedes the "soft warning" design in `REPORT.md`.

## What we measured

16 cached source stories, written by the production writer (git HEAD) and by the new pipeline. Every
sentence of both outputs was then re-checked against the source text by a reasoning-mode model using strict
rules (any added claim, exaggeration, dropped qualifier, changed attribution or merged claim fails).
Reproduce: `python outputs/readability/accuracy_audit.py`.

| | Current production writer | New fact-gated pipeline |
|---|---|---|
| Articles | 16 | 16 (all published; 0 withheld, 0 failed in the final run) |
| Factual sentences audited | 314 | 143 |
| Flagged unsupported | 74 (23.6%) | 1 (0.7%), a false positive (see below) |
| Articles with at least one flagged sentence | 14 of 16 | 0 of 16 genuine |
| Sentences the gate removed before publication | n/a | 37 |

**The current production writer states unsupported things in 14 of 16 articles.** Most are interpretation
presented as fact ("the deal signals institutional conviction"), but the set also includes:
- an opinion attributed to nobody turned into plain fact;
- a statement attributed to the wrong party or described as a direct quote when it was paraphrased;
- a figure given "according to the firm" when the source did not say so;
- internal process language published to readers ("the dossier contains one source", "evidence level").

**The one flag on the new pipeline** is a sentence holding two consecutive passages that both appear verbatim
in the source (a quotation ending in `."` followed by the next sentence). The audit's sentence splitter merged them, so the
auditor judged the pair as one claim. I checked it against the source by hand: both parts are there.

I also read the Cook (Fed) and Texas (ERCOT) articles against their sources. Everything was faithful, with one
loose paraphrase: "BNEF suggests the audit is politically tilted" for a quoted passage that says the pause is
"likely intended to take the controversial data center issue off the table." That kind of characterisation is
the residual risk below.

## How the new pipeline works

1. The writer returns structured sentences. Each carries one or two quotes copied from the source.
2. **Code** checks that every quote exists in the source, and that every number, spelled-out number, name and
   quoted phrase in the sentence is in that sentence's own quote. It rejects a sentence that drops a qualifier
   its quote carries ("most", "about", "plans to", "expects", "could") or the attribution ("said", "according to").
3. **Two model passes** (a yes/no ruling, then a claim-by-claim decomposition) must both say "supported".
   If the checker is unavailable, nothing publishes.
4. The page is assembled from the surviving sentences only. If too few survive, the story is **withheld**,
   which does not block the rest of the day's edition.
5. **No opinions, predictions, "what to watch" lines or closing advice are published.** Every sentence is a
   quoted fact. In the first audit these were where unsupported claims hid, and the checker could not tell.
6. An evidence file per article (`.editorial-state/v4-evidence/`) lists every sentence with its quotes
   and every rejection with its reason.

## What this does NOT guarantee

- **The checker is the same model family as the writer.** OpenAI is configured as the preferred independent
  checker, but its account reports no credits (`insufficient_quota`), so DeepSeek in reasoning mode does both.
  The deterministic quote checks do not depend on any model, but the entailment passes can share blind
  spots. Adding OpenAI credit makes the second pass a different model automatically.
- **Paraphrase fidelity** (for example "politically tilted" above) is judged by models, not code.
- **A wrong source is a wrong article.** The pipeline proves faithfulness to the source, not truth.
- **Titles are checked for numbers and by the models, but not for names** (headlines capitalise every word).
- **Cost and time:** each article now takes about 1-4 minutes and 4-6 model calls. The edition window is
  extended to 45 minutes; the full run was not timed at 70 articles.

## Recommended before turning it on for real

1. Add OpenAI credit (or any second provider) so the second pass is a different model.
2. Run the daily workflow with `mode=preview` and read ten evidence files. For each article, open the
   source and spot-check five sentences.
3. Treat the first week as supervised: dispatch manually in preview mode, read the output, then publish.

## The Friday wrap

Same gate: every summary and "why it matters" line is checked against the item it came from, twice, and
anything rejected falls back to the plain excerpt. On the week of Sep 26 to Oct 2: 45 items featured, 21 had
their model-written lines rejected (real errors such as a pound figure written as dollars, "1.2M SF" for
1,226,825 sq ft, and "raised" for "raises"), 7 kept a "why it matters" line, and a separate re-audit of the
52 published lines found 0 unsupported.

**Chain of trust:** the wrap is checked against the daily articles it links to. Articles published before
the gate existed were written by the old writer, and 14 of 16 audited ones had unsupported sentences. The
wrap cannot be more accurate than the pages it summarises, so its fallback excerpts inherit their errors
until older pages are re-verified. New articles are verified at the source.
