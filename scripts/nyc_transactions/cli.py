"""CLI runner for the Light Tower Group NYC >$10M Transaction Desk.

Usage:
    python -m scripts.nyc_transactions.cli --mode publish --limit 30 --force
    python -m scripts.nyc_transactions.cli --mode publish --limit 0 --scan-live
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
from nyc_transactions.sources import (
    discover_live_nyc_transactions,
    get_curated_nyc_transactions,
)
import site_renderer


def _existing_transaction_ids_and_slugs() -> set[str]:
    seen: set[str] = set()
    manifest_path = REPO_ROOT / "insights.json"
    if manifest_path.exists():
        try:
            items = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in items:
                if item.get("slug"):
                    seen.add(str(item["slug"]))
                if item.get("transactionId"):
                    seen.add(str(item["transactionId"]))
                if item.get("eventId"):
                    seen.add(str(item["eventId"]))
        except Exception:
            pass
    return seen


def run_nyc_desk(
    mode: str = "preview",
    limit: int = 30,
    use_llm: bool = False,
    scan_live: bool = False,
    force: bool = True,
) -> list[dict]:
    seen = _existing_transaction_ids_and_slugs()
    curated = get_curated_nyc_transactions()[:limit] if limit > 0 else []
    if not force:
        curated = [d for d in curated if d.transaction_id not in seen]

    # Sort oldest-to-newest when publishing into insights.json (since update_manifest inserts at index 0)
    # so the newest closing dates end up at the top of the manifest!
    dossiers = list(reversed(curated))

    if scan_live:
        for d in dossiers:
            seen.add(d.transaction_id)
        live_deals = discover_live_nyc_transactions(existing_slugs_or_ids=seen)
        if live_deals:
            print(f"[NYC $10M+ Desk] Discovered {len(live_deals)} new live NYC >$10M deals from RSS/ACRIS feeds!")
            dossiers.extend(live_deals)

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

        print(
            f"[NYC $10M+ Desk] Writing story for {dossier.property_info.address} "
            f"(${dossier.sale_price_usd:,.0f}, closed {dossier.closing_date})..."
        )
        article = generate_nyc_transaction_article(dossier, use_llm=use_llm)
        html_out = site_renderer.render_html(article)

        if mode == "publish":
            target_html = insights_dir / f"{article['slug']}.html"
            target_html.write_text(html_out, encoding="utf-8")
            site_renderer.update_manifest(article)
            print(f"  -> Published {target_html.relative_to(REPO_ROOT)} (dated {article['date']})")
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
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--use-llm", action="store_true", help="Call live LLM writer in addition to literary engine.")
    parser.add_argument("--no-llm", action="store_true", help="Use deterministic literary feature writer.")
    parser.add_argument("--scan-live", action="store_true", help="Scan live NYC RSS feeds and ACRIS for emerging >$10M transactions.")
    parser.add_argument("--no-force", action="store_true", help="Skip curated deals already present in insights.json.")
    args = parser.parse_args()

    use_llm = bool(args.use_llm and not args.no_llm)
    articles = run_nyc_desk(
        mode=args.mode,
        limit=args.limit,
        use_llm=use_llm,
        scan_live=args.scan_live,
        force=not args.no_force,
    )
    print(f"[NYC $10M+ Desk] Completed ({len(articles)} stories processed in '{args.mode}' mode).")


if __name__ == "__main__":
    main()
