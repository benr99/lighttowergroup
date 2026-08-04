"""Choose the day's slate, and be able to say why.

The old rule reserved one slot per sector and filled it with whatever that
sector's strongest item happened to be, regardless of quality. That is how a
developer explainer entered a three-story edition: it did not win a place, it
was handed one because data centres is a sector and something had to fill it.

Two changes follow from that.

Quality is a hard floor; diversity is a soft preference
    A slot stays empty rather than being filled with something weak. Diversity
    shapes the slate only among items that already clear the bar, and can never
    promote an ineligible item.

A shortfall is an event, not a silent success
    When a sector cannot fill its slate the run says so and says why, so that
    "quiet day" is never confused with "our sources broke".
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Sequence

from intelligence_object import IntelligenceObject

#: Minimum score to occupy a slot. Below this an empty slot is the honest answer.
QUALITY_FLOOR = 35.0

#: Depth thresholds, before the evidence cap is applied.
TIER_A_FLOOR = 70.0
TIER_B_FLOOR = 50.0

SECTOR_TARGET = 10
GLOBAL_TARGET = 10

#: Soft caps, applied only when an alternative of adequate quality exists.
MAX_PER_SOURCE = 3
MAX_PER_COMPANY = 3

_ENTITY = re.compile(r"\b[A-Z][A-Za-z&'.-]{2,}(?:\s+[A-Z][A-Za-z&'.-]+)*")


@dataclass
class SectorSlate:
    sector: str
    selected: list[IntelligenceObject] = field(default_factory=list)
    considered: int = 0
    eligible: int = 0
    above_floor: int = 0
    target: int = SECTOR_TARGET
    shortfall: int = 0
    shortfall_reason: str = ""
    runner_up: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sector": self.sector,
            "target": self.target,
            "selected_count": len(self.selected),
            "considered": self.considered,
            "eligible": self.eligible,
            "above_floor": self.above_floor,
            "shortfall": self.shortfall,
            "shortfall_reason": self.shortfall_reason,
            "runner_up": self.runner_up,
            "selected": [
                {
                    "rank": o.sector_rank,
                    "title": o.title,
                    "score": o.final_score,
                    "band": o.tier,
                    "depth": o.recommended_depth,
                    "evidence": o.evidence_level,
                    "subsector": o.primary_subsector,
                    "why": o.selection_rationale,
                }
                for o in self.selected
            ],
        }


@dataclass
class SlateReport:
    sectors: dict[str, SectorSlate] = field(default_factory=dict)
    global_top: list[IntelligenceObject] = field(default_factory=list)
    total_considered: int = 0
    total_selected: int = 0
    depth_counts: dict[str, int] = field(default_factory=dict)
    shortfalls: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_shortfall(self) -> bool:
        return bool(self.shortfalls)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_considered": self.total_considered,
            "total_selected": self.total_selected,
            "depth_counts": self.depth_counts,
            "has_shortfall": self.has_shortfall,
            "shortfalls": self.shortfalls,
            "sectors": {k: v.to_dict() for k, v in self.sectors.items()},
            "global_top": [
                {"rank": o.global_rank, "sector": o.primary_sector,
                 "title": o.title, "score": o.final_score, "depth": o.recommended_depth}
                for o in self.global_top
            ],
        }


def _companies(obj: IntelligenceObject) -> set[str]:
    named = {e.get("name", "") for e in obj.entities if isinstance(e, dict)}
    named |= set(_ENTITY.findall(obj.title or "")[:3])
    return {n.lower().strip() for n in named if n and len(n) > 3}


def assign_depth(obj: IntelligenceObject) -> str:
    """Pick a depth by importance, then cap it at what the evidence supports."""
    if obj.final_score >= TIER_A_FLOOR:
        wanted = "tier_a"
    elif obj.final_score >= TIER_B_FLOOR:
        wanted = "tier_b"
    else:
        wanted = "tier_c"
    return obj.cap_depth_to_evidence(wanted)


def _shortfall_reason(considered: int, eligible: int, above_floor: int, target: int) -> str:
    if considered == 0:
        return ("no candidates reached this sector at all — check source health "
                "before assuming a quiet day")
    if eligible == 0:
        return (f"{considered} candidates found but none described a real event; "
                "likely a discovery or classification problem, not a quiet market")
    if above_floor == 0:
        return (f"{eligible} eligible candidates but none cleared the quality floor "
                f"of {QUALITY_FLOOR:.0f}; the day's material was genuinely weak")
    return (f"only {above_floor} of {eligible} eligible candidates cleared the floor, "
            f"against a target of {target}")


def select_for_sector(
    objects: Sequence[IntelligenceObject],
    sector: str,
    *,
    target: int = SECTOR_TARGET,
    floor: float = QUALITY_FLOOR,
) -> SectorSlate:
    """Rank and choose within one sector."""
    slate = SectorSlate(sector=sector, target=target)
    in_sector = [o for o in objects if o.primary_sector == sector]
    slate.considered = len(in_sector)

    eligible = [o for o in in_sector if o.eligible]
    slate.eligible = len(eligible)

    qualified = sorted(
        (o for o in eligible if o.final_score >= floor),
        key=lambda o: (-o.final_score, o.title),
    )
    slate.above_floor = len(qualified)

    chosen: list[IntelligenceObject] = []
    source_counts: dict[str, int] = {}
    company_counts: dict[str, int] = {}
    deferred: list[IntelligenceObject] = []

    for candidate in qualified:
        if len(chosen) >= target:
            break
        publisher = (candidate.sources[0].source_name if candidate.sources else "").lower()
        firms = _companies(candidate)

        crowded_source = source_counts.get(publisher, 0) >= MAX_PER_SOURCE
        crowded_company = any(company_counts.get(f, 0) >= MAX_PER_COMPANY for f in firms)
        if crowded_source or crowded_company:
            deferred.append(candidate)
            continue

        chosen.append(candidate)
        source_counts[publisher] = source_counts.get(publisher, 0) + 1
        for firm in firms:
            company_counts[firm] = company_counts.get(firm, 0) + 1

    # Diversity is a preference, not a reason to under-fill a slate.
    for candidate in deferred:
        if len(chosen) >= target:
            break
        chosen.append(candidate)

    chosen.sort(key=lambda o: (-o.final_score, o.title))
    for position, obj in enumerate(chosen, 1):
        obj.sector_rank = position
        obj.selected = True
        obj.recommended_depth = assign_depth(obj)
        obj.sector_percentile = (
            round(100.0 * (slate.above_floor - position + 1) / slate.above_floor, 1)
            if slate.above_floor else 0.0
        )
        obj.selection_rationale = (
            f"rank {position} of {len(chosen)} in {sector}: scored {obj.final_score:.1f} "
            f"({obj.tier}); {obj.evidence_level} evidence supports {obj.recommended_depth}"
        )

    slate.selected = chosen
    slate.shortfall = max(0, target - len(chosen))
    if slate.shortfall:
        slate.shortfall_reason = _shortfall_reason(
            slate.considered, slate.eligible, slate.above_floor, target
        )

    # Why did the last selected item beat the first one left out?
    remainder = [o for o in qualified if o not in chosen]
    below = sorted(
        (o for o in eligible if o.final_score < floor),
        key=lambda o: -o.final_score,
    )
    next_best = remainder[0] if remainder else (below[0] if below else None)
    if next_best is not None and chosen:
        last = chosen[-1]
        gap = last.final_score - next_best.final_score
        slate.runner_up = {
            "title": next_best.title,
            "score": next_best.final_score,
            "gap_to_last_selected": round(gap, 1),
            "explanation": (
                f"“{last.title[:60]}” took the final slot at {last.final_score:.1f}; "
                f"“{next_best.title[:60]}” scored {next_best.final_score:.1f}"
                + (f", below the floor of {floor:.0f}" if next_best.final_score < floor
                   else f", {gap:.1f} points behind")
            ),
        }
    return slate


def build_slates(
    objects: Iterable[IntelligenceObject],
    *,
    sectors: Sequence[str] | None = None,
    target: int = SECTOR_TARGET,
    floor: float = QUALITY_FLOOR,
    global_target: int = GLOBAL_TARGET,
) -> SlateReport:
    """Produce per-sector slates and a global ranking."""
    objects = list(objects)
    report = SlateReport(total_considered=len(objects))

    found = sectors or sorted({o.primary_sector for o in objects if o.primary_sector})
    for sector in found:
        report.sectors[sector] = select_for_sector(
            objects, sector, target=target, floor=floor
        )

    selected = [o for slate in report.sectors.values() for o in slate.selected]
    report.total_selected = len(selected)

    for position, obj in enumerate(
        sorted(selected, key=lambda o: (-o.final_score, o.title)), 1
    ):
        obj.global_rank = position
    report.global_top = sorted(selected, key=lambda o: o.global_rank)[:global_target]

    for obj in selected:
        report.depth_counts[obj.recommended_depth] = (
            report.depth_counts.get(obj.recommended_depth, 0) + 1
        )

    for sector, slate in report.sectors.items():
        if slate.shortfall:
            report.shortfalls.append({
                "sector": sector,
                "target": slate.target,
                "selected": len(slate.selected),
                "short_by": slate.shortfall,
                "reason": slate.shortfall_reason,
            })
    return report


def format_slate(slate: SectorSlate) -> str:
    """Readable per-sector slate for the run summary."""
    lines = [f"{slate.sector} — {len(slate.selected)}/{slate.target}"]
    for obj in slate.selected:
        lines.append(
            f"  {obj.sector_rank:>2}. {obj.final_score:>5.1f} [{obj.recommended_depth}] {obj.title[:66]}"
        )
    if slate.shortfall:
        lines.append(f"  short by {slate.shortfall}: {slate.shortfall_reason}")
    if slate.runner_up:
        lines.append(f"  next out: {slate.runner_up['explanation']}")
    return "\n".join(lines)
