"""Quality and safety gates for generated Light Tower Ideas articles."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any

from content_governance import independent_quality_issues

PLACEHOLDER_PATTERNS = [
    "Essay body to be generated",
    "Excerpt to be generated",
    "[Essay body",
    "[Excerpt",
    "TODO",
    "lorem ipsum",
]

SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9._-]+|ANTHROPIC_API_KEY|DEEPSEEK_API_KEY|OPENAI_API_KEY|NEWS_API_KEY|Bearer\s+[A-Za-z0-9._~+/=-]+)",
    re.I,
)
MOJIBAKE_RE = re.compile("[\u00e2\u00c3\ufffd]")
FIGURE_RE = re.compile(r"(\$[\d,.]+(?:\.\d+)?\s?(?:billion|million|trillion|bn|mm|m|b)?|\b\d+(?:\.\d+)?\s?%)", re.I)
QUOTE_RE = re.compile(r"(said|told|according to)\s+[\"']", re.I)
VISIT_RE = re.compile(r"\b(I|we)\s+(visited|walked|saw|stood|sat)\b", re.I)
HIGH_RISK_RE = re.compile(r"\b(fraud|criminal|corrupt|illegal|scam|bribery|indict|guilty|stole|lying)\b", re.I)
SPECULATIVE_RE = re.compile(
    r"\b(perhaps|almost certainly|will never know|more likely to|less likely to|unconscious confession|fictional kingdom|will be seen by|will hang|will not think|secretly|narcissism|slightly unsettling|not of this place|must live up to|this is what we meant all along|will be answered only when|laughter of children|mirror held up|inverted identity|architecture of inversion|spelled backward)\b",
    re.I,
)
NAME_WORDPLAY_RE = re.compile(r"\bname\b.{0,80}\bbackward\b|\bbackward\b.{0,80}\bname\b", re.I | re.S)
META_HEADING_RE = re.compile(r"<h2>\s*(a\s+)?resonant ending\s*</h2>", re.I)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return " ".join(self.parts)


def html_to_text(value: str) -> str:
    parser = TextExtractor()
    parser.feed(value or "")
    return re.sub(r"\s+", " ", parser.text()).strip()


def assert_no_mojibake(label: str, payload: object) -> None:
    text = json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
    match = MOJIBAKE_RE.search(text)
    if match:
        start = max(match.start() - 40, 0)
        end = min(match.end() + 40, len(text))
        raise ValueError(f"{label} contains possible mojibake near: {text[start:end]}")


def validate_article(article: dict[str, Any], dossier: dict[str, Any]) -> list[str]:
    """Return validation errors. Empty list means publishable."""
    errors: list[str] = []
    body = article.get("body_html", "")
    text = html_to_text(body)
    serialized = json.dumps(article, ensure_ascii=False)

    for field in ("slug", "title", "subtitle", "excerpt", "meta_description", "body_html"):
        if not str(article.get(field, "")).strip():
            errors.append(f"missing {field}")

    if len(text.split()) < 650:
        errors.append("body_html is below 650 words")

    if not article.get("sources"):
        errors.append("missing source URL")

    if str(article.get("generation_mode", "")).endswith("fallback"):
        errors.append("fallback writing held for editorial review")

    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.lower() in serialized.lower():
            errors.append(f"placeholder text found: {pattern}")

    if SECRET_RE.search(serialized):
        errors.append("secret-looking token found")

    if MOJIBAKE_RE.search(serialized):
        errors.append("mojibake found")

    allowed_figures = set()
    for value in dossier.get("reported_facts", []):
        allowed_figures.update(m.group(1) for m in FIGURE_RE.finditer(str(value)))
    allowed_figures.update(m.group(1) for m in FIGURE_RE.finditer(str(dossier.get("source_story", {}))))
    for figure in FIGURE_RE.findall(text):
        if figure not in allowed_figures:
            errors.append(f"unsupported figure: {figure}")

    if QUOTE_RE.search(text):
        errors.append("quote attribution pattern requires manual review")

    if VISIT_RE.search(text):
        errors.append("site-visit language requires manual review")

    if HIGH_RISK_RE.search(text) and not dossier.get("high_risk_allowed"):
        errors.append("high-risk allegation language found")

    if SPECULATIVE_RE.search(serialized) or NAME_WORDPLAY_RE.search(serialized):
        errors.append("unsupported speculative or imagined-scene language found")
    if META_HEADING_RE.search(body):
        errors.append("generic meta heading found")

    try:
        quality = float(article.get("quality_score", 0))
    except Exception:
        quality = 0
    if quality < 6.8:
        errors.append("quality score below threshold")

    try:
        risk = float(article.get("risk_score", 10))
    except Exception:
        risk = 10
    if risk > 4.5:
        errors.append("risk score above threshold")

    errors.extend(independent_quality_issues(article))

    return list(dict.fromkeys(errors))


def validate_html(html_doc: str) -> list[str]:
    errors = []
    required = [
        '<meta name="description"',
        '<link rel="canonical"',
        'property="og:title"',
        'name="twitter:card"',
        'application/ld+json',
        'itemscope itemtype="https://schema.org/Article"',
    ]
    for marker in required:
        if marker not in html_doc:
            errors.append(f"missing html marker: {marker}")
    if "noindex" in html_doc.lower():
        errors.append("published HTML contains noindex")
    if SECRET_RE.search(html_doc):
        errors.append("secret-looking token found in HTML")
    if MOJIBAKE_RE.search(html_doc):
        errors.append("mojibake found in HTML")
    return errors
