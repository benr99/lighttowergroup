#!/usr/bin/env python3
"""A/B: the writer prompt at git HEAD (arm A) vs the working-tree writer (arm B).

Both arms get the same dossier (source text from .editorial-state/retrieval-cache),
the same provider, one request each, no retry. So arm B's warning rate is the raw
compliance rate (production adds one corrective retry on top).

Needs DEEPSEEK_API_KEY (or OPENAI_API_KEY) in the environment. Writes
ab_results.json and ab_samples.md beside this file.
"""
from __future__ import annotations

import json
import random
import re
import subprocess
import sys
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(HERE))

import v4_generation as new  # noqa: E402
from measure import metrics  # noqa: E402
from model_router import provider_chain, provider_config  # noqa: E402
from readability import paragraph_texts, unsupported_numbers  # noqa: E402

# (url fragment, tier) - CRE-relevant stories across sectors and all three tiers.
STORIES = [
    ("yieldpro.com/2026/08/cobblestone-village", "tier_c"),
    ("bisnow.com/news/denver/development/gold-crown-foundation", "tier_c"),
    ("altswire.com/bluerock-value-exchange-launches-58-4m", "tier_c"),
    ("bisnow.com/news/washington-dc/office/prp-buys-downtown-office", "tier_c"),
    ("multihousingnews.com/ejs-group-jv-secures-138m-refi", "tier_c"),
    ("commercialobserver.com/2026/08/starwoods-net-income-drops", "tier_b"),
    ("multihousingnews.com/jpmorganchase-commits-750b", "tier_b"),
    ("commercialobserver.com/2026/08/tpg-ag-redfearn-capital-industrial", "tier_b"),
    ("commercialobserver.com/2026/08/brookfield-asset-management-q2-2026", "tier_b"),
    ("americanbanker.com/news/feds-cook-ready-to-hike-rates", "tier_b"),
    ("nationalmortgagenews.com/news/who-loses-when-upstart", "tier_a"),
    ("powermag.com/texas-audit-could-delay-49-8-gw", "tier_a"),
]

LEGACY_SYSTEM = "You are a precise financial journalist."
JUDGE_SYSTEM = (
    "You are a veteran commercial real estate finance editor judging two drafts of the same story "
    "for readers who are sponsors, lenders and investors reading on their phones. Return JSON only."
)


def load_legacy():
    src = subprocess.check_output(["git", "show", "HEAD:scripts/v4_generation.py"], cwd=ROOT).decode("utf-8")
    module = types.ModuleType("v4_legacy")
    module.__dict__["__name__"] = "v4_legacy"
    sys.modules["v4_legacy"] = module
    exec(compile(src, "v4_generation_HEAD.py", "exec"), module.__dict__)
    return module


def load_dossiers() -> list[dict]:
    cache = {}
    for path in (ROOT / ".editorial-state" / "retrieval-cache").glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        cache[str(data.get("canonical_url") or data.get("url"))] = data
    out = []
    for fragment, tier in STORIES:
        match = next((d for u, d in cache.items() if fragment in u), None)
        if not match or len(match.get("text", "")) < 1200:
            print(f"  skip (not cached): {fragment}")
            continue
        url = str(match.get("canonical_url") or match["url"])
        slug = url.rstrip("/").rsplit("/", 1)[-1].replace(".html", "")
        title = re.sub(r"[-_]+", " ", slug).strip().title()
        text = match["text"][:5000]
        domain = re.sub(r"^www\.", "", re.sub(r"https?://", "", url).split("/")[0])
        dossier = {
            "event_id": slug, "title": title, "what_happened": text[:300], "sector": "commercial_real_estate",
            "event_type": "", "evidence_level": "single_source_full_text",
            "evidence_level_note": "One source read in full; analysis must stay close to it.",
            "material_claims": [], "missing_information": [], "facts": [],
            "sources": [{"name": domain, "source": domain, "url": url, "text": text, "summary": text[:300]}],
        }
        out.append({"slug": slug, "title": title, "tier": tier, "dossier": dossier})
    return out


def chat(provider: dict, system: str, user: str, temperature: float, max_tokens: int = 3600) -> str:
    payload = {"model": provider["model"], "temperature": temperature, "max_tokens": max_tokens,
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if provider["provider"] == "deepseek":
        payload["thinking"] = {"type": "disabled"}
    r = requests.post(provider["url"], headers={"Authorization": f"Bearer {provider['api_key']}",
                                                "Content-Type": "application/json"}, json=payload, timeout=180)
    r.raise_for_status()
    return str(r.json()["choices"][0]["message"]["content"]).strip()


def parse(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    return json.loads(text)


def run_arm(provider, legacy, story, arm) -> dict:
    obj = SimpleNamespace(title=story["title"])
    dossier = story["dossier"]
    if arm == "A":
        spec = legacy.DEPTH_SPEC[story["tier"]]
        prompt, system, temp = legacy._writer_prompt(obj, dossier, spec), LEGACY_SYSTEM, 0.2
    else:
        spec = new.DEPTH_SPEC[story["tier"]]
        prompt, system, temp = new._writer_prompt(obj, dossier, spec), new.WRITER_SYSTEM, new.WRITER_TEMPERATURE
    try:
        article = parse(chat(provider, system, prompt, temp))
    except Exception as exc:  # noqa: BLE001
        return {"arm": arm, "error": f"{type(exc).__name__}: {exc}"[:200]}
    paras = paragraph_texts(article.get("body_html", ""))
    m = metrics(paras, article.get("title", ""), article.get("excerpt", ""))
    invented = unsupported_numbers(" ".join([article.get("title", ""), article.get("excerpt", "")] + paras),
                                   json.dumps(dossier, ensure_ascii=False))
    result = {"arm": arm, "article": article, "metrics": m, "invented_numbers": invented}
    if arm == "B":
        v = new.validate_article(article, dossier, spec)
        result.update(hard_valid=v.valid, hard_codes=v.codes, warnings=v.warnings)
    return result


def judge(provider, story, a, b, rng) -> dict:
    order = ["A", "B"]
    rng.shuffle(order)
    arms = {"A": a, "B": b}
    def show(label):
        art = arms[label]["article"]
        body = "\n\n".join(paragraph_texts(art.get("body_html", "")))
        return f"TITLE: {art.get('title')}\nEXCERPT: {art.get('excerpt')}\n\n{body}"
    first, second = order
    prompt = f"""Two drafts of one story. Source facts are in the dossier below; neither draft may add facts beyond it.

DOSSIER TEXT:
{story['dossier']['sources'][0]['text'][:3500]}

=== DRAFT ONE ===
{show(first)}

=== DRAFT TWO ===
{show(second)}

Score each draft 1-5 on: hook (does the first screen make you read on), plain_language (an expert could read it fast without re-reading), skimmability (short paragraphs, clear shape), usefulness (does it say why it matters and what to do), trust (stays within the facts, no hype or filler).
Also say which draft you would rather read and forward ("one" or "two").
Return exactly: {{"one": {{"hook":0,"plain_language":0,"skimmability":0,"usefulness":0,"trust":0}}, "two": {{"hook":0,"plain_language":0,"skimmability":0,"usefulness":0,"trust":0}}, "prefer": "one", "reason": "one sentence"}}"""
    try:
        data = parse(chat(provider, JUDGE_SYSTEM, prompt, 0.0, 800))
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"[:200]}
    mapped = {first: data.get("one"), second: data.get("two")}
    preferred = first if str(data.get("prefer")).lower().startswith("one") else second
    return {"scores": mapped, "prefer": preferred, "reason": data.get("reason", "")}


def main() -> None:
    chain = provider_chain(provider_config("deepseek", for_writing=True), for_writing=True)
    if not chain:
        sys.exit("No provider key in the environment; cannot run the A/B.")
    provider = chain[0]
    legacy = load_legacy()
    stories = load_dossiers()
    print(f"{len(stories)} stories, provider {provider['provider']}/{provider['model']}")
    rng = random.Random(11)

    def retry_b(story, b):
        """Mimic production: one corrective rewrite when the first draft has warnings."""
        if not b.get("warnings"):
            return None
        spec = new.DEPTH_SPEC[story["tier"]]
        prompt = new._writer_prompt(SimpleNamespace(title=story["title"]), story["dossier"], spec)
        feedback = "\n".join(f"- {w}" for w in b["warnings"])
        prompt += ("\n\nYour previous response is valid but needs to be easier to read. Rewrite the whole article, "
                   "fixing every point below and keeping every fact accurate. Return a complete replacement JSON "
                   "object. Do not explain the correction.\n" + feedback)
        try:
            article = parse(chat(provider, new.WRITER_SYSTEM, prompt, new.WRITER_TEMPERATURE))
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)[:160]}
        v = new.validate_article(article, story["dossier"], spec)
        paras = paragraph_texts(article.get("body_html", ""))
        return {"article": article, "hard_valid": v.valid, "hard_codes": v.codes, "warnings": v.warnings,
                "metrics": metrics(paras, article.get("title", ""), article.get("excerpt", ""))}

    def one(story):
        a = run_arm(provider, legacy, story, "A")
        b = run_arm(provider, legacy, story, "B")
        if "article" in b:
            b["retry"] = retry_b(story, b)
        j = judge(provider, story, a, b, rng) if "article" in a and "article" in b else {"error": "missing arm"}
        return {"slug": story["slug"], "tier": story["tier"], "A": a, "B": b, "judge": j}

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(one, stories))
    (HERE / "ab_results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")

    ok = [r for r in results if "metrics" in r["A"] and "metrics" in r["B"]]
    def mean(arm, key):
        return round(sum(r[arm]["metrics"][key] for r in ok) / max(1, len(ok)), 1)
    print(f"\nscored pairs: {len(ok)} of {len(results)}")
    for key in ["words", "words_per_para_mean", "words_per_sentence_mean", "pct_sentences_over_30",
                "flesch_reading_ease", "fk_grade", "the_starter_pct", "hook_first_sentence_words"]:
        print(f"  {key:28s} A={mean('A', key):>6}  B={mean('B', key):>6}")
    for key in ("template_closer", "excerpt_truncated"):
        a = sum(r["A"]["metrics"][key] for r in ok); b = sum(r["B"]["metrics"][key] for r in ok)
        print(f"  {key:28s} A={a}/{len(ok)}  B={b}/{len(ok)}")
    print(f"  invented numbers (articles)  A={sum(bool(r['A']['invented_numbers']) for r in ok)}  B={sum(bool(r['B']['invented_numbers']) for r in ok)}")
    print(f"  B hard-valid                 {sum(r['B'].get('hard_valid', False) for r in ok)}/{len(ok)}")
    print(f"  B with readability warnings  {sum(bool(r['B'].get('warnings')) for r in ok)}/{len(ok)} (these would get one corrective retry)")
    retried = [r for r in ok if r["B"].get("retry")]
    if retried:
        fixed = sum(1 for r in retried if "warnings" in r["B"]["retry"] and not r["B"]["retry"]["warnings"])
        still = [r for r in retried if r["B"]["retry"].get("warnings")]
        hard = sum(1 for r in retried if r["B"]["retry"].get("hard_valid") is False)
        print(f"  after 1 corrective retry     {fixed}/{len(retried)} fully clean; {len(still)} still carry warnings; {hard} hard-invalid")
        for r in still:
            print("     -", r["slug"][:30], [w[:70] for w in r["B"]["retry"]["warnings"]])
    judged = [r for r in ok if "scores" in r["judge"]]
    if judged:
        wins = sum(r["judge"]["prefer"] == "B" for r in judged)
        print(f"  judge prefers B              {wins}/{len(judged)}")
        for dim in ["hook", "plain_language", "skimmability", "usefulness", "trust"]:
            a = sum(r["judge"]["scores"]["A"][dim] for r in judged) / len(judged)
            b = sum(r["judge"]["scores"]["B"][dim] for r in judged) / len(judged)
            print(f"    judge {dim:15s} A={a:.2f}  B={b:.2f}")

    lines = ["# A/B samples (A = current prompt at HEAD, B = new writer)\n"]
    for r in ok[:12]:
        if r["tier"] == "tier_a" and len(lines) > 7:
            pass
        lines.append(f"\n## {r['slug']} ({r['tier']})\n")
        for arm in ("A", "B"):
            art = r[arm]["article"]
            lines.append(f"### Arm {arm}: {art.get('title')}\n*{art.get('excerpt')}*\n")
            lines.extend(paragraph_texts(art.get("body_html", "")))
            lines.append("")
    (HERE / "ab_samples.md").write_text("\n\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
