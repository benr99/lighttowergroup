"""Human Style Gate — Programmatic Anti-AI & 60-Book Sentence Craft Enforcer.

Applies the Forensic Anti-AI / 100% Human Prose Framework inspired by the
Top 30 Books on Narrative Journalism (Blundell, McPhee, Wolfe, Talese, Didion,
Lewis, Ward, Hart) and the Top 30 Books on Sentence Craft & Style (Zinsser,
Strunk & White, Clark, Provost, Tufte, Landon, Fish, Forsyth, Hale, Lanham,
Pinker, Moran, Garner, Gowers).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

# Hard-banned AI tell phrases mapped to crisp human replacements or removal
AI_CLICHE_REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\bIn a market where [^,]+,\s*", re.IGNORECASE),
        "",
    ),
    (
        re.compile(r"\bAmidst a shifting [^,]+,\s*", re.IGNORECASE),
        "",
    ),
    (
        re.compile(r"\bis a textbook readout of\b", re.IGNORECASE),
        "shows",
    ),
    (
        re.compile(r"\ba textbook readout\b", re.IGNORECASE),
        "a clear signal",
    ),
    (
        re.compile(r"\bcrystallizes liquidity\b", re.IGNORECASE),
        "locks in a clean exit",
    ),
    (
        re.compile(r"\bIt remains to be seen\b", re.IGNORECASE),
        "The next test is",
    ),
    (
        re.compile(r"\btestament to\b", re.IGNORECASE),
        "proof of",
    ),
    (
        re.compile(r",\s*illustrating the\b", re.IGNORECASE),
        "—showing the",
    ),
    (
        re.compile(r",\s*underscoring the\b", re.IGNORECASE),
        "—proving the",
    ),
    (
        re.compile(r",\s*highlighting the\b", re.IGNORECASE),
        "—pointing to the",
    ),
    (
        re.compile(r"\$/GSF\b"),
        " a square foot",
    ),
    (
        re.compile(r"/GSF\b"),
        " a square foot",
    ),
    (
        re.compile(r"/BSF\b"),
        " per buildable foot",
    ),
    (
        re.compile(r"/unit\b"),
        " a door",
    ),
    (
        re.compile(r"/key\b"),
        " a key",
    ),
]

# Remove redundant dual-number notation in prose: "$46,200,000 ($46.2M)" -> "$46.2 million"
_DUAL_USD_RE = re.compile(
    r"\$([0-9]{1,3}(?:,[0-9]{3}){2,})\s*\(\$([0-9]+(?:\.[0-9]+)?)M\)"
)

# Convert raw ISO dates inside prose ("on 2026-03-22") into human dates ("on March 22, 2026")
_ISO_DATE_IN_PROSE_RE = re.compile(r"\b(20[12][0-9])-([01][0-9])-([0-3][0-9])\b")


def _humanize_iso_date(match: re.Match[str]) -> str:
    raw = match.group(0)
    try:
        dt = datetime.strptime(raw, "%Y-%m-%d")
        return dt.strftime("%B %d, %Y").replace(" 0", " ")
    except ValueError:
        return raw


def scrub_ai_tells(html_or_text: str) -> str:
    """Clean database leakage, duplicate number parentheticals, ISO dates, and AI clichés from prose."""
    text = str(html_or_text or "")

    # 1. Replace "$46,200,000 ($46.2M)" with "$46.2 million"
    text = _DUAL_USD_RE.sub(r"$\2 million", text)

    # 2. Convert raw YYYY-MM-DD dates in prose to "Month D, YYYY"
    text = _ISO_DATE_IN_PROSE_RE.sub(_humanize_iso_date, text)

    # 3. Apply cliché replacements
    for pattern, replacement in AI_CLICHE_REPLACEMENTS:
        text = pattern.sub(replacement, text)

    # 4. Capitalize first letter inside <p> if a leading subordinate clause was stripped
    text = re.sub(
        r"<p>\s*([a-z])",
        lambda m: f"<p>{m.group(1).upper()}",
        text,
    )

    return text


def measure_burstiness(html_or_text: str) -> dict[str, Any]:
    """Measure sentence-length variation (Gary Provost / Virginia Tufte burstiness check)."""
    plain = re.sub(r"<[^>]+>", " ", str(html_or_text or ""))
    plain = re.sub(r"\s+", " ", plain).strip()
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“])", plain)
        if len(s.strip().split()) >= 3
    ]
    if not sentences:
        return {"sentence_count": 0, "min_words": 0, "max_words": 0, "spread": 0, "passes": False}

    lengths = [len(s.split()) for s in sentences]
    min_w = min(lengths)
    max_w = max(lengths)
    spread = max_w - min_w
    has_short_punch = any(w <= 14 for w in lengths)
    has_narrative_sweep = any(w >= 20 for w in lengths)
    return {
        "sentence_count": len(sentences),
        "min_words": min_w,
        "max_words": max_w,
        "spread": spread,
        "has_short_punch": has_short_punch,
        "has_narrative_sweep": has_narrative_sweep,
        "passes": spread >= 8 and has_short_punch and has_narrative_sweep,
    }
