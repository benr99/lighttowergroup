"""Deterministic readability checks shared by the article writer and the weekly wrap.

The benchmark is plain words with expert content: a sharp colleague explaining the
deal on a phone. Thresholds come from measuring Light Tower's own pages against
its own LinkedIn essays (outputs/readability/REPORT.md): published pages averaged
26 words per sentence and 100 per paragraph; the essays readers are given on
LinkedIn averaged 13 and 38. The limits below sit between the two, closer to the
essays, because the pages carry more reporting than a post.

Everything here returns *warnings*: strings written so they can be fed straight
back to a model as retry feedback. Callers decide whether a warning blocks.
"""

from __future__ import annotations

import html
import re
import statistics

MAX_MEAN_SENTENCE_WORDS = 22
MAX_SENTENCE_WORDS = 35
MAX_PARAGRAPH_WORDS = 60
MAX_PARAGRAPH_SENTENCES = 4  # the prompt asks for 1-3; 4 short ones still read fine
MAX_FIRST_PARAGRAPH_WORDS = 45
MAX_THE_STARTER_PCT = 35
EXCERPT_MIN_CHARS = 40
EXCERPT_MAX_CHARS = 200

BANNED_PHRASES = re.compile(
    r"\b(?:remains to be seen|it(?:'|’)s worth noting|landscape|navigat(?:e|es|ing)|highlights?|"
    r"underscor(?:e|es|ing)|dynamic|arguably|essentially|transformative|robust demand|"
    r"paradigm shift|only time will tell|market will be watching|game[- ]chang(?:er|ing)|"
    r"unprecedented|going forward|at the end of the day|in this cycle|the real story is|"
    r"the dossier|evidence level|single[- ]source|this analysis|the sources? (?:does|do) not (?:state|say|specify)|"
    r"this is not a (?:[a-z-]+ ){0,2}story)\b",
    re.I,
)
TEMPLATE_CLOSER = re.compile(
    r"(what remains (?:unknown|unclear)|remains? (?:unknown|unclear|to be seen)|"
    r"whether .{0,140}(?:remains|is yet) (?:unknown|unclear|to be seen))",
    re.I,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9“\"'$(])")


def words(text: str) -> list[str]:
    return re.findall(r"\w[\w’'%-]*", text or "")


# A period after these does not end a sentence ("U.S. Treasury", "Gov. Abbott", "Aug. 3", "J.P. Morgan", "Pier St. NW").
_ABBREVIATION = re.compile(
    r"\b(?:U\.S|U\.K|J\.P|N\.Y|D\.C|L\.P|Gov|Sen|Rep|Mr|Ms|Mrs|Dr|Inc|Corp|Co|Ltd|No|St|Ave|Blvd|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|vs|etc)\.|\b[A-Z]\.(?=\s[A-Z])"
)
_HOLD = "\u0001"


def sentences(text: str) -> list[str]:
    clean = re.sub(r"\s+", " ", text or "").strip()
    held = _ABBREVIATION.sub(lambda m: m.group(0)[:-1] + _HOLD, clean)
    parts = [p.replace(_HOLD, ".") for p in _SENTENCE_SPLIT.split(held)]
    return [p for p in parts if len(words(p)) >= 2]


def paragraph_texts(body_html: str) -> list[str]:
    out = []
    for raw in re.findall(r"<p\b[^>]*>(.*?)</p>", body_html or "", re.I | re.S):
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()
        if text:
            out.append(text)
    return out


def _snip(sentence: str, n: int = 9) -> str:
    return " ".join(sentence.split()[:n]) + "…"


def readability_warnings(paragraphs: list[str], *, excerpt: str = "") -> list[str]:
    """Plain-English problems with a draft, phrased as instructions to fix them."""
    warnings: list[str] = []
    if not paragraphs:
        return warnings
    all_sentences = [s for p in paragraphs for s in sentences(p)]
    lengths = [len(words(s)) for s in all_sentences] or [0]
    mean = statistics.mean(lengths)
    if mean > MAX_MEAN_SENTENCE_WORDS:
        warnings.append(
            f"Sentences average {mean:.0f} words. Aim for about 15 and stay under {MAX_MEAN_SENTENCE_WORDS - 4}. "
            "Split long sentences; one idea each."
        )
    long_sentences = [s for s in all_sentences if len(words(s)) > MAX_SENTENCE_WORDS]
    if long_sentences:
        examples = "; ".join(f"“{_snip(s)}” ({len(words(s))} words)" for s in long_sentences[:3])
        warnings.append(f"Split these sentences (over {MAX_SENTENCE_WORDS} words): {examples}")
    for index, paragraph in enumerate(paragraphs, 1):
        n_words, n_sents = len(words(paragraph)), len(sentences(paragraph))
        if n_words > MAX_PARAGRAPH_WORDS or n_sents > MAX_PARAGRAPH_SENTENCES:
            warnings.append(
                f"Paragraph {index} has {n_words} words and {n_sents} sentences. "
                f"Keep paragraphs to 3 sentences and {MAX_PARAGRAPH_WORDS} words; split it."
            )
            break  # one example is enough to fix the habit
    first = paragraphs[0]
    if len(words(first)) > MAX_FIRST_PARAGRAPH_WORDS:
        warnings.append(
            f"The opening paragraph is {len(words(first))} words. Open with one or two short sentences "
            "that give the who, the number and the tension."
        )
    if len(all_sentences) >= 8:
        the_pct = 100 * sum(1 for s in all_sentences if s.startswith("The ")) / len(all_sentences)
        if the_pct > MAX_THE_STARTER_PCT:
            warnings.append(f"{the_pct:.0f}% of sentences start with “The”. Vary the openings.")
    text = " ".join(paragraphs)
    found = sorted({m.group(0).lower() for m in BANNED_PHRASES.finditer(text)})
    if found:
        warnings.append("Remove these phrases: " + ", ".join(f"“{f}”" for f in found))
    if TEMPLATE_CLOSER.search(paragraphs[-1]):
        warnings.append(
            "Do not close on what is unknown or “remains to be seen”. End with one concrete thing "
            "a sponsor, lender or investor can check or ask this week."
        )
    if excerpt:
        value = excerpt.strip()
        if not (EXCERPT_MIN_CHARS <= len(value) <= EXCERPT_MAX_CHARS) or value[-1] not in ".!?":
            warnings.append(
                f"The excerpt must be one complete sentence of {EXCERPT_MIN_CHARS}-{EXCERPT_MAX_CHARS} "
                "characters that ends with a period. It is the card text and the LinkedIn preview."
            )
    return warnings


def trim_to_sentence(text: str, limit: int) -> str:
    """Shorten ``text`` to ``limit`` characters at a sentence or word boundary, never mid-word."""
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(clean) <= limit:
        return clean
    window = clean[:limit]
    cut = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
    if cut >= limit * 0.5:
        return window[: cut + 1]
    window = window.rsplit(" ", 1)[0].rstrip(",;:- ")
    return window + "…"


_NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
# Spelled-out numbers count too: "three buildings" must not pass when the source says two.
# "one" is left out on purpose (pronoun use: "one of", "no one").
_SPELLED = {
    "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8",
    "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
    "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18", "nineteen": "19",
    "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70",
    "eighty": "80", "ninety": "90", "hundred": "100", "thousand": "1000", "dozen": "12",
}
_SPELLED_RE = re.compile(r"\b(" + "|".join(_SPELLED) + r")\b", re.I)
_SCALES = (1.0, 1e3, 1e6, 1e9, 1e12, 1e-3, 1e-6, 1e-9, 1e-12)


def _clean(token: str) -> str:
    return token.replace(",", "").rstrip(".")


def numbers_in(text: str) -> set[str]:
    found = {_clean(n) for n in _NUM_RE.findall(text or "")}
    found |= {_SPELLED[w.lower()] for w in _SPELLED_RE.findall(text or "")}
    return found


def _supported(token: str, source_tokens: set[str], source_values: list[float]) -> bool:
    if token in source_tokens:
        return True
    try:
        value = float(token)
    except ValueError:
        return False
    decimals = len(token.split(".")[1]) if "." in token else 0
    for source in source_values:
        for scale in _SCALES:
            # "$16.8 million" is a faithful restatement of "$16,782,000"; "149" is not in either.
            if round(source * scale, decimals) == value:
                return True
    return False


def unsupported_numbers(output: str, source: str) -> list[str]:
    """Numbers in ``output`` that cannot be traced to ``source``, allowing rescaling and rounding.

    The writer may say "$16.8 million" for "$16,782,000". It may not produce a figure
    (a difference, a ratio, a hypothetical) that the source never stated.
    """
    source_tokens = numbers_in(source)
    source_values: list[float] = []
    for token in source_tokens:
        try:
            source_values.append(float(token))
        except ValueError:
            continue
    return sorted(n for n in numbers_in(output) if not _supported(n, source_tokens, source_values))


def strip_unsupported_sentences(paragraphs: list[str], source: str) -> tuple[list[str], list[str]]:
    """Last-resort fact guard: drop sentences whose numbers the source never gave.

    Returns the cleaned paragraphs and the sentences removed. An article that says a
    little less is better than one that states a figure nobody reported.
    """
    kept_paragraphs: list[str] = []
    removed: list[str] = []
    for paragraph in paragraphs:
        kept = []
        for sentence in sentences(paragraph):
            if unsupported_numbers(sentence, source):
                removed.append(sentence)
            else:
                kept.append(sentence)
        if kept:
            kept_paragraphs.append(" ".join(kept))
    return kept_paragraphs, removed


_COMMON_CAPS = {"Why", "What", "Check", "Ask", "Watch", "Read", "Here", "That", "This", "There", "When", "While",
                "Most", "Some", "Other", "Last", "Next", "First", "Second", "Third", "January", "February", "March",
                "April", "June", "July", "August", "September", "October", "November", "December", "Monday",
                "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "The", "And", "But"}


def unsupported_names(output: str, source: str) -> list[str]:
    """Capitalised names used mid-sentence that never appear in the source text.

    A cheap tripwire for invented places and parties ("high-barrier markets like Tampa"
    when the source named no such city). It is advisory: spelling variants can trip it.
    """
    haystack = re.sub(r"[^a-z0-9& ]+", " ", (source or "").lower())
    found: list[str] = []
    for sentence in sentences(output):
        # Drop the sentence's first word, which is capitalised for grammar, not because it is a name.
        rest = sentence.split(" ", 1)[1] if " " in sentence else ""
        for match in re.finditer(r"(?<=[ (“])\b([A-Z][A-Za-z&-]{2,})\b", " " + rest):
            token = match.group(1)
            if token in _COMMON_CAPS:
                continue
            if re.sub(r"[^a-z0-9&]+", "", token.lower()) in re.sub(r"[^a-z0-9&]+", "", haystack):
                continue
            if token not in found:
                found.append(token)
    return found
