#!/usr/bin/env python3
"""
Backfill the end-of-article CTA block onto already-published Insights articles.

The CTA (headline + "Start a Conversation" button that opens the chat widget)
was added to the live article template in daily_news_agent.py's render_html()
for articles published from here forward. This script applies the same CSS
and HTML to the archive of already-published articles so the change covers
existing traffic too, not just future articles.

Scope: only insights/*.html files that match the current article template
(identified by the presence of class="sources-block"). A separate cohort of
files in insights/ are building-profile pages from a different, unrelated
generator (data-driven property pages with PLUTO/ACRIS/DOF records, their
own "Discuss This Asset" CTA, and a different page structure entirely) --
those are deliberately left untouched by this script.

Usage:
  python backfill_article_cta.py --dry-run   # report what would change, write nothing
  python backfill_article_cta.py             # apply changes
  python backfill_article_cta.py --limit 5   # apply to only the first N matching files
                                              # (useful for a small first pass to review)
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SITE_ROOT = SCRIPT_DIR.parent
INSIGHTS_DIR = SITE_ROOT / "insights"

# Must match _CATEGORY_CTA_LINES in daily_news_agent.py exactly.
CATEGORY_CTA_LINES: dict[str, str] = {
    "Deal Intelligence": "Working through a deal with a similar structure?",
    "Debt & Equity": "Sourcing debt or equity for something like this?",
    "Capital Markets": "Navigating a similar capital markets decision?",
    "Market Analysis": "Thinking through how this affects your next move?",
    "Policy & Regulation": "Trying to work out how this affects your capital plan?",
    "_default": "Have a deal that raises questions like this one?",
}

CTA_MARKER = "article-cta-block"  # idempotency guard: skip files that already have it

CSS_ANCHOR = '    .sources-block a:hover { text-decoration: underline; }\n'
CSS_BLOCK = """    .sources-block a:hover { text-decoration: underline; }

    /* ── End-of-article CTA ── */
    .article-cta-block {
      margin: 3rem 0 2.5rem; padding: 2.25rem 2.25rem;
      background: rgba(201,168,76,0.06);
      border: 1px solid var(--gold-dim);
      border-left: 3px solid var(--gold);
      border-radius: 2px;
    }
    .article-cta-eyebrow {
      font-family: var(--sans); font-size: 0.7rem; letter-spacing: 0.18em;
      text-transform: uppercase; color: var(--gold); margin-bottom: 0.6rem;
      font-weight: 600;
    }
    .article-cta-headline {
      font-family: var(--serif); font-size: 1.5rem; font-weight: normal;
      line-height: 1.3; color: var(--white); margin-bottom: 0.6rem;
    }
    .article-cta-sub {
      font-family: var(--sans); font-size: 0.92rem; color: var(--muted);
      line-height: 1.6; margin-bottom: 1.4rem; max-width: 46ch;
    }
    .article-cta-btn {
      font-family: var(--sans); font-size: 0.78rem; letter-spacing: 0.08em;
      text-transform: uppercase; color: var(--black); background: var(--gold);
      border: 1px solid var(--gold); padding: 0.75rem 1.6rem; border-radius: 2px;
      cursor: pointer; transition: background 0.2s, opacity 0.2s;
      font-weight: 600;
    }
    .article-cta-btn:hover { opacity: 0.88; }
"""

HTML_ANCHOR = '      <div class="sources-block">'

CATEGORY_RE = re.compile(r'class="article-category">([^<]*)</div>')
NAV_CTA_RE = re.compile(r'class="nav-cta" onclick="openLTGChat\(\)"')
NAV_MOBILE_CTA_RE = re.compile(r'class="nav-mobile-cta" onclick="openLTGChat\(\)"')


def cta_headline_for(raw_category_html: str) -> str:
    category = html.unescape(raw_category_html).strip()
    return CATEGORY_CTA_LINES.get(category, CATEGORY_CTA_LINES["_default"])


def esc(value: str) -> str:
    return html.escape(value, quote=False)


def build_cta_html(category_html: str) -> str:
    headline = esc(cta_headline_for(category_html))
    return f"""      <div class="article-cta-block">
        <p class="article-cta-eyebrow">Talk to Light Tower Group</p>
        <h3 class="article-cta-headline">{headline}</h3>
        <p class="article-cta-sub">Tell us about it — Ben Rohr reviews every conversation personally and typically replies within one business day.</p>
        <button class="article-cta-btn" onclick="openLTGChat('article_cta')">Start a Conversation</button>
      </div>

"""


def process_file(path: Path) -> str:
    """Return a status string: 'updated', 'skipped-no-match', 'skipped-already-done', or 'error: ...'."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"error: could not read ({exc})"

    if CTA_MARKER in text:
        return "skipped-already-done"

    if '"sources-block"' not in text or HTML_ANCHOR not in text:
        return "skipped-no-match"

    category_match = CATEGORY_RE.search(text)
    category_html = category_match.group(1) if category_match else ""

    new_text = text

    if CSS_ANCHOR in new_text:
        new_text = new_text.replace(CSS_ANCHOR, CSS_BLOCK, 1)
    else:
        return "skipped-no-match"

    cta_html = build_cta_html(category_html)
    new_text = new_text.replace(HTML_ANCHOR, cta_html + HTML_ANCHOR, 1)

    new_text = NAV_CTA_RE.sub('class="nav-cta" onclick="openLTGChat(\'nav_cta\')"', new_text)
    new_text = NAV_MOBILE_CTA_RE.sub('class="nav-mobile-cta" onclick="openLTGChat(\'nav_mobile_cta\')"', new_text)

    if new_text == text:
        return "skipped-no-match"

    path.write_text(new_text, encoding="utf-8")
    return "updated"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N matching files")
    args = parser.parse_args()

    if not INSIGHTS_DIR.is_dir():
        raise SystemExit(f"insights/ directory not found at {INSIGHTS_DIR}")

    html_files = sorted(p for p in INSIGHTS_DIR.glob("*.html"))
    print(f"Found {len(html_files)} .html files in insights/")

    counts = {"updated": 0, "skipped-already-done": 0, "skipped-no-match": 0, "error": 0}
    processed = 0

    for path in html_files:
        if args.limit is not None and processed >= args.limit:
            break

        if args.dry_run:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                print(f"  error: {path.name} could not be read ({exc})")
                counts["error"] += 1
                continue
            if CTA_MARKER in text:
                counts["skipped-already-done"] += 1
                continue
            if '"sources-block"' not in text or HTML_ANCHOR not in text or CSS_ANCHOR not in text:
                counts["skipped-no-match"] += 1
                continue
            counts["updated"] += 1
            processed += 1
            continue

        status = process_file(path)
        processed += 1
        if status == "updated":
            counts["updated"] += 1
        elif status == "skipped-already-done":
            counts["skipped-already-done"] += 1
        elif status.startswith("error"):
            counts["error"] += 1
            print(f"  {status}: {path.name}")
        else:
            counts["skipped-no-match"] += 1

    label = "Would update" if args.dry_run else "Updated"
    print(f"\n{label}: {counts['updated']}")
    print(f"Already had the CTA (skipped): {counts['skipped-already-done']}")
    print(f"Did not match the modern template, left untouched: {counts['skipped-no-match']}")
    if counts["error"]:
        print(f"Errors: {counts['error']}")


if __name__ == "__main__":
    main()
