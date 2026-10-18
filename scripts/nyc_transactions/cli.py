"""CLI runner for the Light Tower Group NYC >$10M Transaction Desk.

Usage:
    python -m scripts.nyc_transactions.cli --mode preview
    python -m scripts.nyc_transactions.cli --mode publish --limit 3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from nyc_transactions.economics import evaluate_eligibility
from nyc_transactions.generation import generate_nyc_transaction_article
from nyc_transactions.sources import get_curated_nyc_transactions
import site_renderer


def run_nyc_desk(mode: str = "preview", limit: int = 3, use_llm: bool = True) -> list[dict]:
    dossiers = get_curated_nyc_transactions()[:limit]
    published_articles: list[dict] = []

    preview_dir = REPO_ROOT / "data" / "nyc_transactions_preview"
    preview_dir.mkdir(parents=True, exist_ok=True)
    insights_dir = REPO_ROOT / "insights"
    insights_dir.mkdir(parents=True, exist_ok=True)

    for dossier in dossiers:
        elig = evaluate_eligibility(dossier)
        if not elig.eligible:
            print(f"Skipping {dossier.transaction_id}: {elig.reason_codes}")
            continue

        print(f"[NYC $10M+ Desk] Generating story for {dossier.property_info.address} (${dossier.sale_price_usd:,.0f})...")
        article = generate_nyc_transaction_article(dossier, use_llm=use_llm)
        html_out = site_renderer.render_html(article)

        if mode == "publish":
            target_html = insights_dir / f"{article['slug']}.html"
            target_html.write_text(html_out, encoding="utf-8")
            site_renderer.update_manifest(article)
            print(f"  -> Published {target_html.relative_to(REPO_ROOT)}")
        else:
            preview_html = preview_dir / f"{article['slug']}.html"
            preview_json = preview_dir / f"{article['slug']}.json"
            preview_html.write_text(html_out, encoding="utf-8")
            preview_json.write_text(json.dumps(article, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  -> Preview saved to {preview_html.relative_to(REPO_ROOT)}")

        published_articles.append(article)

    if mode == "publish" and published_articles:
        site_renderer.update_feed_xml()
        site_renderer.update_sitemap_xml()

    return published_articles


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the NYC >$10M Transaction Desk.")
    parser.add_argument("--mode", choices=["preview", "publish"], default="preview")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--no-llm", action="store_true", help="Use deterministic fallback writer without calling LLM.")
    args = parser.parse_args()

    articles = run_nyc_desk(mode=args.mode, limit=args.limit, use_llm=not args.no_llm)
    print(f"[NYC $10M+ Desk] Completed ({len(articles)} stories processed in '{args.mode}' mode).")


if __name__ == "__main__":
    main()
