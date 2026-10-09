#!/usr/bin/env python3
"""Audit articles ALREADY on the site against the source text the pipeline retrieved for them.

Matches insights.json entries to .editorial-state/retrieval-cache by source URL, then has a
reasoning-mode model rule on every sentence of the published page with the strict fact rules.
This estimates how often live articles state something their source does not support.

Run: python published_audit.py <insights.json> <insights_dir> [--n 30]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(HERE))

import claim_verifier as cv  # noqa: E402
from accuracy_audit import audit, auditor  # noqa: E402
from measure import article_paragraphs  # noqa: E402
from model_router import provider_config  # noqa: E402
from readability import sentences, unsupported_numbers  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("insights_dir")
    ap.add_argument("--n", type=int, default=30)
    args = ap.parse_args()

    cache = {}
    for path in (ROOT / ".editorial-state" / "retrieval-cache").glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for key in (data.get("canonical_url"), data.get("url"), data.get("final_url")):
            if key and len(data.get("text", "")) >= 1000:
                cache[str(key).rstrip("/")] = data["text"]

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    pool = []
    for record in manifest:
        url = str(record.get("sourceUrl") or "").rstrip("/")
        if url in cache and record.get("format") in {"brief", "analysis", "flagship"}:
            paras = article_paragraphs(Path(args.insights_dir) / f"{record['slug']}.html")
            if len(paras) >= 2:
                pool.append((record, paras, cache[url][:5000]))
    random.Random(3).shuffle(pool)
    pool = pool[: args.n]
    print(f"{len(pool)} published articles matched to a cached source")

    ds = provider_config("deepseek", for_writing=True)
    auditors = {"deepseek-reasoning-audit": auditor(ds)}

    def one(entry):
        record, paras, source = entry
        sents = [s for p in paras for s in sentences(p)]
        flagged = audit(sents, f"[Source]\n{source}", auditors)
        return {"slug": record["slug"], "date": record["date"], "sentences": len(sents), "flagged": flagged,
                "bad_numbers": unsupported_numbers(" ".join(paras), source)}

    with ThreadPoolExecutor(max_workers=2) as pool_exec:
        results = list(pool_exec.map(one, pool))
    (HERE / "published_audit_results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    total = sum(r["sentences"] for r in results)
    bad = sum(len(r["flagged"]) for r in results)
    arts = sum(1 for r in results if r["flagged"])
    print(f"sentences audited: {total}; flagged unsupported: {bad} ({100 * bad / max(1, total):.1f}%)")
    print(f"articles with at least one flagged sentence: {arts}/{len(results)}")
    print(f"articles with a figure absent from the source: {sum(1 for r in results if r['bad_numbers'])}")
    for r in results:
        for sent, why in r["flagged"].items():
            print(f"  [{r['slug'][:30]}] {sent[:150]}  <- {why[0][:120]}")


if __name__ == "__main__":
    main()
