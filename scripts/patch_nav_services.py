#!/usr/bin/env python3
"""
patch_nav_services.py — Add Services nav link to all insight article pages.

Two cases handled:
1. Old template (site-nav / nav-hide): inserts Services after Insights link
2. New template (nav-mobile): inserts Services between Buildings and About
"""
from pathlib import Path

INSIGHTS_DIR = Path(__file__).parent.parent / "insights"

# ── Case 1: old template ─────────────────────────────────────────────────────
OLD_INSIGHTS_LINK = '<a href="/insights.html" class="nav-hide">Insights</a>'
OLD_SERVICES_INSERT = (
    '<a href="/insights.html" class="nav-hide">Insights</a>\n'
    '        <a href="/services.html" class="nav-hide">Services</a>'
)

# ── Case 2: new template – desktop nav ───────────────────────────────────────
NEW_BUILDINGS_ABOUT = (
    '      <a href="/buildings.html">Buildings</a>\n'
    '      <a href="/about.html">About</a>'
)
NEW_BUILDINGS_SERVICES_ABOUT = (
    '      <a href="/buildings.html">Buildings</a>\n'
    '      <a href="/services.html">Services</a>\n'
    '      <a href="/about.html">About</a>'
)

# ── Case 2: new template – mobile nav ────────────────────────────────────────
NEW_MOB_BUILDINGS_ABOUT = (
    '    <a href="/buildings.html">Buildings</a>\n'
    '    <a href="/about.html">About</a>'
)
NEW_MOB_BUILDINGS_SERVICES_ABOUT = (
    '    <a href="/buildings.html">Buildings</a>\n'
    '    <a href="/services.html">Services</a>\n'
    '    <a href="/about.html">About</a>'
)


def patch_file(path: Path) -> str:
    """Return 'old_patched', 'new_patched', 'already_done', or 'no_match'."""
    text = path.read_text(encoding="utf-8")

    # Already done?
    if "/services.html" in text:
        return "already_done"

    # Case 1 – old template
    if OLD_INSIGHTS_LINK in text:
        patched = text.replace(OLD_INSIGHTS_LINK, OLD_SERVICES_INSERT, 1)
        path.write_text(patched, encoding="utf-8")
        return "old_patched"

    # Case 2 – new template without Services
    if NEW_BUILDINGS_ABOUT in text:
        patched = text.replace(NEW_BUILDINGS_ABOUT, NEW_BUILDINGS_SERVICES_ABOUT, 1)
        patched = patched.replace(NEW_MOB_BUILDINGS_ABOUT, NEW_MOB_BUILDINGS_SERVICES_ABOUT, 1)
        path.write_text(patched, encoding="utf-8")
        return "new_patched"

    return "no_match"


def main():
    files = sorted(INSIGHTS_DIR.glob("*.html"))
    print(f"Found {len(files)} article files in {INSIGHTS_DIR}\n")

    counts = {"old_patched": 0, "new_patched": 0, "already_done": 0, "no_match": 0}
    no_match_list = []

    for f in files:
        result = patch_file(f)
        counts[result] += 1
        if result == "no_match":
            no_match_list.append(f.name)

    print(f"Results:")
    print(f"  Old template patched : {counts['old_patched']}")
    print(f"  New template patched : {counts['new_patched']}")
    print(f"  Already had Services : {counts['already_done']}")
    print(f"  No match (skipped)   : {counts['no_match']}")
    if no_match_list:
        print(f"\nFiles with no match:")
        for name in no_match_list:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
