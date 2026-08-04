"""Score how consequential an item is, on a 0-100 scale that means something.

The previous scorer had three of ten measures that never varied: novelty was
hardcoded to 7, "editorial potential" measured article length and sat at its
floor for every single story, and a third returned the same answer 98% of the
time. About a fifth of the weight added identical points to everything, which
compressed the whole distribution. Across 288 candidates, scores only ever
reached 31 to 64 out of 100 -- so the 80-point bar for "must cover" was
unreachable by construction.

Two rules fix that, and everything here follows from them.

Every measure must be able to vary
    A measure that returns the same value for most items is not scoring, it is
    adding a constant. `distribution_report` exists to catch that happening
    again, and a test asserts it on real data.

Every score must explain itself
    Each component carries a rationale and the evidence behind it. A bare
    number is exactly how three dead measures went unnoticed for months.

Band meanings, documented rather than implied:

     90-100  defining; reshapes how the market is understood
     80-89   major story for its sector; essential coverage
     70-79   clearly important and highly relevant
     60-69   solid story with real implications
     50-59   legitimate market signal; useful but secondary
     40-49   routine, narrow, or thinly supported
      0-39   not publishable on its own
"""

from __future__ import annotations

import json
import math
import re
import statistics
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Sequence

from intelligence_object import (
    ContentType,
    EvidenceLevel,
    IntelligenceObject,
    NoveltyState,
    ObjectClass,
    ScoreComponent,
)

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"

BANDS = (
    (90, "defining", "Reshapes how the market is understood"),
    (80, "major", "Major story for its sector; essential coverage"),
    (70, "important", "Clearly important and highly relevant"),
    (60, "solid", "Solid story with real implications"),
    (50, "signal", "Legitimate market signal; useful but secondary"),
    (40, "routine", "Routine, narrow, or thinly supported"),
    (0, "not_publishable", "Not publishable on its own"),
)

#: What counts as large differs by sector. Each list is the dollar ladder from
#: "barely notable" to "extraordinary". A $100m property trade is significant; a
#: $100m private equity fund is not. Sourced from the observed distribution of
#: real deals per sector rather than a single universal scale.
_MAGNITUDE_LADDERS: dict[str, list[float]] = {
    "commercial_real_estate": [5e6, 25e6, 75e6, 200e6, 600e6, 1.5e9, 5e9],
    "private_equity":         [50e6, 150e6, 400e6, 1e9, 3e9, 8e9, 20e9],
    "data_centers":           [25e6, 100e6, 300e6, 750e6, 2e9, 5e9, 15e9],
    "energy":                 [25e6, 100e6, 300e6, 800e6, 2e9, 6e9, 15e9],
    "banking_credit":         [10e6, 50e6, 200e6, 750e6, 2e9, 10e9, 50e9],
    "local_government":       [1e6, 10e6, 40e6, 120e6, 400e6, 1e9, 3e9],
}

#: Non-dollar scale that still signals size, per sector.
_SCALE_PATTERNS = (
    (re.compile(r"\b([\d,]+(?:\.\d+)?)\s*(?:mw|megawatts?)\b", re.I), "mw", [10, 50, 150, 400, 1000, 2000, 5000]),
    (re.compile(r"\b([\d,]+(?:\.\d+)?)\s*units?\b", re.I), "units", [20, 100, 250, 600, 1500, 4000, 10000]),
    (re.compile(r"\b([\d,]+(?:\.\d+)?)\s*(?:sf|square feet)\b", re.I), "sf", [2e4, 1e5, 3e5, 7e5, 2e6, 5e6, 2e7]),
    (re.compile(r"\b([\d,]+(?:\.\d+)?)\s*acres?\b", re.I), "acres", [5, 25, 75, 200, 600, 2000, 8000]),
    (re.compile(r"\b([\d,]+(?:\.\d+)?)\s*(?:basis points|bps)\b", re.I), "bps", [10, 25, 50, 75, 100, 150, 250]),
)

_MONEY = re.compile(
    r"\$\s?([\d,]+(?:\.\d+)?)\s*(billion|bn|b|million|mm|m|trillion|tn|k)?\b", re.I
)
_MULT = {"trillion":1e12,"tn":1e12,"billion":1e9,"bn":1e9,"b":1e9,
         "million":1e6,"mm":1e6,"m":1e6,"k":1e3,None:1.0,"":1.0}

_SYSTEMIC = re.compile(
    r"\b(?:first (?:time|ever)|largest (?:ever|on record)|record(?:-| )(?:high|low|size)|"
    r"unprecedented|landmark|sets? (?:a )?precedent|bellwether|watershed|"
    r"systemic|contagion|bailout|receivership|conservatorship)\b", re.I)
_SURPRISE = re.compile(
    r"\b(?:unexpected(?:ly)?|surprise[sd]?|shock(?:ed|ing)?|"
    r"(?:higher|lower|weaker|stronger) than (?:expected|forecast)|"
    r"defy(?:ing)?|contrary to|reversal|abrupt|sudden(?:ly)?)\b", re.I)
_DISTRESS = re.compile(
    r"\b(?:default(?:s|ed)?|delinquen\w+|foreclos\w+|receivership|bankrupt\w+|"
    r"restructur\w+|workout|special servicing|distress(?:ed)?|impair\w+|write-?down|"
    r"covenant breach|maturity wall)\b", re.I)
_MAJOR_PARTY = re.compile(
    r"\b(?:blackstone|brookfield|kkr|apollo|carlyle|starwood|blackrock|"
    r"jpmorgan|goldman|morgan stanley|wells fargo|bank of america|citi(?:group)?|"
    r"prologis|vornado|sl green|boston properties|bxp|related|tishman|hines|"
    r"federal reserve|treasury|fdic|occ|sec|freddie mac|fannie mae|"
    r"microsoft|amazon|google|meta|oracle|nvidia)\b", re.I)


@lru_cache(maxsize=1)
def _profiles() -> dict[str, Any]:
    try:
        return json.loads((CONFIG_DIR / "scoring_profiles.json").read_text(encoding="utf-8")).get("profiles", {})
    except (OSError, json.JSONDecodeError):
        return {}


def _amounts(text: str) -> list[float]:
    out = []
    for raw, unit in _MONEY.findall(text or ""):
        try:
            out.append(float(raw.replace(",", "")) * _MULT.get((unit or "").lower(), 1.0))
        except ValueError:
            continue
    return out


def _ladder_score(value: float, ladder: Sequence[float]) -> int:
    """Position on a sector ladder, 1-10, with a smooth tail above the top rung."""
    if value <= 0:
        return 1
    for index, rung in enumerate(ladder):
        if value < rung:
            return max(1, index + 1)
    over = value / ladder[-1]
    return min(10, 8 + int(math.log10(max(1.0, over)) * 2))


def _text_of(obj: IntelligenceObject) -> str:
    return f"{obj.title} {obj.what_happened}"


# ── individual measures ────────────────────────────────────────────────────

def _magnitude(obj: IntelligenceObject) -> ScoreComponent:
    text = _text_of(obj)
    ladder = _MAGNITUDE_LADDERS.get(obj.primary_sector, _MAGNITUDE_LADDERS["commercial_real_estate"])
    best, why, evidence = 1, "no stated size", []

    amounts = _amounts(text)
    if amounts:
        largest = max(amounts)
        best = _ladder_score(largest, ladder)
        why = f"${largest:,.0f} against the {obj.primary_sector or 'CRE'} ladder"
        evidence.append(f"amount ${largest:,.0f}")

    for pattern, unit, unit_ladder in _SCALE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        try:
            value = float(match.group(1).replace(",", ""))
        except ValueError:
            continue
        scored = _ladder_score(value, unit_ladder)
        evidence.append(f"{value:,.0f} {unit}")
        if scored > best:
            best, why = scored, f"{value:,.0f} {unit} against the {unit} ladder"

    # A policy move carries weight without any figure at all.
    if obj.primary_sector == "fed_macro" and best <= 2:
        best, why = 6, "monetary policy carries weight independent of any dollar figure"
        evidence.append("fed_macro floor applied")

    return ScoreComponent("magnitude", best, 1.5, why, evidence)


def _market_impact(obj: IntelligenceObject) -> ScoreComponent:
    text = _text_of(obj)
    score, why, evidence = 3, "local or single-asset effect", []
    if obj.primary_sector in ("fed_macro", "banking_credit"):
        score, why = 6, "rates and credit conditions transmit across every sector"
    if obj.object_class in (ObjectClass.DATA_RELEASE, ObjectClass.MARKET_MOVEMENT):
        score = max(score, 6)
        why = "a market-wide reading rather than a single transaction"
        evidence.append(f"class {obj.object_class}")
    if _DISTRESS.search(text):
        score = max(score, 7)
        why = "distress reprices comparable assets and tightens lending"
        evidence.append("distress language present")
    if len(obj.secondary_sectors) >= 2:
        score = min(10, score + 2)
        why += "; touches several sectors"
        evidence.append(f"{len(obj.secondary_sectors)} secondary sectors")
    elif len(obj.secondary_sectors) == 1:
        score = min(10, score + 1)
    return ScoreComponent("market_impact", score, 1.3, why, evidence)


def _party_weight(obj: IntelligenceObject) -> ScoreComponent:
    text = _text_of(obj)
    names = {m.group(0).lower() for m in _MAJOR_PARTY.finditer(text)}
    if len(names) >= 2:
        return ScoreComponent("parties", 9, 1.1,
            "several institutions of scale involved", sorted(names)[:4])
    if names:
        return ScoreComponent("parties", 7, 1.1,
            f"a major institution is involved ({sorted(names)[0]})", sorted(names))
    if re.search(r"\b[A-Z][A-Za-z&'.-]+(?:\s+[A-Z][A-Za-z&'.-]+)+\b", obj.title or ""):
        return ScoreComponent("parties", 4, 1.1, "named but not widely-followed parties", [])
    return ScoreComponent("parties", 2, 1.1, "no clearly named party", [])


def _precedent(obj: IntelligenceObject) -> ScoreComponent:
    """Does this set a marker others will price against?

    Explicit "first ever" language is rare in feed text, so this also reads
    signals that do vary: exceptional size for the sector, distress (which
    reprices comparable assets), and trend framing.
    """
    text = _text_of(obj)
    score, why, evidence = 2, "an ordinary instance of its type", []

    match = _SYSTEMIC.search(text)
    if match:
        score, why = 8, "signals a first, a record, or systemic consequence"
        evidence.append(match.group(0))

    if _DISTRESS.search(text):
        score = max(score, 6)
        why = "distress sets a reference point for comparable assets"
        evidence.append("distress language")

    if obj.object_class == ObjectClass.TREND:
        score = max(score, 6)
        why = "presented as an emerging pattern"

    # Exceptional size is itself precedent-setting, and size does vary.
    ladder = _MAGNITUDE_LADDERS.get(obj.primary_sector, _MAGNITUDE_LADDERS["commercial_real_estate"])
    amounts = _amounts(text)
    if amounts:
        rung = _ladder_score(max(amounts), ladder)
        if rung >= 7:
            score = max(score, 7)
            why = "exceptional size for this sector sets a market marker"
            evidence.append(f"ladder rung {rung}/10")
        elif rung >= 5:
            score = max(score, 4)
            evidence.append(f"ladder rung {rung}/10")

    return ScoreComponent("precedent", score, 1.2, why, evidence)


def _surprise(obj: IntelligenceObject) -> ScoreComponent:
    """How far this departs from what the market already assumed.

    Explicit surprise wording is uncommon in short feed text, so distress and
    reversals -- which are surprising by nature -- also count.
    """
    text = _text_of(obj)
    score, why, evidence = 3, "broadly in line with expectations", []

    match = _SURPRISE.search(text)
    if match:
        score, why = 8, "explicitly diverges from what was expected"
        evidence.append(match.group(0))
    elif _DISTRESS.search(text):
        score, why = 6, "distress is rarely what the market had priced"
        evidence.append("distress language")
    elif re.search(r"(?:first|record|halt(?:s|ed)?|paus(?:e|es|ed)|cancel\w+|"
                   r"withdraw\w+|scrap(?:s|ped)?|delay(?:s|ed)?|abandon\w+)", text, re.I):
        score, why = 5, "a change of course rather than a continuation"
        evidence.append("reversal language")
    elif obj.object_class == ObjectClass.DATA_RELEASE:
        score, why = 4, "a scheduled release; surprise depends on the reading"

    return ScoreComponent("surprise", score, 1.0, why, evidence)


def _novelty(obj: IntelligenceObject) -> ScoreComponent:
    """Real novelty from editorial memory. Previously hardcoded to 7."""
    mapping = {
        NoveltyState.NEW: (9, "not previously covered"),
        NoveltyState.NEW_STAGE: (7, "a new stage of a transaction we have followed"),
        NoveltyState.MATERIAL_UPDATE: (6, "materially changes a story we ran"),
        NoveltyState.MINOR_FOLLOW_UP: (3, "a minor follow-up to existing coverage"),
        NoveltyState.DUPLICATE: (1, "the same event, reported again"),
        NoveltyState.ALREADY_PUBLISHED: (1, "we have already published this"),
    }
    score, why = mapping.get(obj.novelty_state, (5, "novelty unknown"))
    evidence = [f"state {obj.novelty_state}"]
    if obj.prior_object_ids:
        evidence.append(f"{len(obj.prior_object_ids)} prior sightings")
    return ScoreComponent("novelty", score, 1.2, why, evidence)


def _story_richness(obj: IntelligenceObject) -> ScoreComponent:
    """Substance available for analysis. Replaces the word-count measure."""
    score, evidence = 1, []
    facts = [f for f in obj.facts if not f.is_inference]
    if facts:
        score += min(3, len(facts))
        evidence.append(f"{len(facts)} extracted facts")
    if _amounts(_text_of(obj)):
        score += 2
        evidence.append("deal economics stated")
    if obj.entities:
        score += min(2, len(obj.entities))
        evidence.append(f"{len(obj.entities)} named parties")
    if obj.usable_full_text_count:
        score += 2
        evidence.append(f"{obj.usable_full_text_count} sources read in full")
    if obj.market_consequences:
        score += 1
        evidence.append("stated consequences")
    score = max(1, min(10, score))
    why = "enough material for real analysis" if score >= 6 else "little to work with beyond the headline"
    return ScoreComponent("story_richness", score, 1.2, why, evidence)


def _evidence_strength(obj: IntelligenceObject) -> ScoreComponent:
    mapping = {
        EvidenceLevel.PRIMARY_CORROBORATED: (10, "primary source, corroborated"),
        EvidenceLevel.CORROBORATED: (8, "two or more independent accounts"),
        EvidenceLevel.SINGLE_FULL_TEXT: (5, "one article, read in full"),
        EvidenceLevel.SINGLE_SUMMARY: (2, "a feed summary only"),
        EvidenceLevel.INSUFFICIENT: (0, "no usable source"),
    }
    score, why = mapping.get(obj.evidence_level, (0, "unknown"))
    return ScoreComponent("evidence", score, 1.4, why, [
        f"{obj.independent_source_count} independent",
        f"{obj.primary_source_count} primary",
    ])


def _right_to_win(obj: IntelligenceObject) -> ScoreComponent:
    """Whether a capital-markets desk can say something others would not."""
    text = _text_of(obj)
    score, evidence = 3, []
    if re.search(r"\b(?:cap rate|spread|basis points|bps|ltv|debt yield|coupon|"
                 r"refinanc\w+|maturity|covenant|mezzanine|preferred equity|"
                 r"securitiz\w+|tranche)\b", text, re.I):
        score += 4
        evidence.append("capital-structure detail present")
    if _amounts(text):
        score += 2
        evidence.append("deal economics available")
    if obj.primary_sector in ("commercial_real_estate", "banking_credit", "fed_macro"):
        score += 1
        evidence.append("core beat")
    score = max(1, min(10, score))
    return ScoreComponent("right_to_win", score, 1.1,
        "we can add capital-markets reading others will not" if score >= 6
        else "little for a capital-markets desk to add", evidence)


# ── penalties ──────────────────────────────────────────────────────────────

def _penalties(obj: IntelligenceObject) -> list[ScoreComponent]:
    """Separated from scores so they can be inspected and tuned independently."""
    out: list[ScoreComponent] = []
    text = _text_of(obj)

    if obj.novelty_state in (NoveltyState.DUPLICATE, NoveltyState.ALREADY_PUBLISHED):
        out.append(ScoreComponent("archive_repetition", -18, 1.0,
            "we have already covered this event", [obj.novelty_state]))
    elif obj.novelty_state == NoveltyState.MINOR_FOLLOW_UP:
        out.append(ScoreComponent("minor_follow_up", -8, 1.0,
            "an incremental update rather than a new story", []))

    if obj.content_type == ContentType.PRESS_RELEASE and obj.independent_source_count < 2:
        out.append(ScoreComponent("uncorroborated_release", -10, 1.0,
            "a company announcement nobody else has verified", []))

    if obj.content_type in (ContentType.INTERVIEW, ContentType.OPINION):
        out.append(ScoreComponent("opinion_format", -6, 1.0,
            "opinion carries less weight than a completed event", []))

    if obj.evidence_level == EvidenceLevel.SINGLE_SUMMARY:
        out.append(ScoreComponent("thin_evidence", -12, 1.0,
            "a summary alone cannot support analysis", []))

    if re.search(r"\b(?:routine|as expected|no change|reaffirm(?:s|ed)|maintains?)\b", text, re.I) \
            and not _SURPRISE.search(text):
        out.append(ScoreComponent("routine_event", -8, 1.0,
            "a routine announcement with no meaningful change", []))

    if re.search(r"\b(?:could|may|might|reportedly|rumou?r|speculat\w+|in talks|"
                 r"exploring|considering)\b", text, re.I) and obj.primary_source_count == 0:
        out.append(ScoreComponent("unconfirmed", -7, 1.0,
            "speculative and not confirmed by a primary source", []))

    return out


#: `_surprise` is deliberately NOT in this tuple.
#:
#: Change-against-expectations is editorially real, but it cannot be measured
#: from a headline and a 600-character summary: explicit surprise wording
#: appears in under 2% of the corpus, so including it produced a measure that
#: returned the same value for 98% of items. That is exactly the defect this
#: scorer exists to remove, and adding a tenth dead measure to replace three
#: old ones would be no improvement.
#:
#: It returns as a real measure once structured data lands and consensus can be
#: compared against actual. Until then its signal is folded into `_precedent`,
#: which reads departure-from-ordinary from size and distress instead.
MEASURES = (_magnitude, _market_impact, _party_weight, _precedent,
            _novelty, _story_richness, _evidence_strength, _right_to_win)


def band(score: float) -> tuple[str, str]:
    for floor, name, meaning in BANDS:
        if score >= floor:
            return name, meaning
    return "not_publishable", BANDS[-1][2]


def score_object(obj: IntelligenceObject) -> IntelligenceObject:
    """Score one object and record every component on it."""
    components = [measure(obj) for measure in MEASURES]

    profile = _profiles().get(obj.primary_sector, {})
    for component in components:
        # Sector profiles may nudge a measure's weight; absent config keeps 1.0.
        component.weight = round(component.weight * float(profile.get(component.name, 1.0)), 3)

    weight_total = sum(c.weight for c in components) or 1.0
    raw = sum(c.weighted for c in components) / weight_total  # 0-10
    base = raw * 10.0

    penalties = _penalties(obj)
    final = max(0.0, min(100.0, base + sum(p.score for p in penalties)))

    obj.importance_components = components
    obj.penalties = penalties
    obj.importance_score = round(base, 1)
    obj.editorial_opportunity_score = round(
        next(c.score for c in components if c.name == "right_to_win") * 10, 1)
    obj.final_score = round(final, 1)
    obj.tier = band(final)[0]
    return obj


def score_all(objects: Iterable[IntelligenceObject]) -> list[IntelligenceObject]:
    return [score_object(o) for o in objects]


def explain(obj: IntelligenceObject) -> str:
    """Human-readable account of why an object scored what it did."""
    name, meaning = band(obj.final_score)
    lines = [f"{obj.final_score:.1f}/100 — {name}: {meaning}", ""]
    for component in sorted(obj.importance_components, key=lambda c: -c.weighted):
        evidence = f"  [{', '.join(component.evidence)}]" if component.evidence else ""
        lines.append(f"  {component.name:<16} {component.score:>2}/10 x{component.weight:<5} "
                     f"{component.rationale}{evidence}")
    if obj.penalties:
        lines.append("")
        for penalty in obj.penalties:
            lines.append(f"  {penalty.name:<16} {penalty.score:>3}     {penalty.rationale}")
    return "\n".join(lines)


def distribution_report(objects: Sequence[IntelligenceObject]) -> dict[str, Any]:
    """Catch a measure going constant again.

    A measure whose values barely move is not scoring, it is adding a constant.
    This is the instrument that would have caught the previous three.
    """
    report: dict[str, Any] = {"count": len(objects), "measures": {}, "degenerate": []}
    if not objects:
        return report

    by_name: dict[str, list[float]] = {}
    for obj in objects:
        for component in obj.importance_components:
            by_name.setdefault(component.name, []).append(component.score)

    for name, values in by_name.items():
        unique = len(set(values))
        modal_share = max(values.count(v) for v in set(values)) / len(values)
        stdev = statistics.pstdev(values) if len(values) > 1 else 0.0
        entry = {
            "min": min(values), "max": max(values),
            "mean": round(statistics.mean(values), 2),
            "stdev": round(stdev, 3),
            "unique_values": unique,
            "modal_share": round(modal_share, 3),
        }
        if unique == 1:
            entry["verdict"] = "CONSTANT"
            report["degenerate"].append(name)
        elif modal_share >= 0.9:
            entry["verdict"] = "SATURATED"
            report["degenerate"].append(name)
        else:
            entry["verdict"] = "ok"
        report["measures"][name] = entry

    finals = [o.final_score for o in objects]
    report["final_score"] = {
        "min": min(finals), "max": max(finals),
        "mean": round(statistics.mean(finals), 1),
        "stdev": round(statistics.pstdev(finals), 2) if len(finals) > 1 else 0.0,
        "range_used": round(max(finals) - min(finals), 1),
    }
    return report
