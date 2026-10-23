"""Live NYC >$10M deal discovery from the city's own records, with nothing invented.

The earlier live scanner turned news headlines into deal dossiers and filled every field
it could not read (building size, year built, tax lot, seller, broker) with placeholders.
This replaces it. A deal enters only through a recorded deed, and every fact a story can
use comes from three public datasets:

    ACRIS master   (NYC Department of Finance)   the deed: amount, dates, % transferred
    ACRIS legals + parties                       the tax lots and addresses; seller and buyer
    PLUTO          (NYC Department of City Planning)  the building on each lot

Those records are written out as plain sentences (the "record sheet") and become the
story's only sources. The story is then written and fact-checked by the same v4 writer
and claim gate as every other article: a sentence that is not supported by the record
sheet is deleted. A field the records do not carry is left out, never estimated.

ACRIS is published with a lag of a few weeks, so "live" means: every qualifying deed
recorded in the look-back window that we have not covered yet, a few per run.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "config" / "nyc_transactions.json"

ACRIS_DOC_URL = "https://a836-acris.nyc.gov/DS/DocumentSearch/DocumentImageView?doc_id={doc}"
ZOLA_URL = "https://zola.planning.nyc.gov/l/lot/{boro}/{block}/{lot}"
BOROUGH_NAMES = {"1": "Manhattan", "2": "Bronx", "3": "Brooklyn", "4": "Queens", "5": "Staten Island"}
PLUTO_BOROUGH = {"1": "MN", "2": "BX", "3": "BK", "4": "QN", "5": "SI"}
DEED_TYPES = ("DEED", "DEEDO")
MAX_LOTS = 10  # larger portfolios are listed in the records but are too complex to summarise safely

# NYC Department of City Planning building class families (first letter).
BUILDING_CLASS_FAMILY = {
    "A": "one-family dwelling", "B": "two-family dwelling", "C": "walk-up apartment building",
    "D": "elevator apartment building", "E": "warehouse", "F": "factory or industrial building",
    "G": "garage", "H": "hotel", "I": "health care facility", "J": "theatre",
    "K": "store building", "L": "loft building", "M": "religious facility", "N": "asylum or home",
    "O": "office building", "P": "place of assembly or cultural facility", "Q": "outdoor recreation facility",
    "R": "condominium", "S": "mixed residential and commercial building", "T": "transportation facility",
    "U": "utility property", "V": "vacant land", "W": "educational facility", "Y": "government installation",
    "Z": "miscellaneous property",
}

Fetch = Callable[[str, dict[str, Any]], list[dict[str, Any]]]


def load_config() -> dict[str, Any]:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def socrata_fetch(url: str, params: dict[str, Any], timeout: float = 40.0) -> list[dict[str, Any]]:
    response = requests.get(url, params=params, timeout=timeout,
                            headers={"User-Agent": "LightTowerInsights/1.0 (records lookup)"})
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


# ── formatting: the record sheet says exactly what the record says ──────────

_KEEP_UPPER = {"JP", "HSBC", "TD", "BNY", "LLC", "LP", "LLP", "INC", "INC.", "N.A.", "NA", "II", "III", "IV", "REIT", "USA", "NY", "NYC", "FSB", "CO.", "CORP", "CORP."}


_SPECIAL = {"JPMORGAN": "JPMorgan", "MCDONALD": "McDonald", "BLACKROCK": "BlackRock", "ICECAP": "IceCap"}


def party_name(raw: str) -> str:
    words = []
    for word in str(raw or "").split():
        bare = word.rstrip(",")
        if bare.upper() in _SPECIAL:
            words.append(_SPECIAL[bare.upper()] + word[len(bare):])
        else:
            words.append(word if bare.upper() in _KEEP_UPPER else word[:1].upper() + word[1:].lower())
    return " ".join(words).replace(" ,", ",").strip()


def street_address(number: str, street: str) -> str:
    street = " ".join(w if w.isdigit() else w[:1].upper() + w[1:].lower() for w in str(street or "").split())
    return f"{str(number or '').strip()} {street}".strip()


def money(amount: float) -> str:
    whole = round(float(amount))
    cents = round(float(amount) - whole, 2)
    return f"${float(amount):,.2f}" if abs(cents) >= 0.005 else f"${whole:,}"


def short_money(amount: float) -> str:
    """$11.75 million, never rounded away from the recorded figure."""
    millions = float(amount) / 1_000_000
    text = f"{millions:,.6f}".rstrip("0").rstrip(".")
    return f"${text} million"


def long_date(iso: str) -> str:
    try:
        day = datetime.fromisoformat(str(iso)[:10])
    except ValueError:
        return ""
    return f"{day:%B} {day.day}, {day.year}"


def _percent(value: Any) -> str:
    """ACRIS percent transferred as written ("100", "49.5"); empty when missing."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return f"{number:g}"


def _join(names: list[str]) -> str:
    return "; ".join(n.rstrip(".") if n.endswith("..") else n for n in names).rstrip(".")


def _int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


# ── the deal ────────────────────────────────────────────────────────────────

@dataclass
class Lot:
    borough: str
    block: str
    lot: str
    address: str
    pluto: dict[str, Any] = field(default_factory=dict)

    @property
    def bbl(self) -> str:
        return f"{self.borough}-{self.block}-{self.lot}"


@dataclass
class DeedDeal:
    document_id: str
    doc_type: str
    amount: float
    document_date: str
    recorded_date: str
    percent: str
    lots: list[Lot]
    sellers: list[str]
    buyers: list[str]
    mortgages: list[dict[str, Any]] = field(default_factory=list)

    @property
    def borough(self) -> str:
        return BOROUGH_NAMES.get(self.lots[0].borough, "") if self.lots else ""

    @property
    def headline_address(self) -> str:
        return self.lots[0].address if self.lots else ""


def record_sheets(deal: DeedDeal) -> tuple[str, str]:
    """(ACRIS sheet, PLUTO sheet): plain sentences, each stating one recorded field."""
    lines = [
        f"NYC Department of Finance ACRIS record, document ID {deal.document_id}.",
        f"Document type: deed. The deed is dated {long_date(deal.document_date)} and was recorded on {long_date(deal.recorded_date)}.",
        f"The consideration stated on the deed is {money(deal.amount)}.",
    ]
    if deal.percent and deal.percent != "100":
        lines.append(f"The deed transfers {deal.percent} percent of the property.")
    lot_text = "; ".join(f"{lot.address}, {BOROUGH_NAMES.get(lot.borough, '')} (block {lot.block}, lot {lot.lot})" for lot in deal.lots)
    lines.append(f"Property covered by the deed: {lot_text}.")
    if deal.sellers:
        lines.append(f"Seller (grantor) named on the deed: {_join(deal.sellers)}.")
    if deal.buyers:
        lines.append(f"Buyer (grantee) named on the deed: {_join(deal.buyers)}.")
    for mortgage in deal.mortgages:
        lender = f" from {mortgage['lender']}" if mortgage.get("lender") else ""
        lines.append(
            f"A mortgage of {money(mortgage['amount'])}{lender} on the same property was recorded on "
            f"{long_date(mortgage['recorded_date'])} (ACRIS document ID {mortgage['document_id']}).")
    pluto_lines = []
    for lot in deal.lots:
        p = lot.pluto
        if not p:
            continue
        parts = []
        code = str(p.get("bldgclass") or "")
        if code:
            family = BUILDING_CLASS_FAMILY.get(code[:1], "")
            parts.append(f"building class {code}" + (f" ({family})" if family else ""))
        if _int(p.get("numfloors")):
            parts.append(f"{_int(p.get('numfloors'))} floors")
        if _int(p.get("unitsres")):
            parts.append(f"{_int(p.get('unitsres'))} residential units")
        if _int(p.get("unitstotal")):
            parts.append(f"{_int(p.get('unitstotal'))} total units")
        if _int(p.get("bldgarea")):
            parts.append(f"{_int(p.get('bldgarea')):,} square feet of building area")
        if _int(p.get("lotarea")):
            parts.append(f"{_int(p.get('lotarea')):,} square feet of lot area")
        if _int(p.get("yearbuilt")):
            parts.append(f"built in {_int(p.get('yearbuilt'))}")
        if p.get("zonedist1"):
            parts.append(f"zoning district {p['zonedist1']}")
        if p.get("zipcode"):
            parts.append(f"ZIP code {p['zipcode']}")
        if parts:
            pluto_lines.append(f"NYC Department of City Planning PLUTO data for {lot.address} "
                               f"(block {lot.block}, lot {lot.lot}): " + ", ".join(parts) + ".")
    return "\n".join(lines), "\n".join(pluto_lines)


def deal_object(deal: DeedDeal) -> Any:
    """An IntelligenceObject whose only sources are the record sheets."""
    from intelligence_object import ContentType, IntelligenceObject, RetrievalStatus, SourceRef

    acris_text, pluto_text = record_sheets(deal)
    first = deal.lots[0]
    sources = [SourceRef(
        item_id=f"acris-{deal.document_id}", source_name="NYC Department of Finance (ACRIS)",
        source_url=ACRIS_DOC_URL.format(doc=deal.document_id), canonical_url=ACRIS_DOC_URL.format(doc=deal.document_id),
        source_tier=1, content_type=ContentType.PRIMARY_DOCUMENT, retrieval_status=RetrievalStatus.STRUCTURED_DATA,
        publication_date=deal.recorded_date[:10], is_primary_authority=True, text_chars=len(acris_text),
        retrieved_text=acris_text, discovery_channel="acris")]
    if pluto_text:
        zola = ZOLA_URL.format(boro=first.borough, block=int(first.block), lot=int(first.lot))
        sources.append(SourceRef(
            item_id=f"pluto-{first.bbl}", source_name="NYC Department of City Planning (PLUTO)",
            source_url=zola, canonical_url=zola, source_tier=1, content_type=ContentType.PRIMARY_DOCUMENT,
            retrieval_status=RetrievalStatus.STRUCTURED_DATA, is_primary_authority=True,
            text_chars=len(pluto_text), retrieved_text=pluto_text, discovery_channel="acris"))
    title = f"{short_money(deal.amount)} deed recorded for {deal.headline_address}, {deal.borough}"
    obj = IntelligenceObject(
        object_id=f"acris-{deal.document_id}", cluster_id=f"acris-{deal.document_id}",
        primary_sector="commercial_real_estate", title=title,
        what_happened=f"A deed for {deal.headline_address}, {deal.borough}, states a consideration of {money(deal.amount)}.",
        sources=sources, content_type=ContentType.PRIMARY_DOCUMENT, event_type="property_acquisition",
        eligible=True, selected=True, final_score=60.0,
    )
    obj.eligibility_reason = "recorded NYC deed above $10 million (ACRIS)"
    obj.assess_evidence()
    obj.cap_depth_to_evidence("tier_b")
    return obj


# ── discovery ───────────────────────────────────────────────────────────────

_DEED_ID_RE = re.compile(r"\b(\d{16})\b")


def covered_deed_ids(manifest_path: Path | None = None) -> set[str]:
    """Deed document IDs already on the site (the October desk pages and our own)."""
    path = manifest_path or (REPO_ROOT / "insights.json")
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    covered: set[str] = set()
    for entry in entries if isinstance(entries, list) else []:
        for key in ("eventId", "sourceName", "transactionId"):
            value = str(entry.get(key) or "")
            if value.startswith("acris-"):
                covered.add(value[6:])
            covered.update(_DEED_ID_RE.findall(value) if key == "sourceName" else [])
    return covered


@dataclass
class DiscoveryReport:
    considered: int = 0
    found: int = 0
    skipped: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    def to_dict(self) -> dict[str, Any]:
        return {"considered": self.considered, "found": self.found, "skipped": self.skipped, "errors": self.errors}


def discover_deals(
    *, limit: int = 5, lookback_days: int = 60, covered: set[str] | None = None,
    fetch: Fetch | None = None, today: date | None = None,
) -> tuple[list[DeedDeal], DiscoveryReport]:
    """Qualifying deeds recorded in the look-back window that are not on the site yet."""
    config = load_config()
    endpoints = config.get("socrata_endpoints", {})
    minimum = float(config.get("min_consideration_usd", 10_000_000))
    excluded_classes = tuple(config.get("excluded_building_classes_prefixes", []))
    fetch = fetch or socrata_fetch
    covered = set(covered or ())
    report = DiscoveryReport()
    since = ((today or datetime.now(timezone.utc).date()) - timedelta(days=lookback_days)).isoformat()
    types = ",".join(f"'{t}'" for t in DEED_TYPES)
    try:
        masters = fetch(endpoints["acris_master"], {
            "$where": f"doc_type in({types}) AND document_amt > {int(minimum)} AND recorded_datetime >= '{since}'",
            "$order": "recorded_datetime DESC", "$limit": 200,
        })
    except Exception as exc:  # noqa: BLE001
        report.errors.append(f"ACRIS deed search failed: {type(exc).__name__}")
        return [], report

    deals: list[DeedDeal] = []
    seen_docs: set[str] = set()
    for master in masters:
        doc = str(master.get("document_id") or "")
        if not doc or doc in seen_docs:
            continue
        seen_docs.add(doc)
        report.considered += 1
        if doc in covered:
            report.skip("already on the site")
            continue
        try:
            legals = fetch(endpoints["acris_legals"], {"document_id": doc})
            parties = fetch(endpoints["acris_parties"], {"document_id": doc})
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"ACRIS lookup failed for {doc}: {type(exc).__name__}")
            continue
        lots: dict[tuple[str, str, str], Lot] = {}
        for legal in legals:
            key = (str(legal.get("borough") or ""), str(_int(legal.get("block"))), str(_int(legal.get("lot"))))
            if key[0] in BOROUGH_NAMES and key not in lots:
                lots[key] = Lot(*key, address=street_address(legal.get("street_number"), legal.get("street_name")))
        if not lots:
            report.skip("no NYC tax lot on the deed")
            continue
        if len(lots) > MAX_LOTS:
            report.skip(f"more than {MAX_LOTS} tax lots")
            continue
        if any(1001 <= int(lot.lot) <= 6999 for lot in lots.values()):
            report.skip("condominium unit")
            continue
        sellers = sorted({party_name(p.get("name")) for p in parties if str(p.get("party_type")) == "1" and p.get("name")})
        buyers = sorted({party_name(p.get("name")) for p in parties if str(p.get("party_type")) == "2" and p.get("name")})
        if not buyers or not sellers:
            report.skip("buyer or seller not named")
            continue
        if {b.lower() for b in buyers} == {s.lower() for s in sellers}:
            report.skip("same party on both sides")
            continue
        try:
            for lot in lots.values():
                rows = fetch(endpoints["pluto"], {"borough": PLUTO_BOROUGH[lot.borough], "block": lot.block, "lot": lot.lot})
                lot.pluto = rows[0] if rows else {}
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"PLUTO lookup failed for {doc}: {type(exc).__name__}")
        classes = [str(lot.pluto.get("bldgclass") or "") for lot in lots.values() if lot.pluto.get("bldgclass")]
        if excluded_classes and classes and all(c.startswith(excluded_classes) for c in classes):
            report.skip("residential condominium or co-op unit")
            continue
        deal = DeedDeal(
            document_id=doc, doc_type=str(master.get("doc_type") or ""), amount=float(master.get("document_amt") or 0),
            document_date=str(master.get("document_date") or "")[:10], recorded_date=str(master.get("recorded_datetime") or "")[:10],
            percent=_percent(master.get("percent_trans")), lots=list(lots.values()),
            sellers=sellers, buyers=buyers)
        deal.mortgages = _mortgages(deal, endpoints, fetch, report)
        deals.append(deal)
        report.found += 1
        if len(deals) >= limit:
            break
    return deals, report


def _mortgages(deal: DeedDeal, endpoints: dict[str, str], fetch: Fetch, report: DiscoveryReport) -> list[dict[str, Any]]:
    """Mortgages recorded on the deal's first lot within three days of the deed."""
    lot = deal.lots[0]
    try:
        legals = fetch(endpoints["acris_legals"], {"borough": lot.borough, "block": lot.block, "lot": lot.lot,
                                                   "$limit": 60, "$order": "good_through_date DESC"})
        ids = sorted({str(l.get("document_id")) for l in legals if l.get("document_id") and l.get("document_id") != deal.document_id})
        if not ids:
            return []
        quoted = ",".join(f"'{i}'" for i in ids[:50])
        masters = fetch(endpoints["acris_master"], {"$where": f"document_id in({quoted}) AND doc_type='MTGE'"})
    except Exception as exc:  # noqa: BLE001
        report.errors.append(f"mortgage lookup failed for {deal.document_id}: {type(exc).__name__}")
        return []
    out = []
    try:
        recorded = datetime.fromisoformat(deal.recorded_date)
    except ValueError:
        return []
    for m in masters:
        try:
            when = datetime.fromisoformat(str(m.get("recorded_datetime") or "")[:10])
        except ValueError:
            continue
        if abs((when - recorded).days) > 3 or not float(m.get("document_amt") or 0):
            continue
        lender = ""
        try:
            parties = fetch(endpoints["acris_parties"], {"document_id": m["document_id"]})
            lenders = sorted({party_name(p.get("name")) for p in parties if str(p.get("party_type")) == "2" and p.get("name")})
            lender = "; ".join(lenders)
        except Exception:  # noqa: BLE001
            pass
        out.append({"document_id": str(m["document_id"]), "amount": float(m["document_amt"]),
                    "recorded_date": str(m.get("recorded_datetime"))[:10], "lender": lender})
    return out[:3]


def discover_deed_objects(*, limit: int = 5, lookback_days: int = 60, covered: set[str] | None = None,
                          fetch: Fetch | None = None) -> tuple[list[Any], DiscoveryReport]:
    deals, report = discover_deals(limit=limit, lookback_days=lookback_days,
                                   covered=covered if covered is not None else covered_deed_ids(), fetch=fetch)
    return [deal_object(d) for d in deals], report
