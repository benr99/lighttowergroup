#!/usr/bin/env python3
"""Read-only readability metrics for Light Tower Insights articles.

Usage: python measure.py <insights.json> <insights_dir> [--n 8] [--out metrics.json]
Samples published articles (per format tier and sector bucket), older articles,
and the stored LinkedIn essays, then prints per-group aggregates.
"""
from __future__ import annotations

import argparse
import html
import json
import random
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

BODY = re.compile(r'itemprop="articleBody">(.*?)</div>\s*<div class="article-tags"', re.S)
PARA = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)
# Ordinary CRE vocabulary the audience knows: not counted as unknown acronyms.
KNOWN = {"CRE", "NOI", "DSCR", "LTV", "SOFR", "CMBS", "REIT", "REITS", "NYC", "SEC", "FDIC", "FED",
         "GDP", "CPI", "LP", "GP", "AI", "US", "PE", "RMBS", "CLO", "OCC", "FOMC", "PJM", "MW", "GW"}
# Insider-of-insider terms that need a gloss on first use.
JARGON = re.compile(
    r"\b(R&W|reps and warranties|sunset provisions?|QM|safe harbor|tranches?|subordinat\w+|"
    r"credit enhancement|pari passu|waterfall|servicer|securities administrator|surveillance|"
    r"rebuttable presumption|mezz\w*|SPV|CUSIP|basis points?|bps|NAV|DPI|TVPI|clawback|covenant\w*|"
    r"amortiz\w+|hyperscal\w+|interconnection|capacity (?:market|price)|BDC|non-QM|prime jumbo|"
    r"loan-to-value|debt service coverage|net operating income)\b",
    re.I,
)
PASSIVE = re.compile(r"\b(?:is|are|was|were|been|being|be)\s+(?:\w+ly\s+)?\w+(?:ed|en)\b", re.I)
HEDGE = re.compile(r"\b(may|might|could|appears?|seems?|suggests?|likely|potentially|reportedly|perhaps)\b", re.I)
TEMPLATE_CLOSE = re.compile(r"(remains? (?:unknown|unclear|to be seen)|what remains unknown|whether .{0,120} remains)", re.I)


def syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith(("le", "ee")) and n > 1:
        n -= 1
    return max(1, n)


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9“\"'$(])", text.strip())
    return [p for p in parts if len(re.findall(r"\w+", p)) >= 2]


def metrics(paragraphs: list[str], title: str = "", excerpt: str = "") -> dict:
    text = " ".join(paragraphs)
    sents = sentences(text)
    words = re.findall(r"\w[\w’'%-]*", text)
    wc = len(words) or 1
    sl = [len(re.findall(r"\w+", s)) for s in sents] or [0]
    syl = sum(syllables(w) for w in words)
    fre = 206.835 - 1.015 * (wc / max(1, len(sents))) - 84.6 * (syl / wc)
    fk = 0.39 * (wc / max(1, len(sents))) + 11.8 * (syl / wc) - 15.59
    nums = re.findall(r"\d[\d,.]*", text)
    acr = [a for a in re.findall(r"\b[A-Z][A-Z&]{1,6}\b", text) if a not in KNOWN]
    first = (paragraphs[0] if paragraphs else "")[:210]
    last = paragraphs[-1] if paragraphs else ""
    para_words = sorted(len(re.findall(r"\w+", p)) for p in paragraphs) or [0]
    para_sents = [len(sentences(p)) for p in paragraphs] or [0]
    return {
        "words": wc,
        "paragraphs": len(paragraphs),
        "words_per_para_mean": round(wc / max(1, len(paragraphs)), 1),
        "words_per_para_p90": para_words[int(0.9 * (len(para_words) - 1))],
        "sent_per_para_mean": round(statistics.mean(para_sents), 1),
        "sentences": len(sents),
        "words_per_sentence_mean": round(statistics.mean(sl), 1),
        "words_per_sentence_p90": sorted(sl)[int(0.9 * (len(sl) - 1))],
        "pct_sentences_over_30": round(100 * sum(1 for x in sl if x > 30) / max(1, len(sl)), 1),
        "flesch_reading_ease": round(fre, 1),
        "fk_grade": round(fk, 1),
        "jargon_per_100w": round(100 * len(JARGON.findall(text)) / wc, 2),
        "unknown_acronyms_per_100w": round(100 * len(acr) / wc, 2),
        "numbers_per_100w": round(100 * len(nums) / wc, 2),
        "passive_per_100w": round(100 * len(PASSIVE.findall(text)) / wc, 2),
        "hedges_per_100w": round(100 * len(HEDGE.findall(text)) / wc, 2),
        "the_starter_pct": round(100 * sum(1 for s in sents if s.startswith("The ")) / max(1, len(sents)), 1),
        "hook_has_number": bool(re.search(r"\d", first)),
        "hook_starts_with_the": first.startswith("The "),
        "hook_first_sentence_words": len(re.findall(r"\w+", (sentences(first) or [first])[0])),
        "template_closer": bool(TEMPLATE_CLOSE.search(last)),
        "title_len": len(title),
        "title_has_number": bool(re.search(r"\d", title)),
        "excerpt_truncated": bool(excerpt) and len(excerpt) >= 190 and excerpt.rstrip()[-1] not in ".!?\"”’",
    }


def article_paragraphs(path: Path) -> list[str]:
    try:
        page = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    m = BODY.search(page)
    if not m:
        return []
    out = []
    for raw in PARA.findall(m.group(1)):
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()
        if len(t) > 30:
            out.append(t)
    return out


def agg(rows: list[dict]) -> dict:
    keys = [k for k, v in rows[0].items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    out = {k: round(statistics.mean(r[k] for r in rows), 1) for k in keys}
    for k in [k for k, v in rows[0].items() if isinstance(v, bool)]:
        out[k + "_pct"] = round(100 * sum(r[k] for r in rows) / len(rows))
    out["n"] = len(rows)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("insights_dir")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--out", default="")
    ap.add_argument("--since", default="2026-09-01")
    a = ap.parse_args()

    import weekly_wrap as w

    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    rng = random.Random(7)
    iso = re.compile(r"\d{4}-\d{2}-\d{2}")
    recent = [r for r in manifest if iso.match(str(r.get("date"))) and r["date"] >= a.since and r.get("format") != "weekly"]
    legacy = [r for r in manifest if not iso.match(str(r.get("date"))) or str(r.get("date")) < "2026-04-30"]
    groups: dict[str, list[dict]] = {}
    for r in recent:
        groups.setdefault("fmt:" + str(r.get("format")), []).append(r)
        groups.setdefault("sector:" + w.classify(r), []).append(r)

    rows_by_group: dict[str, list[dict]] = {}
    per_article: list[dict] = []

    def take(label: str, pool: list[dict], n: int) -> None:
        pool = list(pool)
        rng.shuffle(pool)
        out = []
        for r in pool:
            paras = article_paragraphs(Path(a.insights_dir) / f"{r['slug']}.html")
            if len(paras) >= 2:
                m = metrics(paras, r["title"], r.get("excerpt", ""))
                m.update(slug=r["slug"], group=label)
                out.append(m)
            if len(out) >= n:
                break
        rows_by_group[label] = out
        per_article.extend(out)

    for g, pool in sorted(groups.items()):
        take(g, pool, a.n)
    take("era:legacy(Mar-Apr 2026)", [r for r in legacy if r.get("slug")], a.n)

    q = json.loads((ROOT / "linkedin_essay_queue.json").read_text(encoding="utf-8"))
    li = []
    for item in q[:60]:
        paras = [p.strip() for p in re.split(r"\n\s*\n", item.get("linkedin_essay") or "") if len(p.strip()) > 30]
        if len(paras) >= 3:
            li.append(metrics(paras, item.get("title", "")))
    if li:
        rows_by_group["own_linkedin_essays"] = li

    unique = {m["slug"] for m in per_article}
    print(f"sampled {len(unique)} distinct published articles ({len(per_article)} group rows) + {len(li)} LinkedIn essays\n")
    cols = ["n", "words", "words_per_para_mean", "words_per_sentence_mean", "pct_sentences_over_30",
            "flesch_reading_ease", "fk_grade", "jargon_per_100w", "unknown_acronyms_per_100w",
            "numbers_per_100w", "hook_has_number_pct", "hook_starts_with_the_pct",
            "template_closer_pct", "excerpt_truncated_pct"]
    summary = {g: agg(r) for g, r in rows_by_group.items() if r}
    print(" | ".join(["group".ljust(30)] + [c[:10].ljust(10) for c in cols]))
    for g, s in summary.items():
        print(" | ".join([g.ljust(30)] + [str(s.get(c, "")).ljust(10) for c in cols]))
    fmt_rows = {}
    for m in per_article:
        if m["group"].startswith("fmt:"):
            fmt_rows[m["slug"]] = m
    pooled = agg(list(fmt_rows.values())) if fmt_rows else {}
    print("\nPOOLED recent published:", json.dumps(pooled))
    if a.out:
        Path(a.out).write_text(json.dumps({"summary": summary, "pooled": pooled, "articles": per_article}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
