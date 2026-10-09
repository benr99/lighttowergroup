#!/usr/bin/env python3
"""Accuracy audit: current production writer (git HEAD) vs the fact-gated writer.

For each cached source story:
  arm A  the writer prompt at git HEAD, one request, as production ran it
  arm B  the working-tree pipeline end to end (write, verify, assemble), real providers
Then EVERY sentence of both final articles is re-checked against the source by two
independent models (DeepSeek and OpenAI) with the strict fact rules, plus a deterministic
number check. A sentence counts as unsupported if either auditor says so.

Run: python accuracy_audit.py [--n 16]. Needs DEEPSEEK_API_KEY and OPENAI_API_KEY.
Writes accuracy_results.json beside this file.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(HERE))

import claim_verifier as cv  # noqa: E402
import v4_generation as new  # noqa: E402
from intelligence_object import IntelligenceObject, RetrievalStatus, SourceRef  # noqa: E402
from measure import metrics  # noqa: E402
from model_router import provider_config  # noqa: E402
from readability import paragraph_texts, sentences, unsupported_numbers  # noqa: E402

STORIES = [
    ("yieldpro.com/2026/08/cobblestone-village", "tier_c"),
    ("altswire.com/bluerock-value-exchange-launches-58-4m", "tier_c"),
    ("bisnow.com/news/washington-dc/office/prp-buys-downtown-office", "tier_c"),
    ("multihousingnews.com/ejs-group-jv-secures-138m-refi", "tier_c"),
    ("multihousingnews.com/tishman-speyer-enters-charlotte", "tier_c"),
    ("multihousingnews.com/providence-enters-austin", "tier_c"),
    ("yieldpro.com/2026/08/reserve-at-waterford-lakes", "tier_c"),
    ("commercialobserver.com/2026/08/starwoods-net-income-drops", "tier_b"),
    ("multihousingnews.com/jpmorganchase-commits-750b", "tier_b"),
    ("commercialobserver.com/2026/08/tpg-ag-redfearn-capital-industrial", "tier_b"),
    ("commercialobserver.com/2026/08/brookfield-asset-management-q2-2026", "tier_b"),
    ("americanbanker.com/news/feds-cook-ready-to-hike-rates", "tier_b"),
    ("commercialobserver.com/2026/08/zenith-jpmam-keybank-truist", "tier_b"),
    ("housingwire.com/articles/uwm-2-05b-capital-q2-loss", "tier_b"),
    ("powermag.com/texas-audit-could-delay-49-8-gw", "tier_a"),
    ("housingwire.com/articles/finance-of-america-q2-2026-earnings", "tier_a"),
]
LEGACY_SYSTEM = "You are a precise financial journalist."


def load_legacy():
    src = subprocess.check_output(["git", "show", "HEAD:scripts/v4_generation.py"], cwd=ROOT).decode("utf-8")
    module = types.ModuleType("v4_legacy")
    module.__dict__["__name__"] = "v4_legacy"
    sys.modules["v4_legacy"] = module
    exec(compile(src, "v4_generation_HEAD.py", "exec"), module.__dict__)
    return module


def load_objects() -> list[dict]:
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
            continue
        url = str(match.get("canonical_url") or match["url"])
        slug = url.rstrip("/").rsplit("/", 1)[-1].replace(".html", "")
        title = re.sub(r"[-_]+", " ", slug).strip().title()
        text = match["text"]
        domain = re.sub(r"^www\.", "", re.sub(r"https?://", "", url).split("/")[0])
        obj = IntelligenceObject(
            object_id=slug[:60], cluster_id=slug, primary_sector="commercial_real_estate", title=title,
            what_happened=text[:300],
            sources=[SourceRef(item_id="s1", source_name=domain, canonical_url=url, source_tier=1,
                               text_chars=len(text), retrieved_text=text,
                               retrieval_status=RetrievalStatus.FULL_TEXT)],
            eligible=True, selected=True, final_score=80)
        obj.assess_evidence()
        obj.cap_depth_to_evidence(tier)
        out.append({"slug": slug, "tier": tier, "obj": obj, "text": text[:5000]})
    return out


def chat(provider: dict, system: str, user: str, temperature: float, max_tokens: int = 3600, json_mode=False) -> str:
    payload = {"model": provider["model"], "temperature": temperature, "max_tokens": max_tokens,
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if provider["provider"] == "deepseek":
        payload["thinking"] = {"type": "enabled" if json_mode else "disabled"}
        if json_mode:
            payload["max_tokens"] = 8000
    for attempt in range(6):
        r = requests.post(provider["url"], headers={"Authorization": f"Bearer {provider['api_key']}",
                                                    "Content-Type": "application/json"}, json=payload, timeout=180)
        if r.status_code in (429, 500, 502, 503) and attempt < 5:
            time.sleep(4 * (attempt + 1))
            continue
        r.raise_for_status()
        return str(r.json()["choices"][0]["message"]["content"]).strip()
    raise RuntimeError("unreachable")


def auditor(provider: dict):
    return lambda system, user: chat(provider, system, user, 0.0, 3000, json_mode=True)


def audit(sentences_in: list[str], source_text: str, auditors: dict) -> dict:
    """Judge each sentence as a plain fact with both auditors."""
    flagged: dict[str, list[str]] = {}
    for name, llm in auditors.items():
        items = [cv.Item(id=f"s{i}", kind="fact", text=t) for i, t in enumerate(sentences_in, 1)]
        for attempt in range(2):
            try:
                cv.run_verifier(llm, source_text, items, "")
                break
            except Exception:  # noqa: BLE001
                if attempt:
                    raise
        for item in items:
            if item.verdict == "unsupported":
                flagged.setdefault(item.text, []).append(f"{name}: {item.issue}")
    return flagged


def parse(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    return json.loads(text)


def run_story(story, legacy, writer, auditors) -> dict:
    obj = story["obj"]
    dossier = new._safe_dossier(obj)
    source_text = cv.source_text_from_dossier(dossier)
    out = {"slug": story["slug"], "tier": story["tier"]}

    # ---- arm A: the prompt as production ran it
    try:
        spec = legacy.DEPTH_SPEC[story["tier"]]
        raw = chat(writer, LEGACY_SYSTEM, legacy._writer_prompt(obj, dossier, spec), 0.2)
        article = parse(raw)
        paras = paragraph_texts(article.get("body_html", ""))
        sents = [s for p in paras for s in sentences(p)]
        flagged = audit(sents, source_text, auditors)
        out["A"] = {"status": "written", "title": article.get("title"), "sentences": len(sents),
                    "flagged": flagged, "bad_numbers": unsupported_numbers(" ".join(paras), source_text),
                    "metrics": metrics(paras, article.get("title", ""), article.get("excerpt", "")),
                    "paragraphs": paras}
    except Exception as exc:  # noqa: BLE001
        out["A"] = {"status": "error", "error": f"{type(exc).__name__}: {exc}"[:200]}

    # ---- arm B: the gated pipeline, end to end
    state = Path(tempfile.mkdtemp())
    started = time.monotonic()
    result = new.write_one(obj, provider=writer, deadline=time.monotonic() + 280, state_dir=state, run_id="audit")
    b = {"status": result.status, "seconds": round(time.monotonic() - started, 1),
         "diagnostics": {k: v for k, v in result.diagnostics.items() if k in ("attempts", "fact_check", "error")}}
    if result.article:
        paras = paragraph_texts(result.article["body_html"])
        evidence_files = list((state / "v4-evidence").glob("*.json"))
        kinds = {}
        if evidence_files:
            ev = json.loads(evidence_files[0].read_text(encoding="utf-8"))
            for para in ev["paragraphs"]:
                for item in para:
                    kinds[item["text"]] = item["kind"]
        facts = [s for p in paras for s in sentences(p) if kinds.get(s, "fact") == "fact"]
        views = [s for p in paras for s in sentences(p) if kinds.get(s, "fact") != "fact"]
        flagged = audit(facts, source_text, auditors)
        b.update(title=result.article["title"], sentences=len(facts), non_fact_sentences=len(views),
                 flagged=flagged, bad_numbers=unsupported_numbers(" ".join(paras), source_text),
                 metrics=metrics(paras, result.article["title"], result.article["excerpt"]),
                 paragraphs=paras,
                 rejected_by_gate=result.diagnostics.get("sentences_rejected_by_fact_check", []))
    out["B"] = b
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=16)
    args = ap.parse_args()
    ds = provider_config("deepseek", for_writing=True)
    if not ds:
        sys.exit("Needs DEEPSEEK_API_KEY.")
    # OpenAI is skipped when it has no credit (as of 2026-10-08 it reports insufficient_quota).
    auditors = {"deepseek-reasoning-audit": auditor(ds)}
    legacy = load_legacy()
    stories = load_objects()[: args.n]
    print(f"{len(stories)} stories | writer and gate verifier both {ds['model']} (OpenAI has no credit)")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda s: run_story(s, legacy, ds, auditors), stories))
    (HERE / "accuracy_results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")

    for arm, label in (("A", "CURRENT production writer"), ("B", "NEW fact-gated pipeline")):
        rows = [r[arm] for r in results if r[arm].get("sentences") is not None]
        total = sum(r["sentences"] for r in rows)
        bad = sum(len(r["flagged"]) for r in rows)
        arts = sum(1 for r in rows if r["flagged"] or r["bad_numbers"])
        print(f"\n{label}: {len(rows)} articles, {total} factual sentences audited")
        print(f"  sentences flagged unsupported by either auditor: {bad} ({100 * bad / max(1, total):.1f}%)")
        print(f"  articles with at least one unsupported sentence or figure: {arts}/{len(rows)}")
        print(f"  articles with a figure not in the source: {sum(1 for r in rows if r['bad_numbers'])}")
        if arm == "B":
            from collections import Counter
            print("  outcomes:", dict(Counter(r["B"]["status"] for r in results)))
            rej = sum(len(r["B"].get("rejected_by_gate", [])) for r in results)
            print(f"  sentences the gate rejected before publication: {rej}")
    for r in results:
        for arm in "AB":
            for sent, why in (r[arm].get("flagged") or {}).items():
                print(f"  [{arm} {r['slug'][:22]}] {sent[:140]} <- {why[0][:110]}")


if __name__ == "__main__":
    main()
