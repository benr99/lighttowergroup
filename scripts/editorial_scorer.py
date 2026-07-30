"""Editorial scoring rubric — 14-dimension automated article review.

Scores every generated article against publication thresholds.
Articles below minimum scores are flagged for revision or withheld.
"""

from __future__ import annotations
import json
import re
from typing import Any


# Minimum scores per dimension to publish
PUBLISH_MINIMUMS = {
    "factual_accuracy": 6,
    "financial_understanding": 6,
    "analytical_originality": 6,
    "thesis_strength": 5,
    "incentive_analysis": 5,
    "use_of_numbers": 5,
    "market_context": 5,
    "narrative_structure": 5,
    "opening_quality": 6,
    "sentence_quality": 5,
    "originality_of_language": 5,
    "intellectual_honesty": 7,
    "reader_utility": 5,
    "conclusion_quality": 5,
}

OVERALL_MINIMUM = 7.0

# Pre-compiled regex patterns used across scoring dimensions
_RE_DOLLAR_AMOUNT = re.compile(
    r'\$ ?[\d,.]+(?: ?(?:billion|million|trillion|[BMKT]))?'
    r'|[\d,.]+ (?:billion|million|trillion) (?:dollars|deal|transaction|sale|acquisition|office|property|building|loan|fund|portfolio)'
    r'|[\d.]+%'
    r'|[\d,]+ basis points'
    r'|\$ ?[\d,.]+'
)
_RE_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+')
_RE_HTML_TAG = re.compile(r'<[^>]+>')
_RE_PARAGRAPH_BREAK = re.compile(r'</p>\s*<p[^>]*>', re.IGNORECASE)
_RE_BR_TAG = re.compile(r'<br\s*/?>', re.IGNORECASE)


class EditorialScorer:
    """Scores articles against the 14-dimension editorial rubric."""

    def __init__(self):
        self.scores: dict[str, int] = {}
        self.issues: dict[str, list[str]] = {}

    def score(self, article: dict[str, Any], brief: dict[str, Any] | None = None) -> dict[str, Any]:
        """Score an article and determine publishability."""
        body = article.get("body_html", "")
        text = _strip_html(body)

        dimensions: list[tuple[str, Any, tuple]] = [
            ("factual_accuracy", self._score_factual_accuracy, (article, brief)),
            ("financial_understanding", self._score_financial_understanding, (article, brief)),
            ("analytical_originality", self._score_analytical_originality, (article, brief)),
            ("thesis_strength", self._score_thesis_strength, (article, brief)),
            ("incentive_analysis", self._score_incentive_analysis, (text,)),
            ("use_of_numbers", self._score_use_of_numbers, (text,)),
            ("market_context", self._score_market_context, (text,)),
            ("narrative_structure", self._score_narrative_structure, (text,)),
            ("opening_quality", self._score_opening_quality, (text,)),
            ("sentence_quality", self._score_sentence_quality, (text,)),
            ("originality_of_language", self._score_originality, (text,)),
            ("intellectual_honesty", self._score_intellectual_honesty, (text,)),
            ("reader_utility", self._score_reader_utility, (text,)),
            ("conclusion_quality", self._score_conclusion_quality, (text,)),
        ]
        self.scores = {}
        self.issues = {}
        for dim_name, method, args in dimensions:
            try:
                self.scores[dim_name] = method(*args)
            except Exception as e:
                self.scores[dim_name] = 5
                self.issues.setdefault(dim_name, []).append(f"Scoring error: {e}")

        below_minimum = []
        for dim, score in self.scores.items():
            minimum = PUBLISH_MINIMUMS.get(dim, 6)
            if score < minimum:
                below_minimum.append(f"{dim}: {score}/{minimum}")

        overall = round(sum(self.scores.values()) / len(self.scores), 1)
        publishable = overall >= OVERALL_MINIMUM and len(below_minimum) == 0

        return {
            "scores": self.scores,
            "overall": overall,
            "publishable": publishable,
            "below_minimum": below_minimum,
            "verdict": "PUBLISH" if publishable else f"REVISE — {len(below_minimum)} dimension(s) below minimum",
        }

    # ── Dimension Scorers ──
    def _score_factual_accuracy(self, article: dict[str, Any], brief: dict[str, Any] | None) -> int:
        sources = article.get("sources") or []
        if not sources:
            self.issues["factual_accuracy"] = ["No sources cited"]
            return 4
        if not isinstance(sources, list):
            self.issues["factual_accuracy"] = ["Sources is not a list"]
            return 4
        valid_urls = [s for s in sources if isinstance(s, dict) and isinstance(s.get("url", ""), str) and s.get("url", "").startswith("http")]
        if not valid_urls:
            self.issues["factual_accuracy"] = ["No valid source URLs"]
            return 5
        fixture_urls = [s for s in valid_urls if "example.com" in s.get("url", "").lower()]
        if fixture_urls:
            self.issues["factual_accuracy"] = ["Fixture source URLs detected (example.com)"]
            return 3
        if len(valid_urls) >= 3:
            return 9
        if len(valid_urls) >= 2:
            return 8
        return 7

    def _score_financial_understanding(self, article: dict[str, Any], brief: dict[str, Any] | None) -> int:
        body = str(article.get("body_html", "")).lower()
        score = 5  # base
        fin_terms = ["cap rate", "basis", "leverage", "yield", "spread", "amortization", "debt service",
                      "loan-to-value", "debt yield", "interest rate", "maturity", "refinancing"]
        found = 0
        for t in fin_terms:
            t_lower = t.lower()
            idx = body.find(t_lower)
            while idx != -1:
                before = body[max(0, idx - 30):idx]
                negated = any(n in before for n in (
                    "not ", "no ", "without ", "excluding ", "absence of ", "lacking ",
                    "was not ", "were not ", "did not ", "has not ", "have not ",
                    "is not ", "are not ", "isn't ", "aren't ", "wasn't ", "weren't ",
                ))
                if negated:
                    self.issues.setdefault("financial_understanding", []).append(
                        f"'{t}' appears negated; may not indicate genuine understanding"
                    )
                else:
                    found += 1
                idx = body.find(t_lower, idx + 1)
        score += min(3, found // 2)
        if brief and brief.get("transaction_economics", {}).get("calculated"):
            score += 1
        return min(10, score)

    def _score_analytical_originality(self, article: dict[str, Any], brief: dict[str, Any] | None) -> int:
        body = str(article.get("body_html", ""))
        # Check for original analytical verbs vs. "signals/reveals" crutch
        crutch_words = ["signals", "highlights", "underscores", "showcases", "demonstrates"]
        crutch_count = sum(1 for w in crutch_words if w in body.lower())
        if crutch_count > 5: return 4
        if crutch_count > 3: return 5
        if crutch_count > 1: return 6
        return 8

    def _score_thesis_strength(self, article: dict[str, Any], brief: dict[str, Any] | None) -> int:
        if not brief or not brief.get("thesis"):
            return 5
        thesis = str(brief.get("thesis", ""))
        if len(thesis) > 50: return 8
        return 6

    def _score_incentive_analysis(self, text: str) -> int:
        incentive_words = ["gain", "risk", "incentive", "motivated", "benefit", "exposure", "protect"]
        found = sum(1 for w in incentive_words if w in text.lower())
        return min(10, 4 + found)

    def _score_use_of_numbers(self, text: str) -> int:
        numbers = _RE_DOLLAR_AMOUNT.findall(text)
        if len(numbers) >= 8: return 9
        if len(numbers) >= 5: return 8
        if len(numbers) >= 3: return 7
        if len(numbers) >= 1: return 6
        return 4

    def _score_market_context(self, text: str) -> int:
        context_words = ["market", "sector", "comparable", "benchmark", "trend", "supply", "demand"]
        found = sum(1 for w in context_words if w in text.lower())
        return min(10, 4 + found)

    def _score_narrative_structure(self, text: str) -> int:
        paragraphs = [p.strip() for p in text.split('\n') if len(p.strip()) > 50]
        if len(paragraphs) < 3: return 4
        if len(paragraphs) < 5: return 6
        return 8

    def _score_opening_quality(self, text: str) -> int:
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        first_para = paragraphs[0] if paragraphs else ""
        generic = ["in a significant development", "the commercial real estate",
                    "in a move that", "today announced", "is pleased to announce"]
        if any(g in first_para.lower() for g in generic):
            return 4
        if len(first_para) > 100:
            return 8
        return 6

    def _score_sentence_quality(self, text: str) -> int:
        sentences = _RE_SENTENCE_SPLIT.split(text)
        if len(sentences) < 3: return 4
        lengths = [len(s.split()) for s in sentences if s.strip()]
        if not lengths: return 5
        # Good: varied lengths
        unique_lengths = len(set(lengths))
        if unique_lengths >= len(lengths) * 0.5: return 9
        if unique_lengths >= len(lengths) * 0.3: return 7
        return 6

    def _score_originality(self, text: str) -> int:
        ai_tells = ["the most important", "the real story", "this is not a story about",
                     "in this cycle", "at the end of the day", "it is worth noting",
                     "interestingly", "notably", "furthermore", "moreover"]
        count = sum(1 for t in ai_tells if t in text.lower())
        if count == 0: return 9
        if count <= 2: return 7
        if count <= 4: return 5
        return 3

    def _score_intellectual_honesty(self, text: str) -> int:
        # Reward: distinguishing fact from inference
        honesty_markers = ["according to", "reported", "disclosed", "filed",
                           "not disclosed", "unclear whether", "unknown", "may",
                           "could", "if", "appears to", "suggests that"]
        found = sum(1 for m in honesty_markers if m in text.lower())
        # Penalize: presenting speculation as fact
        overconfidence = ["will certainly", "undoubtedly", "without question", "obviously"]
        over = sum(1 for o in overconfidence if o in text.lower())
        score = min(10, 5 + found - over * 2)
        return max(2, score)

    def _score_reader_utility(self, text: str) -> int:
        utility_markers = ["should watch", "should monitor", "should test",
                           "the question is whether", "the key variable",
                           "investors should", "lenders should", "developers should"]
        found = sum(1 for m in utility_markers if m in text.lower())
        return min(10, 4 + found)

    def _score_conclusion_quality(self, text: str) -> int:
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        last_para = paragraphs[-1] if paragraphs else ""
        generic_ends = ["only time will tell", "remains to be seen", "will be watching",
                        "to be determined", "stay tuned"]
        if any(g in last_para.lower() for g in generic_ends):
            return 3
        if len(last_para) > 100:
            return 8
        return 6


def _strip_html(html: str) -> str:
    """Remove HTML tags for text analysis, preserving paragraph boundaries
    and decoding common HTML entities."""
    html = html or ""
    html = _RE_PARAGRAPH_BREAK.sub('\n', html)
    html = _RE_BR_TAG.sub('\n', html)
    html = _RE_HTML_TAG.sub(' ', html)
    html = html.replace('&amp;', '&')
    html = html.replace('&lt;', '<')
    html = html.replace('&gt;', '>')
    html = html.replace('&nbsp;', ' ')
    html = html.replace('&mdash;', '\u2014')
    html = html.replace('&rsquo;', '\u2019')
    html = html.replace('&ldquo;', '\u201c')
    html = html.replace('&rdquo;', '\u201d')
    html = html.replace('&lsquo;', '\u2018')
    html = html.replace('&#39;', "'")
    html = html.replace('&quot;', '"')
    html = re.sub(r'&#\d+;', ' ', html)
    html = re.sub(r'&[a-zA-Z]+;', ' ', html)
    return html


def score_article(article: dict[str, Any], brief: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convenience function to score an article."""
    scorer = EditorialScorer()
    return scorer.score(article, brief)
