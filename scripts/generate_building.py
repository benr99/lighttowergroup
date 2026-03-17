#!/usr/bin/env python3
"""
Light Tower Group — Building Biography Generator
─────────────────────────────────────────────────
Pulls data from multiple NYC public sources and generates SEO-optimised
editorial building biography pages in the exact Light Tower Group brand style.

Data sources:
  • PLUTO        — physical characteristics, zoning, FAR, air rights, ownership
  • ACRIS        — mortgage history, deed transfers, lender names, loan amounts
  • DOF Sales    — actual sale prices and dates
  • DOB Permits  — recent construction and renovation activity
  • LL84/LL97    — energy benchmarking and emissions compliance
  • LPC          — landmark and historic district details

Usage:
  python generate_building.py "740 Park Avenue"
  python generate_building.py --batch buildings.txt

Requirements:
  pip install anthropic requests
  export ANTHROPIC_API_KEY=sk-ant-...
"""

import anthropic
import requests
import json
import re
import sys
import time
import argparse
import os
from datetime import date
from pathlib import Path
from textwrap import dedent

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Load .env from the same directory as this script
_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ── Config ─────────────────────────────────────────────────────────────────────
SITE_ROOT     = Path(__file__).parent.parent
INSIGHTS_DIR  = SITE_ROOT / "insights"
INSIGHTS_JSON = SITE_ROOT / "insights.json"

# NYC Open Data — Socrata endpoints
PLUTO_API       = "https://data.cityofnewyork.us/resource/64uk-42ks.json"
ACRIS_LEGALS    = "https://data.cityofnewyork.us/resource/8h5j-fqxa.json"
ACRIS_MASTER    = "https://data.cityofnewyork.us/resource/bnx9-e6tj.json"
ACRIS_PARTIES   = "https://data.cityofnewyork.us/resource/636b-3b5g.json"
DOF_SALES       = "https://data.cityofnewyork.us/resource/usep-8jbt.json"
DOB_PERMITS     = "https://data.cityofnewyork.us/resource/ipu4-2q9a.json"
ENERGY_LL84     = "https://data.cityofnewyork.us/resource/5zyy-y8am.json"
LPC_LANDMARKS   = "https://data.cityofnewyork.us/resource/7mgd-s57w.json"

# ACRIS document types we care about
MORTGAGE_TYPES  = ("MTGE", "SMTG", "AMTG", "CONV D", "AGMT")
DEED_TYPES      = ("DEED", "DEED IN LI", "DEEDO")
SATISFY_TYPES   = ("SATS", "SAT")

BOROUGH_NAMES = {
    "1": "Manhattan", "2": "The Bronx",
    "3": "Brooklyn",  "4": "Queens", "5": "Staten Island",
}
BLDG_CLASS_LABELS = {
    "D": "Elevator Apartment Building", "C": "Walk-Up Apartment Building",
    "A": "Single-Family Residence",     "B": "Two-Family Residence",
    "S": "Mixed Residential/Commercial","O": "Office Building",
    "K": "Retail Store Building",       "H": "Hotel",
    "F": "Factory/Industrial",          "L": "Loft Building",
    "R": "Condominium",                 "W": "Cultural/Institutional",
    "Z": "Mixed Use",
}
LOT_TYPES = {
    "1": "Block Assemblage", "2": "Irregular Lot", "3": "Interior Lot",
    "4": "Through Lot", "5": "Corner Lot",
}

client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from env


# ── Helpers ────────────────────────────────────────────────────────────────────

def get(url: str, params: dict, timeout: int = 12) -> list:
    """Safe Socrata GET — returns empty list on any error."""
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json() or []
    except Exception:
        return []


def parse_bbl(bbl_str: str) -> dict:
    """Split a 10-digit PLUTO BBL into the components other APIs expect."""
    s = str(bbl_str or "").strip().zfill(10)
    return {
        "boro":  s[0],
        "block": str(int(s[1:6])),   # strip leading zeros
        "lot":   str(int(s[6:10])),
    }


def fmt_money(val) -> str:
    try:
        v = int(float(str(val).replace(",", "").replace("$", "")))
        if v >= 1_000_000:
            return f"${v/1_000_000:.2f}M"
        if v >= 1_000:
            return f"${v:,}"
        return f"${v}"
    except Exception:
        return str(val)


def fmt_date(iso: str) -> str:
    try:
        return date.fromisoformat(iso[:10]).strftime("%B %Y")
    except Exception:
        return iso[:10] if iso else ""


# ── PLUTO ──────────────────────────────────────────────────────────────────────

def fetch_pluto(address: str) -> dict:
    """Fetch the best-matching PLUTO record for a given NYC address.

    Accepts addresses with optional borough suffix like '395 Carroll St, Brooklyn'
    or '75 West End Avenue, Manhattan'.  The borough suffix is stripped before
    querying PLUTO and used as an additional borocode filter when available.
    """
    # Split optional ", Borough" suffix
    BOROUGH_CODES_INV = {v: k for k, v in BOROUGH_NAMES.items()}
    boro_filter = ""
    street_part = address.strip()
    if ", " in street_part:
        parts = street_part.rsplit(", ", 1)
        maybe_boro = parts[1].strip().title()
        if maybe_boro in BOROUGH_CODES_INV:
            street_part = parts[0].strip()
            boro_code   = BOROUGH_CODES_INV[maybe_boro]
            boro_filter = f" AND borocode='{boro_code}'"

    clean = re.sub(r"\s+", " ", street_part.upper())

    # Try exact match first, then progressively looser LIKE queries
    for where in [
        f"upper(address) = '{clean}'{boro_filter}",
        f"upper(address) like '{clean}%'{boro_filter}",
        f"upper(address) like '%{clean}%'{boro_filter}",
        # Fallback without borough filter
        f"upper(address) = '{clean}'",
        f"upper(address) like '{clean}%'",
    ]:
        results = get(PLUTO_API, {"$where": where, "$limit": 10, "$order": "unitsres DESC"})
        if results:
            return max(results, key=lambda r: int(r.get("unitsres") or 0))
    raise ValueError(f"No PLUTO record found for: {address}")


def parse_pluto(p: dict) -> dict:
    """Extract and compute all useful fields from a raw PLUTO record."""
    def _int(k):  return int(float(p.get(k) or 0)) or None
    def _flt(k):  return float(p.get(k) or 0) or None
    def _str(k):  return (p.get(k) or "").strip()

    bldg_code  = _str("bldgclass")[:1].upper()
    bldg_type  = BLDG_CLASS_LABELS.get(bldg_code, "Multifamily Residential Building")
    borough    = BOROUGH_NAMES.get(_str("borocode"), _str("borough") or "New York")
    year_built = _int("yearbuilt")
    far        = _flt("builtfar")
    max_far    = _flt("residfar") or _flt("commfar")
    lot_area   = _int("lotarea")

    # Air rights: unused FAR × lot area
    air_rights_sf = None
    if far and max_far and max_far > far and lot_area:
        air_rights_sf = int((max_far - far) * lot_area)

    # Implied market value: NYC Class 2 assessed value is ~45% of market value
    assess_total  = _int("assesstot")
    implied_value = int(assess_total / 0.45) if assess_total else None

    # Space-use breakdown
    space = {}
    for label, key in [
        ("Residential", "resarea"), ("Commercial", "comarea"),
        ("Office", "officearea"), ("Retail", "retailarea"),
        ("Garage", "garagearea"), ("Storage", "strgearea"),
        ("Industrial", "factryarea"),
    ]:
        v = _int(key)
        if v:
            space[label] = v

    return {
        "address":       _str("address").title(),
        "borough":       borough,
        "neighborhood":  _str("nta").replace("  ", " ") or borough,
        "community_dist":_str("cd"),
        "year_built":    year_built,
        "year_alter1":   _int("yearalter1"),
        "year_alter2":   _int("yearalter2"),
        "num_floors":    _int("numfloors"),
        "units_res":     _int("unitsres"),
        "units_total":   _int("unitstotal"),
        "bldg_area_sf":  _int("bldgarea"),
        "lot_area_sf":   lot_area,
        "bldg_type":     bldg_type,
        "bldg_class":    _str("bldgclass"),
        "zoning":        _str("zonedist1"),
        "overlay":       _str("overlay1"),
        "far":           far,
        "max_far":       max_far,
        "air_rights_sf": air_rights_sf,
        "assess_total":  assess_total,
        "assess_land":   _int("assessland"),
        "implied_value": implied_value,
        "owner":         _str("ownername").title(),
        "landmark":      _str("landmark"),
        "hist_dist":     _str("histdist"),
        "lot_type":      LOT_TYPES.get(_str("lottype"), ""),
        "space":         space,
        "bbl":           _str("bbl"),
        "borocode":      _str("borocode"),
        "block":         _str("block"),
        "lot":           _str("lot"),
    }


# ── ACRIS — Mortgage & Deed History ───────────────────────────────────────────

def fetch_acris(building: dict) -> dict:
    """
    Pull mortgage and deed history from ACRIS for this BBL.
    Returns: most recent mortgage (lender, amount, date) + last deed (buyer, price, date).
    """
    boro  = building["borocode"]
    block = building["block"]
    lot   = building["lot"]

    if not (boro and block and lot):
        return {}

    # Step 1: get all document IDs for this BBL
    legals = get(ACRIS_LEGALS, {
        "$where": f"borough='{boro}' AND block='{block}' AND lot='{lot}'",
        "$select": "document_id",
        "$limit": 200,
    })
    doc_ids = [l["document_id"] for l in legals if l.get("document_id")]
    if not doc_ids:
        return {}

    # Step 2: fetch master records for those doc IDs in one query
    id_list = ",".join(f"'{d}'" for d in doc_ids[:100])  # Socrata limit
    masters = get(ACRIS_MASTER, {
        "$where": f"document_id IN ({id_list})",
        "$select": "document_id,doc_type,document_date,document_amt,recorded_datetime",
        "$order": "document_date DESC",
        "$limit": 100,
    })

    mortgages = sorted(
        [m for m in masters if m.get("doc_type") in MORTGAGE_TYPES and m.get("document_amt")],
        key=lambda x: x.get("document_date", ""), reverse=True
    )
    satisfactions = {m["document_id"] for m in masters if m.get("doc_type") in SATISFY_TYPES}
    deeds = sorted(
        [m for m in masters if m.get("doc_type") in DEED_TYPES and m.get("document_amt")],
        key=lambda x: x.get("document_date", ""), reverse=True
    )

    result = {}

    # Most recent active mortgage
    if mortgages:
        mtg = mortgages[0]
        # Get lender name from parties table
        parties = get(ACRIS_PARTIES, {
            "$where": f"document_id='{mtg['document_id']}' AND party_type='2'",
            "$select": "name",
            "$limit": 1,
        })
        lender = parties[0]["name"].title() if parties else "Unknown Lender"
        result["mortgage"] = {
            "amount":   int(float(mtg.get("document_amt", 0) or 0)),
            "date":     mtg.get("document_date", "")[:10],
            "lender":   lender,
            "doc_type": mtg.get("doc_type", ""),
        }

    # Most recent deed (sale)
    if deeds:
        deed = deeds[0]
        parties = get(ACRIS_PARTIES, {
            "$where": f"document_id='{deed['document_id']}' AND party_type='2'",
            "$select": "name",
            "$limit": 1,
        })
        buyer = parties[0]["name"].title() if parties else "Unknown"
        result["last_deed"] = {
            "amount": int(float(deed.get("document_amt", 0) or 0)),
            "date":   deed.get("document_date", "")[:10],
            "buyer":  buyer,
        }

    # Mortgage history summary (last 3)
    result["mortgage_history"] = [
        {
            "amount": int(float(m.get("document_amt", 0) or 0)),
            "date":   m.get("document_date", "")[:10],
            "type":   m.get("doc_type", ""),
        }
        for m in mortgages[:3]
    ]

    return result


# ── DOF — Sales History ────────────────────────────────────────────────────────

def fetch_dof_sales(building: dict) -> list:
    """Pull recent property sales from NYC DOF rolling sales data."""
    block = building["block"]
    lot   = building["lot"]
    boro  = building["borocode"]
    if not (block and lot and boro):
        return []

    sales = get(DOF_SALES, {
        "$where": (
            f"block='{block.zfill(5)}' AND lot='{lot.zfill(4)}' "
            f"AND upper(borough)='{BOROUGH_NAMES.get(boro, '').upper()}'"
        ),
        "$order": "sale_date DESC",
        "$limit": 5,
    })

    # Also try without borough filter if no results
    if not sales:
        sales = get(DOF_SALES, {
            "$where": f"block='{block}' AND lot='{lot}'",
            "$order": "sale_date DESC",
            "$limit": 5,
        })

    result = []
    for s in sales:
        price = int(float(str(s.get("sale_price") or "0").replace(",", "") or 0))
        if price > 10_000:   # filter out nominal transfers ($0, $10, etc.)
            result.append({
                "price": price,
                "date":  (s.get("sale_date") or "")[:10],
                "class": s.get("building_class_category", ""),
            })
    return result


# ── DOB — Recent Permits ───────────────────────────────────────────────────────

def fetch_dob_permits(building: dict) -> list:
    """Pull significant recent DOB permits."""
    block = building["block"]
    lot   = building["lot"]
    boro  = building["borocode"]
    if not (block and lot and boro):
        return []

    permits = get(DOB_PERMITS, {
        "$where": (
            f"block='{block}' AND lot='{lot}' AND borough='{boro}' "
            f"AND issuance_date > '2018-01-01'"
        ),
        "$order": "issuance_date DESC",
        "$select": "permit_type,work_type,filing_date,issuance_date,job_description,owner_s_business_name",
        "$limit": 20,
    })

    # Filter for meaningful work types only
    meaningful = {"NB", "A1", "A2", "DM"}   # New Building, Major Alt, Minor Alt, Demolition
    return [
        {
            "type":        p.get("permit_type", ""),
            "work":        p.get("work_type", ""),
            "date":        (p.get("issuance_date") or "")[:10],
            "description": p.get("job_description", ""),
        }
        for p in permits
        if p.get("permit_type", "").upper() in meaningful
    ][:5]


# ── LL84 — Energy Benchmarking ─────────────────────────────────────────────────

def fetch_energy(building: dict) -> dict:
    """Pull LL84 energy benchmarking data. BBL is 10-digit in this dataset."""
    bbl = building.get("bbl", "")
    if not bbl:
        return {}

    rows = get(ENERGY_LL84, {
        "$where": f"bbl='{bbl}'",
        "$order": "report_year DESC",
        "$limit": 3,
    })
    if not rows:
        return {}

    r = rows[0]   # most recent year
    result = {"report_year": r.get("report_year", "")}

    score = r.get("energy_star_score") or r.get("energystarscore")
    if score:
        try:
            result["energy_star_score"] = int(float(score))
        except Exception:
            pass

    eui = r.get("source_eui") or r.get("sourceeui") or r.get("site_eui")
    if eui:
        try:
            result["source_eui"] = float(eui)
        except Exception:
            pass

    ghg = r.get("total_ghg_emissions") or r.get("ghg_emissions")
    if ghg:
        try:
            result["ghg_emissions"] = float(ghg)
        except Exception:
            pass

    status = r.get("ll84_compliance_status") or r.get("compliance_status")
    if status:
        result["compliance_status"] = str(status)

    return result


# ── LPC — Landmark Details ─────────────────────────────────────────────────────

def fetch_lpc(building: dict) -> dict:
    """Pull LPC landmark/historic district details by address."""
    address = building["address"].upper()
    rows = get(LPC_LANDMARKS, {
        "$where": f"upper(street_address) like '%{address}%'",
        "$limit": 3,
    })
    if not rows:
        return {}
    r = rows[0]
    return {
        "name":             r.get("lm_name", r.get("landmark_name", "")),
        "architect":        r.get("architect", ""),
        "style":            r.get("style", ""),
        "designation_date": (r.get("designated_date") or r.get("designation_date") or "")[:10],
        "type":             r.get("lm_type", r.get("landmark_type", "")),
    }


# ── Enrichment Orchestrator ────────────────────────────────────────────────────

def enrich(building: dict) -> dict:
    """Pull all supplementary data sources and add to the building dict."""
    print("  Fetching ACRIS (mortgage & deed history)...")
    building["acris"] = fetch_acris(building)
    time.sleep(0.3)

    print("  Fetching DOF sales history...")
    building["sales"] = fetch_dof_sales(building)
    time.sleep(0.3)

    print("  Fetching DOB permits...")
    building["permits"] = fetch_dob_permits(building)
    time.sleep(0.3)

    print("  Fetching LL84 energy data...")
    building["energy"] = fetch_energy(building)
    time.sleep(0.3)

    if building.get("landmark") or building.get("hist_dist"):
        print("  Fetching LPC landmark details...")
        building["lpc"] = fetch_lpc(building)
    else:
        building["lpc"] = {}

    return building


# ── Content Generation ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = dedent("""
    You write for Light Tower Group, a New York commercial real estate capital advisory
    firm run by Benjamin Rohr. Your job is to produce building analysis pieces that
    read like Wall Street Journal capital markets reporting — not like a brochure,
    not like a blog post, and not like AI-generated content.

    THE MODEL: WSJ "Heard on the Street" crossed with a sharp CRE broker's perspective.
    Think of how WSJ covers a deal that reveals something larger about a market.
    The architectural observation is your lead — but it earns its place by connecting
    directly to the financial argument. Beauty is not decoration here. It's evidence.

    STRUCTURE (follow this every time):
    1. LEAD — Open with one specific, concrete observation about the building. Not a
       statement of theme. A detail. The limestone setback. The pre-war floor plate.
       The fact that the building changed hands twice in eight years. Start there.
    2. NUT GRAPH — Tell the reader exactly what this piece argues and why it matters
       now. One short paragraph. The thesis, not the preamble.
    3. BODY — Architectural analysis, then capital stack analysis. Each paragraph
       introduces one idea, supports it with specific data, and moves forward.
       No paragraph should exist just to transition. Every one must add information.
    4. IMPLICATIONS — What does the data actually signal? What should a sponsor,
       lender, or buyer understand about this asset's position in 2025-2026?
    5. KICKER — One or two sentences. Return to the opening observation and push it
       forward. Leave the reader with a specific, forward-looking thought.

    VOICE RULES — non-negotiable:
    — Short sentences carry authority. Long ones dilute it. Alternate for rhythm.
    — Active voice only. "The building traded" not "the building was traded."
    — No hedging. "The debt suggests refinancing pressure" not "one might argue
      that the debt could potentially suggest refinancing challenges."
    — No parallel threes. "Precision, elegance, and permanence" is AI filler.
    — No throat-clearing openers: "In a city that...", "Few buildings capture...",
      "There is something about...", "What makes this building remarkable..."
    — No adjectives that aren't earned by the sentence before them.
    — No corporate filler: testament to, epitome of, speaks to, underscores, reflects.
    — When you have real data — a mortgage amount, a lender name, a sale date, a
      permit filing — use it. That specificity is what separates this from everything
      else on the internet. "$47.5M from Signature Bank in 2019" beats "significant
      institutional debt" every time.
    — Write with conviction. This is analysis, not both-sidesing. Take a position.

    WHAT NOT TO WRITE:
    — Do not write "This building is a testament to..."
    — Do not open with the building's address as the first sentence.
    — Do not write a paragraph that just describes what the building looks like
      without connecting it to an argument about money, time, or the market.
    — Do not use: iconic, nestled, boasts, stunning, vibrant, world-class, hidden gem,
      state-of-the-art, timeless, remarkable, extraordinary, or "in the heart of."
    — Do not pad word count with transitions ("Furthermore," "Moreover," "It is
      worth noting that").

    SEO RULES (built into the writing, never bolted on):
    — Use the full address, neighborhood, borough, year built, and building type
      naturally within the first 200 words. These are the search terms that matter.
    — Each section heading must contain a specific, searchable phrase.
    — Minimum 800 words across all four sections.
    — Vary sentence length and structure — search algorithms and humans both
      penalize content that reads like it was generated from a template.
""").strip()


def build_data_summary(b: dict) -> str:
    """Construct a structured data brief for the Claude prompt."""
    lines = [
        f"ADDRESS:          {b['address']}, {b['borough']}, New York",
        f"BUILDING TYPE:    {b['bldg_type']} ({b['bldg_class']})",
        f"YEAR BUILT:       {b['year_built'] or 'Unknown'}",
    ]
    if b.get("year_alter1"):
        lines.append(f"MAJOR ALTERATION: {b['year_alter1']}")
    if b.get("year_alter2"):
        lines.append(f"2ND ALTERATION:   {b['year_alter2']}")

    bldg_area_str = f"{b['bldg_area_sf']:,} SF" if b['bldg_area_sf'] else 'Unknown'
    lot_area_str  = f"{b['lot_area_sf']:,} SF"  if b['lot_area_sf']  else 'Unknown'
    lines += [
        f"FLOORS:           {b['num_floors'] or 'Unknown'}",
        f"RESIDENTIAL UNITS:{b['units_res'] or 'Unknown'}",
        f"TOTAL UNITS:      {b['units_total'] or 'Unknown'}",
        f"BUILDING AREA:    {bldg_area_str}",
        f"LOT AREA:         {lot_area_str}",
        f"LOT TYPE:         {b['lot_type'] or 'Standard'}",
        f"ZONING:           {b['zoning'] or 'Unknown'}",
        f"BUILT FAR:        {b['far'] or 'Unknown'}",
        f"MAX FAR:          {b['max_far'] or 'Unknown'}",
    ]
    if b.get("air_rights_sf"):
        lines.append(f"UNUSED AIR RIGHTS:~{b['air_rights_sf']:,} SF")

    lines.append(f"ASSESSED VALUE:   {fmt_money(b['assess_total']) if b['assess_total'] else 'Unknown'}")
    if b.get("implied_value"):
        lines.append(f"IMPLIED MKT VALUE:~{fmt_money(b['implied_value'])} (assessed ÷ 0.45)")

    if b.get("space"):
        for label, sf in b["space"].items():
            lines.append(f"  {label + ' Area:':<20}{sf:,} SF")

    if b.get("landmark"):
        lines.append(f"LANDMARK:         {b['landmark']}")
    if b.get("hist_dist"):
        lines.append(f"HISTORIC DIST:    {b['hist_dist']}")
    if b.get("lpc"):
        lpc = b["lpc"]
        if lpc.get("architect"):
            lines.append(f"ARCHITECT (LPC):  {lpc['architect']}")
        if lpc.get("style"):
            lines.append(f"STYLE (LPC):      {lpc['style']}")
        if lpc.get("designation_date"):
            lines.append(f"LPC DESIGNATION:  {fmt_date(lpc['designation_date'])}")

    lines.append(f"RECORDED OWNER:   {b['owner'] or 'Unknown'}")

    # ACRIS
    acris = b.get("acris", {})
    if acris.get("mortgage"):
        m = acris["mortgage"]
        lines.append(
            f"MOST RECENT MTGE: {fmt_money(m['amount'])} from {m['lender']} "
            f"({fmt_date(m['date'])})"
        )
    if acris.get("last_deed"):
        d = acris["last_deed"]
        lines.append(
            f"LAST DEED RECORD: {fmt_money(d['amount'])} to {d['buyer']} "
            f"({fmt_date(d['date'])})"
        )
    if acris.get("mortgage_history"):
        lines.append("MORTGAGE HISTORY:")
        for mh in acris["mortgage_history"]:
            lines.append(f"  {fmt_date(mh['date'])}: {fmt_money(mh['amount'])} ({mh['type']})")

    # DOF Sales
    sales = b.get("sales", [])
    if sales:
        lines.append("DOF SALE RECORDS:")
        for s in sales:
            lines.append(f"  {fmt_date(s['date'])}: {fmt_money(s['price'])} — {s['class']}")

    # DOB Permits
    permits = b.get("permits", [])
    if permits:
        lines.append("RECENT DOB PERMITS:")
        for p in permits[:3]:
            lines.append(f"  {fmt_date(p['date'])}: {p['type']} / {p['work']} — {p['description'][:80]}")

    # Energy
    energy = b.get("energy", {})
    if energy:
        yr = energy.get("report_year", "")
        score = energy.get("energy_star_score")
        eui   = energy.get("source_eui")
        ghg   = energy.get("ghg_emissions")
        status = energy.get("compliance_status", "")
        if score:
            lines.append(f"ENERGY STAR SCORE: {score}/100 ({yr})")
        if eui:
            lines.append(f"SOURCE EUI:       {eui} kBtu/SF/yr")
        if ghg:
            lines.append(f"GHG EMISSIONS:    {ghg} metric tons CO₂e")
        if status:
            lines.append(f"LL84 COMPLIANCE:  {status}")

    return "\n".join(lines)


def generate_content(building: dict) -> dict:
    data_summary = build_data_summary(building)

    prompt = dedent(f"""
        Write a Light Tower Group "Building Biography" for the following NYC asset.
        Use the actual data provided — specific numbers, lender names, and dates make
        the writing authoritative and distinguish it from generic real estate content.

        ── BUILDING DATA ──
        {data_summary}

        ── INSTRUCTIONS ──
        Return ONLY a valid JSON object with the keys below.
        Section values must contain valid HTML using only <p>, <h3>, <blockquote> tags.
        Do not include <h2> tags in sections (the template renders those).
        Do not use markdown. Return only the JSON.

        {{
          "title": "WSJ-style headline. Specific tension or market argument, not a description. No colons if possible. Max 85 chars. Example register: 'The Debt Behind the Limestone' or 'What 740 Park's Capital Stack Reveals About Trophy Multifamily'.",
          "slug": "kebab-case using address and borough, e.g. 740-park-avenue-manhattan",
          "excerpt": "One sentence, max 185 chars. State the argument directly — what this building reveals about the market or the money behind it. No throat-clearing.",
          "section_monologue": "2–3 <p> paragraphs. THE LEAD + NUT GRAPH. Open with one specific concrete detail about this building — a material, a date, a transaction, a physical fact. Not a statement of theme. Then, in the second paragraph, state clearly what this piece argues about this building and why it matters now. Short sentences. Active voice. No adjectives that aren't earned.",
          "section_critique": "2–3 <p> paragraphs. Architectural analysis as reported observation, not appreciation. What does the building actually look like, how was it built, what does its construction history tell you about the era and the money behind it? If LPC data lists an architect or style, use it. Connect every architectural observation to a market or financial implication. A thick masonry wall is also a maintenance liability. A pre-war floor plate is also a rent-stabilization constraint.",
          "section_capital": "2–3 <p> paragraphs. This is the core of the piece. Use every piece of real data provided — ACRIS mortgage amounts, lender names, sale dates and prices, DOB permit activity, LL84 energy scores. Write like a reporter who pulled the records. 'City records show a $X mortgage from [Lender] filed in [Month Year].' Then analyze what it means: debt-service context, refinancing timeline, Local Law 97 exposure if energy data is present, what the implied market value suggests about equity position. Be direct about what the numbers signal — don't describe them, argue from them.",
          "section_thesis": "1–2 <p> paragraphs. Benjamin Rohr's direct, specific take on what happens next with this asset. Not a summary. Not a soft close. A position: what a smart sponsor should be thinking about, what the capital markets opportunity or risk is, and why the conventional read on this building is probably wrong or incomplete. End with one sentence that earns — without stating — that Light Tower Group is the right advisor for this asset.",
          "meta_description": "155-char SEO meta — include address, building type, year built, and Light Tower Group",
          "og_title": "Open Graph title under 62 chars",
          "schema_description": "2-sentence plain-text for schema.org markup"
        }}
    """).strip()

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


# ── HTML Rendering ─────────────────────────────────────────────────────────────

def build_sidebar_rows(b: dict) -> str:
    rows = []

    def row(label, value):
        rows.append(
            f'<div class="data-row">'
            f'<span class="data-label">{label}</span>'
            f'<span class="data-value">{value}</span>'
            f'</div>'
        )

    if b["year_built"]:    row("Year Built",         str(b["year_built"]))
    if b["num_floors"]:    row("Floors",             str(b["num_floors"]))
    if b["units_res"]:     row("Residential Units",  f"{b['units_res']:,}")
    if b["bldg_area_sf"]:  row("Building Area",      f"{b['bldg_area_sf']:,} SF")
    if b["zoning"]:        row("Zoning",             b["zoning"])
    if b["far"]:           row("Built FAR",          str(b["far"]))
    if b["air_rights_sf"]: row("Unused Air Rights",  f"~{b['air_rights_sf']:,} SF")
    if b["assess_total"]:  row("Assessed Value",     fmt_money(b["assess_total"]))
    if b["implied_value"]: row("Implied Mkt Value",  f"~{fmt_money(b['implied_value'])}")
    if b["landmark"]:      row("Landmark",           b["landmark"])
    if b["hist_dist"]:     row("Historic District",  b["hist_dist"])

    acris = b.get("acris", {})
    if acris.get("mortgage"):
        m = acris["mortgage"]
        row("Last Mortgage",  fmt_money(m["amount"]))
        row("Lender",         m["lender"])
        row("Mortgage Date",  fmt_date(m["date"]))

    sales = b.get("sales", [])
    if sales:
        row("Last Sale Price", fmt_money(sales[0]["price"]))
        row("Last Sale Date",  fmt_date(sales[0]["date"]))

    energy = b.get("energy", {})
    if energy.get("energy_star_score"):
        row("Energy Star Score", f"{energy['energy_star_score']}/100")

    return "\n          ".join(rows)


def render_html(b: dict, c: dict) -> str:
    today     = date.today().strftime("%B %d, %Y").replace(" 0", " ")
    today_iso = date.today().isoformat()
    year      = date.today().year
    url       = f"https://lighttowergroup.co/insights/{c['slug']}.html"
    rows      = build_sidebar_rows(b)

    def esc(s): return (s or "").replace('"', '\\"').replace('\n', ' ')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">

  <title>{c['og_title']} | Light Tower Group</title>
  <meta name="description" content="{c['meta_description']}">
  <meta name="robots" content="index, follow">
  <meta name="author" content="Benjamin Rohr, Light Tower Group">
  <link rel="canonical" href="{url}">

  <meta property="og:type"                content="article">
  <meta property="og:url"                 content="{url}">
  <meta property="og:title"               content="{c['og_title']}">
  <meta property="og:description"         content="{c['meta_description']}">
  <meta property="og:site_name"           content="Light Tower Group">
  <meta property="article:published_time" content="{today_iso}">
  <meta property="article:author"         content="Benjamin Rohr">
  <meta property="article:section"        content="Architecture &amp; Capital Markets">

  <link rel="alternate" type="application/rss+xml" title="Light Tower Group Insights" href="https://lighttowergroup.co/feed.xml">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400&family=Space+Grotesk:wght@300;400;500;600&display=swap" rel="stylesheet">

  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{esc(c['title'])}",
    "description": "{esc(c['schema_description'])}",
    "url": "{url}",
    "datePublished": "{today_iso}",
    "dateModified": "{today_iso}",
    "author": {{
      "@type": "Person",
      "name": "Benjamin Rohr",
      "url": "https://lighttowergroup.co/#principal"
    }},
    "publisher": {{
      "@type": "Organization",
      "name": "Light Tower Group",
      "url": "https://lighttowergroup.co",
      "logo": "https://lighttowergroup.co/favicon.svg"
    }},
    "mainEntityOfPage": "{url}",
    "about": {{
      "@type": "LandmarksOrHistoricalBuildings",
      "name": "{esc(b['address'])}, {b['borough']}",
      "address": {{
        "@type": "PostalAddress",
        "streetAddress": "{esc(b['address'])}",
        "addressLocality": "{b['borough']}",
        "addressRegion": "NY",
        "addressCountry": "US"
      }}
    }}
  }}
  </script>

  <style>
    :root {{
      --bg: #F5F4F0; --text: #121212; --accent: #C5A059; --accent-hover: #D4AF6B;
      --line: rgba(0,0,0,0.06); --line-strong: rgba(0,0,0,0.12);
      --white: #ffffff; --dark: #0E0E0E; --mid: #555555;
      --font-display: 'Playfair Display', serif;
      --font-body: 'Space Grotesk', sans-serif;
      --container: 1200px; --nav-h: 64px;
    }}
    *, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{ background: var(--bg); color: var(--text); font-family: var(--font-body); font-size: 16px; line-height: 1.6; -webkit-font-smoothing: antialiased; }}
    a {{ text-decoration: none; color: inherit; transition: all 0.3s ease; }}
    img {{ max-width: 100%; display: block; }}

    .container {{ max-width: var(--container); margin: 0 auto; padding: 0 5rem; }}
    @media (max-width: 1280px) {{ .container {{ padding: 0 4rem; }} }}
    @media (max-width: 1024px) {{ .container {{ padding: 0 3rem; }} }}
    @media (max-width: 768px)  {{ .container {{ padding: 0 1.75rem; }} }}
    @media (max-width: 480px)  {{ .container {{ padding: 0 1.5rem; }} }}

    .site-nav {{ position: sticky; top: 0; z-index: 100; background: rgba(245,244,240,0.96); backdrop-filter: blur(14px); border-bottom: 1px solid var(--line-strong); height: var(--nav-h); }}
    .nav-inner {{ max-width: var(--container); margin: 0 auto; padding: 0 5rem; height: 100%; display: flex; justify-content: space-between; align-items: center; }}
    @media (max-width: 1280px) {{ .nav-inner {{ padding: 0 4rem; }} }}
    @media (max-width: 768px)  {{ .nav-inner {{ padding: 0 1.75rem; }} }}
    .nav-logo {{ font-family: var(--font-body); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.22em; font-weight: 600; }}
    .nav-links {{ display: flex; gap: 2.5rem; align-items: center; }}
    .nav-links a {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.15em; color: #888; font-weight: 500; }}
    .nav-links a:hover {{ color: var(--text); }}
    .nav-cta {{ background: var(--text) !important; color: var(--white) !important; padding: 0.6rem 1.4rem; font-size: 0.7rem !important; }}
    .nav-cta:hover {{ background: var(--accent) !important; }}
    @media (max-width: 860px) {{ .nav-hide {{ display: none; }} }}

    .post-header {{ padding-top: 5rem; padding-bottom: 4rem; border-bottom: 1px solid var(--line); }}
    .post-back {{ display: inline-flex; align-items: center; gap: 0.5rem; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.18em; color: #888; margin-bottom: 3rem; transition: color 0.2s; }}
    .post-back:hover {{ color: var(--accent); }}
    .post-category {{ display: inline-block; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.2em; color: var(--accent); font-weight: 600; margin-bottom: 1.5rem; }}
    .post-title {{ font-family: var(--font-display); font-size: clamp(2rem, 4.5vw, 3.8rem); font-weight: 400; line-height: 1.12; max-width: 820px; margin-bottom: 2rem; }}
    .post-meta {{ display: flex; gap: 2.5rem; align-items: center; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.14em; color: #888; flex-wrap: wrap; }}
    .post-meta-sep {{ width: 24px; height: 1px; background: var(--accent); display: block; }}

    .article-wrap {{ display: grid; grid-template-columns: 1fr 300px; gap: 5rem; align-items: start; padding: 4rem 0 5rem; }}
    @media (max-width: 1024px) {{ .article-wrap {{ grid-template-columns: 1fr; gap: 3rem; }} }}

    .post-body h2 {{ font-family: var(--font-display); font-size: clamp(1.4rem, 2.5vw, 1.9rem); font-weight: 400; margin: 3rem 0 1.25rem; line-height: 1.25; }}
    .post-body h3 {{ font-family: var(--font-display); font-size: 1.2rem; font-weight: 400; margin: 2rem 0 0.75rem; }}
    .post-body p {{ font-size: 1.05rem; line-height: 1.88; color: #3a3a3a; margin-bottom: 1.5rem; }}
    .post-body blockquote {{ border-left: 3px solid var(--accent); padding-left: 2rem; margin: 2.5rem 0; }}
    .post-body blockquote p {{ font-family: var(--font-display); font-size: 1.3rem; font-style: italic; color: var(--text); line-height: 1.55; }}
    .section-divider {{ border: none; border-top: 1px solid var(--line); margin: 3rem 0; }}

    .asset-sidebar {{ position: sticky; top: calc(var(--nav-h) + 2rem); }}
    @media (max-width: 1024px) {{ .asset-sidebar {{ position: static; }} }}

    .data-card {{ background: var(--dark); color: var(--white); padding: 2rem 2rem 1.5rem; }}
    .data-card-label {{ font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.22em; color: var(--accent); font-weight: 600; margin-bottom: 1rem; display: block; }}
    .data-card-address {{ font-family: var(--font-display); font-size: 0.95rem; color: rgba(255,255,255,0.85); margin-bottom: 1.5rem; line-height: 1.35; }}
    .data-row {{ display: flex; justify-content: space-between; align-items: baseline; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.06); gap: 0.75rem; }}
    .data-row:last-child {{ border-bottom: none; }}
    .data-label {{ font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255,255,255,0.35); flex-shrink: 0; }}
    .data-value {{ font-size: 0.73rem; font-weight: 500; color: rgba(255,255,255,0.82); text-align: right; }}
    .data-source {{ font-size: 0.58rem; color: rgba(255,255,255,0.2); text-align: right; margin-top: 1rem; }}

    .data-cta {{ margin-top: 1.5rem; display: block; background: var(--accent); color: var(--white); padding: 0.85rem 1.25rem; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.18em; font-weight: 600; text-align: center; transition: background 0.2s; }}
    .data-cta:hover {{ background: var(--accent-hover); color: var(--white); }}

    .post-cta {{ background: var(--dark); color: var(--white); padding: 6rem 0; }}
    .post-cta-inner {{ max-width: 580px; margin: 0 auto; text-align: center; }}
    .post-cta-eyebrow {{ font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.22em; color: var(--accent); font-weight: 600; display: block; margin-bottom: 1.5rem; }}
    .post-cta-headline {{ font-family: var(--font-display); font-size: clamp(1.8rem, 3.5vw, 2.8rem); font-weight: 400; line-height: 1.15; margin-bottom: 1.25rem; }}
    .post-cta-sub {{ font-size: 0.95rem; color: rgba(255,255,255,0.5); line-height: 1.72; margin-bottom: 2.5rem; }}
    .btn-gold {{ display: inline-block; background: var(--accent); color: var(--white); padding: 1rem 2.5rem; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.2em; font-weight: 600; transition: background 0.3s; }}
    .btn-gold:hover {{ background: var(--accent-hover); color: var(--white); }}

    .footer {{ background: var(--dark); color: var(--white); padding: 5rem 0 2.5rem; border-top: 1px solid rgba(255,255,255,0.05); }}
    .footer-top {{ display: grid; grid-template-columns: 1.6fr 1fr 1fr; gap: 4rem; padding-bottom: 3rem; border-bottom: 1px solid rgba(255,255,255,0.07); }}
    @media (max-width: 860px) {{ .footer-top {{ grid-template-columns: 1fr; gap: 2.5rem; }} }}
    .footer-brand-name {{ font-family: var(--font-display); font-size: 1.9rem; font-weight: 400; color: rgba(255,255,255,0.88); margin-bottom: 1.25rem; }}
    .footer-brand p {{ font-size: 0.88rem; color: rgba(255,255,255,0.38); line-height: 1.78; max-width: 300px; }}
    .footer-col-label {{ font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.2em; color: #444; margin-bottom: 1.5rem; display: block; }}
    .footer-link {{ display: block; font-size: 0.88rem; color: rgba(255,255,255,0.42); margin-bottom: 0.7rem; transition: color 0.2s; }}
    .footer-link:hover {{ color: var(--accent); }}
    .footer-bottom {{ display: flex; justify-content: space-between; align-items: flex-start; padding-top: 2.5rem; gap: 2rem; flex-wrap: wrap; }}
    .copyright {{ font-size: 0.62rem; color: #3a3a3a; text-transform: uppercase; letter-spacing: 0.1em; }}
    .footer-disclaimer {{ font-size: 0.62rem; color: #333; max-width: 480px; line-height: 1.65; text-align: right; }}
    @media (max-width: 860px) {{ .footer-disclaimer {{ text-align: left; }} }}
    /* ── Share bar ── */
    .share-bar {{ display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; margin: 1.25rem 0 0.5rem; }}
    .share-label {{ font-size: 0.68rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text-muted); margin-right: 0.2rem; font-family: var(--font-ui); }}
    .share-btn {{ font-family: var(--font-ui); font-size: 0.72rem; letter-spacing: 0.04em; padding: 0.38rem 0.9rem; border-radius: 2px; cursor: pointer; text-decoration: none; border: 1px solid; transition: all 0.18s; background: transparent; }}
    .share-li  {{ color: #5b9bd5; border-color: rgba(91,155,213,0.4); }}
    .share-li:hover  {{ background: rgba(91,155,213,0.1); color: #7fb3e8; }}
    .share-tw  {{ color: rgba(255,255,255,0.7); border-color: rgba(255,255,255,0.2); }}
    .share-tw:hover  {{ background: rgba(255,255,255,0.06); }}
    .share-copy {{ color: var(--accent); border-color: rgba(201,168,76,0.35); }}
    .share-copy:hover {{ background: rgba(201,168,76,0.08); }}
  </style>
</head>

<body>

  <nav class="site-nav" role="navigation" aria-label="Main navigation">
    <div class="nav-inner">
      <a href="/" class="nav-logo">Light Tower Group</a>
      <div class="nav-links">
        <a href="/#practice"   class="nav-hide">The Practice</a>
        <a href="/#advantage"  class="nav-hide">The Advantage</a>
        <a href="/#leadership" class="nav-hide">Leadership</a>
        <a href="/insights.html" class="nav-hide">Insights</a>
        <a href="/#contact"    class="nav-hide">Contact</a>
        <a href="/#contact" class="nav-cta">Initiate Mandate</a>
      </div>
    </div>
  </nav>

  <main>
    <div class="post-header container">
      <a href="/insights.html" class="post-back">&#8592; Back to Insights</a>
      <span class="post-category">Architecture &amp; Capital Markets</span>
      <h1 class="post-title">{c['title']}</h1>
      <div class="post-meta">
        <span>{b['address']}, {b['borough']}</span>
        <span class="post-meta-sep"></span>
        <span>{today}</span>
        <span class="post-meta-sep"></span>
        <span>Benjamin Rohr</span>
        <span class="post-meta-sep"></span>
        <span>8 min read</span>
      </div>
      <div class="share-bar">
        <span class="share-label">Share</span>
        <a href="https://www.linkedin.com/sharing/share-offsite/?url={requests.utils.quote(url, safe='')}"
           target="_blank" rel="noopener" class="share-btn share-li">LinkedIn</a>
        <a href="https://twitter.com/intent/tweet?url={requests.utils.quote(url, safe='')}&text={requests.utils.quote(c['title'][:100], safe='')}"
           target="_blank" rel="noopener" class="share-btn share-tw">X / Twitter</a>
        <button class="share-btn share-copy"
                onclick="navigator.clipboard.writeText('{url}').then(function(){{this.textContent='Copied!'}}.bind(this))">Copy Link</button>
      </div>
    </div>

    <div class="container">
      <div class="article-wrap">

        <article class="post-body" itemscope itemtype="https://schema.org/Article">
          <h2>The Monologue</h2>
          {c['section_monologue']}
          <hr class="section-divider">
          <h2>The Architecture of {b['address']}</h2>
          {c['section_critique']}
          <hr class="section-divider">
          <h2>The Capital Stack: {b['borough']} {b['bldg_type'].split()[0]} Markets, 2025–2026</h2>
          {c['section_capital']}
          <hr class="section-divider">
          <h2>The Light Tower Thesis</h2>
          {c['section_thesis']}
        </article>

        <aside class="asset-sidebar">
          <div class="data-card">
            <span class="data-card-label">Asset Data Profile</span>
            <div class="data-card-address">{b['address']}<br>{b['borough']}, New York</div>
            {rows}
            <p class="data-source">Sources: NYC PLUTO · ACRIS · DOF · LL84</p>
          </div>
          <a href="/#contact" class="data-cta">Discuss This Asset &#8594;</a>
        </aside>

      </div>
    </div>

    <div class="post-cta">
      <div class="post-cta-inner">
        <span class="post-cta-eyebrow">Light Tower Group</span>
        <h2 class="post-cta-headline">This building has a story.<br>Let&rsquo;s write the next chapter.</h2>
        <p class="post-cta-sub">If you own, are acquiring, or are considering a position in a New York asset, we bring institutional capital precision to every mandate — from the first conversation to funding.</p>
        <a href="/#contact" class="btn-gold">Initiate a Mandate</a>
      </div>
    </div>
  </main>

  <footer class="footer" role="contentinfo">
    <div class="container">
      <div class="footer-top">
        <div class="footer-brand">
          <div class="footer-brand-name">Light Tower Group</div>
          <p>Institutional capital advisory for complex commercial real estate mandates. Debt placement, equity structuring, and investment advisory nationwide.</p>
        </div>
        <div>
          <span class="footer-col-label">Navigate</span>
          <a href="/#practice"    class="footer-link">The Practice</a>
          <a href="/#advantage"   class="footer-link">The Advantage</a>
          <a href="/#leadership"  class="footer-link">Leadership</a>
          <a href="/insights.html" class="footer-link">Insights</a>
          <a href="/#contact"     class="footer-link">Contact</a>
        </div>
        <div>
          <span class="footer-col-label">Contact</span>
          <a href="mailto:ben@lighttowergroup.co" class="footer-link">ben@lighttowergroup.co</a>
          <a href="tel:+13475540093"              class="footer-link">+1 347 554 0093</a>
        </div>
      </div>
      <div class="footer-bottom">
        <span class="copyright">&copy; {year} Light Tower Group. All rights reserved.</span>
        <p class="footer-disclaimer">Light Tower Group is a capital advisory firm. Nothing on this page constitutes investment advice or a solicitation to buy or sell any security. Data sourced from NYC public records including PLUTO, ACRIS, and DOF. Implied valuations are estimates only.</p>
      </div>
    </div>
  </footer>

</body>
</html>"""


# ── Manifest Update ────────────────────────────────────────────────────────────

def update_manifest(c: dict, b: dict) -> None:
    manifest = json.loads(INSIGHTS_JSON.read_text()) if INSIGHTS_JSON.exists() else []
    manifest = [e for e in manifest if e.get("slug") != c["slug"]]
    manifest.insert(0, {
        "slug":     c["slug"],
        "title":    c["title"],
        "date":     date.today().isoformat(),
        "category": "Architecture & Capital Markets",
        "excerpt":  c["excerpt"],
        "readTime": 8,
    })
    INSIGHTS_JSON.write_text(json.dumps(manifest, indent=2))
    print(f"  [OK]Updated insights.json  ({len(manifest)} total entries)")


# ── Entry Point ────────────────────────────────────────────────────────────────

def generate(address: str) -> None:
    print(f"\n>> {address}")

    print("  Fetching PLUTO data...")
    raw      = fetch_pluto(address)
    building = parse_pluto(raw)
    print(
        f"  [OK]{building['address']}, {building['borough']}  |  "
        f"Built {building['year_built'] or '?'}  |  "
        f"{building['num_floors'] or '?'} floors  |  "
        f"{building['units_res'] or '?'} units  |  "
        f"BBL {building['bbl']}"
    )

    building = enrich(building)

    print("  Generating editorial content (Claude)...")
    content = generate_content(building)
    print(f"  [OK]Title: {content['title']}")

    INSIGHTS_DIR.mkdir(exist_ok=True)
    out = INSIGHTS_DIR / f"{content['slug']}.html"
    out.write_text(render_html(building, content), encoding="utf-8")
    print(f"  [OK]Saved: {out.relative_to(SITE_ROOT)}")

    update_manifest(content, building)
    print(f"  >> /insights/{content['slug']}.html\n")


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Light Tower Group building biography.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python generate_building.py "740 Park Avenue"\n'
            "  python generate_building.py --batch buildings.txt"
        ),
    )
    parser.add_argument("address", nargs="?", help="NYC street address")
    parser.add_argument("--batch", metavar="FILE",
                        help="Text file with one address per line")
    args = parser.parse_args()

    if args.batch:
        addresses = Path(args.batch).read_text(encoding="utf-8").strip().splitlines()
        total = sum(1 for a in addresses if a.strip() and not a.startswith("#"))
        print(f"Batch mode: {total} addresses\n")
        for addr in addresses:
            addr = addr.strip()
            if not addr or addr.startswith("#"):
                continue
            try:
                generate(addr)
            except Exception as e:
                print(f"  ✗ FAILED ({addr}): {e}\n")
    elif args.address:
        generate(args.address)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
