#!/usr/bin/env python3
"""End-to-end check of the Friday wrap with the fact gate on, against real providers.

Builds a wrap from a manifest snapshot, then re-audits every published summary and
"why it matters" line against the item text it was written from.

Run: python wrap_accuracy.py <insights.json> <insights_dir> <YYYY-MM-DD friday>
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(HERE))

import claim_verifier as cv  # noqa: E402
import weekly_wrap as w  # noqa: E402
from accuracy_audit import audit, auditor  # noqa: E402
from model_router import provider_chain, provider_config  # noqa: E402
from v4_generation import _make_verifier  # noqa: E402


def main() -> None:
    manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    insights_dir = Path(sys.argv[2])
    friday = date.fromisoformat(sys.argv[3])
    chain = provider_chain(provider_config("deepseek", for_writing=True), for_writing=True)
    llm = w.make_llm(chain)
    verifier = _make_verifier(chain[0])
    out = w.build_wrap(manifest, friday, llm, insights_dir=insights_dir, verifier=verifier)
    print("status:", out["status"], "| featured", out.get("items_featured"), "| fell back to plain excerpt:", out.get("fallback_items"))
    for s in out.get("sections", []):
        print(f"  {s['label']}: {s['items']} items, {s['fallback_items']} fallback; problems: {[p[:90] for p in s['problems'][:3]]}")
    article = out["article"]
    print("title:", article["title"])

    # Re-audit what will actually be published, item by item.
    ds = provider_config("deepseek", for_writing=True)
    auditors = {"deepseek-reasoning-audit": auditor(ds)}
    # Rebuild per-item text by parsing the rendered body: each <li> holds summary + optional take.
    import re
    body = article["body_html"]
    pool = {i["title"]: i for i in w.load_week_items(manifest, *w.week_window(friday))}
    flagged, checked, with_take = [], 0, 0
    for li in re.findall(r"<li>(.*?)</li>", body, re.S):
        title_m = re.search(r"<strong><a[^>]*>(.*?)</a></strong>", li, re.S)
        if not title_m:
            continue
        import html as _html
        title = _html.unescape(title_m.group(1))
        item = pool.get(title)
        if not item:
            continue
        text = _html.unescape(re.sub(r"<[^>]+>", " ", li.replace(title_m.group(0), "")))
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\(\s*[^()]*\)\s*$", "", text).strip()  # trailing (Source)
        take = ""
        if "Why it matters:" in text:
            text, take = (t.strip() for t in text.split("Why it matters:", 1))
            with_take += 1
        source = f"{title}\n" + w.read_lead(item["slug"], max_chars=900, insights_dir=insights_dir) + " " + str(item.get("excerpt") or "")
        sents = [s for s in (text, take) if s]
        flagged.append((title, audit(sents, source, auditors)))
        checked += len(sents)
    bad = [(t, f) for t, f in flagged if f]
    print(f"\nre-audited {checked} published lines ({with_take} with a why-it-matters line)")
    print(f"lines flagged unsupported by the independent audit: {sum(len(f) for _, f in bad)}")
    for t, f in bad:
        for sent, why in f.items():
            print(f"  [{t[:40]}] {sent[:140]} <- {why[0][:120]}")
    print("\nSample of the published wrap text:")
    for li in re.findall(r"<li>(.*?)</li>", body, re.S)[:6]:
        print("  -", re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", "", li)))[:300])


if __name__ == "__main__":
    main()
