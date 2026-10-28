"""NYC >$10M Transaction Desk — 60-Book Literary Journalism & Anti-AI Feature Engine.

Generates and verifies institutional NYC >$10M transaction stories grounded in
the deterministic Verified Deal Ammo Sheet (`economics.py`), enforces the
Forensic Anti-AI / 100% Human Prose Framework (`human_style_gate.py`), dates
each story on its closing date, and publishes into `site_renderer.py`.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .economics import build_ammo_sheet, compute_economics, evaluate_eligibility
from .models import DealEconomics, NycTransactionDossier

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from human_style_gate import scrub_ai_tells  # noqa: E402

NYC_DESK_PROMPT_VERSION = "nyc-desk-2.0-literary-60books"

NYC_DESK_SYSTEM_PROMPT = """You are the Senior NYC Real Estate & Capital Markets Feature Writer for Light Tower Group, writing under the byline of Principal Benjamin Rohr.

Your mandate is to write the single best, smoothest, most engaging story on the street for every New York City commercial and multifamily real estate transaction above $10,000,000.

THE 60-BOOK LITERARY JOURNALISM & SENTENCE CRAFT OPERATING SYSTEM:
1. SEPARATE THE DEAL SHEET FROM THE STORY (Zinsser / Pinker / Dreyer):
   - The reader already sees a "Verified ACRIS & PLUTO Deal Sheet" box right above your story with the raw BBL, ACRIS Doc ID, zoning code, exact comma-formatted dollars, and LLC entity names.
   - NEVER dump raw BBL strings, ACRIS Document IDs, ISO dates ("2026-03-22"), dual-number strings ("$46,200,000 ($46.2M)"), slash notation ("$400/GSF"), or "via [Entity] LLC" legalese into your prose paragraphs.
   - In prose, write human-scale numbers and dates: "$46.2 million", "March 22", "$400 a square foot", "$350,000 a door", "65 percent".

2. THE 3-GEAR CAMERA LENS (Blundell's WSJ Feature Guide / McPhee / Tom Wolfe / Talese):
   - Paragraph 1 (The Scene & The Move): Open on a specific moment in time, street corner, physical detail, or dynasty contrast involving the real human principals (e.g., Shibber Khan, Craig Deitelzweig, Joe Sitt, Rob Speyer, KKR).
   - Paragraph 2 (The Nut Graf): Pull back and explain why the price per foot or per door matters against replacement cost or the prior sale basis.
   - Bespoke Subheading #1 (<h2>...</h2>): Use a custom, story-driven magazine subheading (never generic labels like "The Deal & The Players" or "The Asset & Street Reality"). Unpack the debt and equity stack like Michael Lewis—why the lender and structure (CEMA tax shield, 10-year fixed agency, life-company balance sheet, debt-fund bridge) made the deal pencil.
   - Closing Subheading (<h2>From Our Desk</h2>): Written in warm, sharp, conversational first person ("When we look at...", "On our desk..."), giving NYC sponsors and lenders a memorable takeaway that ends on a quotable kicker line.

3. SENTENCE MUSICALITY & THE 12-POINT ANTI-AI CONTRACT (Provost / Tufte / Landon / Fish / Forsyth):
   - High burstiness: mix 6-to-10-word punch sentences with 22-to-30-word right-branching narrative sentences.
   - Max 2 numbers per sentence so each figure lands with weight.
   - Never open with "In a market where..." or "Amidst...".
   - Never tack weak participial tails onto sentences (", illustrating...", ", underscoring...", ", highlighting...", ", marking a...").
   - Never use AI clichés ("textbook readout", "crystallizes liquidity", "testament to", "First... Second...").

Output valid JSON with keys: "title", "subtitle", "meta_description", "body_html", "tags"."""


def _human_date(iso_date: str) -> str:
    try:
        dt = datetime.strptime(str(iso_date)[:10], "%Y-%m-%d")
        return dt.strftime("%B %d, %Y").replace(" 0", " ")
    except ValueError:
        return str(iso_date)


def _human_month_year(iso_date: str) -> str:
    try:
        dt = datetime.strptime(str(iso_date)[:10], "%Y-%m-%d")
        return dt.strftime("%B %Y")
    except ValueError:
        return str(iso_date)[:4]


def _human_millions(amount: float | None) -> str:
    if not amount or amount <= 0:
        return ""
    val = amount / 1_000_000.0
    if abs(val - round(val)) < 0.005:
        return f"${int(round(val)):,} million"
    if abs(val * 10 - round(val * 10)) < 0.05:
        return f"${val:,.1f} million"
    return f"${val:,.2f} million"


def build_deal_sheet_data_points(dossier: NycTransactionDossier, econ: DealEconomics) -> list[dict[str, str]]:
    """Build up to 6 structured data points for the top-of-article Deal Sheet."""
    prop = dossier.property_info
    points: list[dict[str, str]] = [
        {
            "value": f"${econ.sale_price_usd:,.0f}",
            "label": f"Sale Price · {prop.neighborhood}, {prop.borough}",
        }
    ]

    if econ.price_per_gsf and econ.price_per_unit and prop.residential_units > 0:
        points.append(
            {
                "value": f"{econ.price_per_gsf_display}",
                "label": f"{econ.price_per_unit_display} ({prop.residential_units} Res Units)",
            }
        )
    elif econ.price_per_gsf:
        points.append(
            {
                "value": f"{econ.price_per_gsf_display}",
                "label": f"{prop.gross_sqft:,} GSF · {prop.stories} Stories",
            }
        )

    if econ.acquisition_debt_usd and econ.acquisition_debt_usd > 0:
        ltv_tag = f" · {econ.implied_ltv_display} LTV" if econ.implied_ltv_display else ""
        points.append(
            {
                "value": f"${econ.acquisition_debt_usd:,.0f}",
                "label": f"{econ.debt_instrument_label}{ltv_tag} · {econ.primary_lender}",
            }
        )
    else:
        points.append(
            {
                "value": "100% Cash",
                "label": "Unencumbered All-Cash Closing · ACRIS Verified",
            }
        )

    if econ.implied_equity_usd and econ.implied_equity_usd > 0:
        points.append(
            {
                "value": f"${econ.implied_equity_usd:,.0f}",
                "label": f"Implied Equity · {int(dossier.interest_conveyed_pct)}% Fee Simple",
            }
        )
    else:
        points.append(
            {
                "value": f"${econ.sale_price_usd:,.0f}",
                "label": f"Implied Equity · {int(dossier.interest_conveyed_pct)}% Fee Simple",
            }
        )

    if econ.prior_sale_change_display and econ.prior_sale_price_usd:
        points.append(
            {
                "value": econ.prior_sale_change_display.split("(")[0].strip(),
                "label": f"Prior Sale: ${econ.prior_sale_price_usd:,.0f} ({_human_date(econ.prior_sale_date)})",
            }
        )
    else:
        points.append(
            {
                "value": f"{prop.lot_sqft:,} SF Lot",
                "label": f"Built {prop.year_built or 'N/A'} · Closed {_human_date(dossier.closing_date)}",
            }
        )

    points.append(
        {
            "value": f"BBL {prop.bbl}",
            "label": f"Class {prop.building_class} · {prop.zoning or 'NYC PLUTO'}",
        }
    )

    return points[:6]


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)[:85].rstrip("-")


def _clean_entity_name(raw_name: str) -> str:
    return re.sub(r"\s*(?:\(via\s+[^)]+\)|via\s+.*)$", "", raw_name or "", flags=re.IGNORECASE).strip()


def _extract_note_parts(dossier: NycTransactionDossier) -> dict[str, str]:
    parts: dict[str, str] = {
        "scene_hook": "",
        "street_context": "",
        "subhead_1": "Inside the Capital Stack",
        "desk_kicker": "",
        "title": "",
        "subtitle": "",
        "p2": "",
        "p3": "",
        "p4": "",
        "p5": "",
    }
    plain_notes: list[str] = []

    for n in dossier.notes:
        if n.startswith("SUBHEAD::"):
            parts["subhead_1"] = n.split("SUBHEAD::", 1)[1].strip()
        elif n.startswith("KICKER::"):
            parts["desk_kicker"] = n.split("KICKER::", 1)[1].strip()
        elif n.startswith("TITLE::"):
            parts["title"] = n.split("TITLE::", 1)[1].strip()
        elif n.startswith("SUBTITLE::"):
            parts["subtitle"] = n.split("SUBTITLE::", 1)[1].strip()
        elif n.startswith("P2::"):
            parts["p2"] = n.split("P2::", 1)[1].strip()
        elif n.startswith("P3::"):
            parts["p3"] = n.split("P3::", 1)[1].strip()
        elif n.startswith("P4::"):
            parts["p4"] = n.split("P4::", 1)[1].strip()
        elif n.startswith("P5::"):
            parts["p5"] = n.split("P5::", 1)[1].strip()
        else:
            plain_notes.append(n.strip())

    if plain_notes:
        parts["scene_hook"] = plain_notes[0]
    if len(plain_notes) > 1:
        parts["street_context"] = plain_notes[1]
    return parts


def _build_writer_user_prompt(dossier: NycTransactionDossier) -> str:
    ammo = build_ammo_sheet(dossier)
    parts = _extract_note_parts(dossier)
    return f"""Write a flagship NYC >$10M Transaction Desk feature story in the style of a Wall Street Journal Page One feature × New York Magazine × The Real Deal × Commercial Observer's Finance Desk.

=== VERIFIED DEAL AMMO SHEET (JSON) ===
{json.dumps(ammo, indent=2, ensure_ascii=False)}
=======================================

=== NARRATIVE SCENE & CONTEXT ===
- Scene Hook: {parts["scene_hook"]}
- Street & Deal Context: {parts["street_context"]}
- Suggested Feature Subheading: {parts["subhead_1"]}
- Desk Takeaway Thesis: {parts["desk_kicker"]}
=================================

REQUIREMENTS:
1. "title": A magnetic, magazine-grade headline (under 105 characters) that names the principals/buyer, the address or neighborhood, the dollar figure, and the story angle.
2. "subtitle": A crisp 1-sentence deck (20–35 words) highlighting the human stakes, per-foot/per-door basis, and lender.
3. "meta_description": SEO meta description (135–160 characters) naming the address, neighborhood, sale price, buyer, and lender.
4. "body_html": 450–700 words of smooth, human-crafted HTML using ONLY `<p>`, `<h2>`, `<strong>`, and `<em>` tags:
   - Opening Lede (2 `<p>` paragraphs, no heading): Scene-setting hook + Nut Graf on what the price per foot/door means.
   - `<h2>{parts["subhead_1"]}</h2>` (2 `<p>` paragraphs): Unpack the debt, LTV, CEMA/agency/life-co/bridge structure, and seller-vs.-buyer math without repeating the Deal Sheet verbatim.
   - `<h2>From Our Desk</h2>` (1–2 `<p>` paragraphs): Ben Rohr's conversational, first-person placement-desk takeaway ending with a sharp kicker line.
   - DO NOT put raw BBL codes, ACRIS Doc IDs, ISO dates (YYYY-MM-DD), or "via ... LLC" inside `body_html`.
5. "tags": Array of 5–6 specific tags (borough, neighborhood, asset class, lender, "NYC $10M+ Deals").

Return ONLY a valid JSON object."""


def render_literary_story(dossier: NycTransactionDossier, econ: DealEconomics) -> dict[str, Any]:
    """Craft a smooth, magazine-grade WSJ/NYT/TRD/CO feature story using the 60-Book & Anti-AI framework."""
    prop = dossier.property_info
    parts = _extract_note_parts(dossier)
    scene_hook = parts["scene_hook"]
    street_context = parts["street_context"]
    subhead_1 = parts["subhead_1"]
    desk_kicker = parts["desk_kicker"]

    buyer_clean = _clean_entity_name(dossier.buyer)
    seller_clean = _clean_entity_name(dossier.seller)
    m = dossier.mortgages[0] if dossier.mortgages else None
    lender_clean = (econ.primary_lender or "balance-sheet capital").split("(")[0].strip()

    price_prose = _human_millions(econ.sale_price_usd)
    price_short = econ.sale_price_display or price_prose
    close_human = _human_date(dossier.closing_date)
    ppsf_int = int(round(econ.price_per_gsf)) if econ.price_per_gsf else 0
    ppsf_prose = f"${ppsf_int:,} a square foot" if ppsf_int else "an institutional basis"
    v_idx = sum(ord(c) for c in dossier.transaction_id)

    # 1. Headline & Subtitle
    if parts["title"]:
        title = parts["title"]
    elif econ.prior_sale_change_pct is not None and econ.prior_sale_price_usd:
        delta_abs = abs(econ.prior_sale_change_pct)
        if econ.prior_sale_change_pct <= -15.0:
            title = f"{buyer_clean} Snaps Up {prop.address} for {price_short} in a {int(round(delta_abs))}% {prop.neighborhood} Basis Reset"
        elif econ.prior_sale_change_pct < 0:
            title = f"{buyer_clean} Takes Down {prop.neighborhood}'s {prop.address} for {price_short} at ${ppsf_int:,} a Foot"
        else:
            up_titles = [
                f"Why {buyer_clean} Just Paid {price_prose} for {prop.address} in {prop.neighborhood}",
                f"{buyer_clean} Drops {price_prose} on {prop.neighborhood}'s {prop.address} at ${ppsf_int:,} a Foot",
                f"Inside {buyer_clean}'s {price_prose} Takeout of {prop.address} in {prop.neighborhood}",
            ]
            title = up_titles[v_idx % len(up_titles)]
    else:
        fresh_titles = [
            f"{buyer_clean} Closes {price_prose} Purchase of {prop.address} in {prop.neighborhood}",
            f"Why {buyer_clean} Wired {price_prose} for {prop.address} in {prop.neighborhood}",
            f"{buyer_clean} Takes Down {prop.address} in {prop.neighborhood} for {price_prose}",
        ]
        title = fresh_titles[v_idx % len(fresh_titles)]

    if parts["subtitle"]:
        subtitle = parts["subtitle"]
    elif econ.acquisition_debt_usd and econ.acquisition_debt_usd > 0:
        debt_prose = _human_millions(econ.acquisition_debt_usd)
        sub_variants = [
            f"Backed by a {debt_prose} loan from {lender_clean}, the {prop.neighborhood} closing clears at {ppsf_prose} across {prop.gross_sqft:,} square feet.",
            f"With {lender_clean} supplying {debt_prose} in acquisition financing, {buyer_clean} locks in {prop.address} at {ppsf_prose}.",
            f"The {price_prose} deed transfer pairs a {ppsf_prose} basis with {debt_prose} in senior debt from {lender_clean}.",
        ]
        subtitle = sub_variants[v_idx % len(sub_variants)]
    else:
        sub_cash_variants = [
            f"Closed without a dollar of recorded property-level debt, the {price_prose} trade sets a {ppsf_prose} benchmark in {prop.neighborhood}.",
            f"Writing an unencumbered {price_prose} check, {buyer_clean} takes control of {prop.gross_sqft:,} square feet at {ppsf_prose}.",
            f"The all-cash {price_prose} acquisition prices {prop.address} at {ppsf_prose} and highlights the power of unlevered certainty.",
        ]
        subtitle = sub_cash_variants[v_idx % len(sub_cash_variants)]

    # 2. Paragraph 1: Scene-setting Lede (Blundell / Wolfe / Talese — no redundant summary tail)
    if scene_hook and street_context:
        p1 = f"<p>{scene_hook} {street_context}</p>"
    else:
        p1 = (
            f"<p>On {close_human}, <strong>{buyer_clean}</strong> closed on the {prop.stories}-story "
            f"{prop.asset_type} at <strong>{prop.address}</strong> in {prop.neighborhood}, {prop.borough}, "
            f"paying <strong>{price_prose}</strong> to <strong>{seller_clean}</strong>.</p>"
        )

    # 3. Paragraph 2: The Nut Graf (McPhee / Didion benchmark translation)
    unit_clause = ""
    if econ.price_per_unit and prop.residential_units > 1:
        unit_clause = f" (or <strong>${int(round(econ.price_per_unit)):,} per apartment</strong> across {prop.residential_units} residential units)"

    cap_clause = (
        f" Based on underwritten net operating income, the trade clears at a <strong>{econ.cap_rate_pct:.2f} percent going-in cap rate</strong>."
        if econ.cap_rate_pct
        else ""
    )

    if parts["p2"]:
        p2 = f"<p>{parts['p2']}</p>"
    elif econ.prior_sale_change_pct is not None and econ.prior_sale_price_usd:
        prior_prose = _human_millions(econ.prior_sale_price_usd)
        prior_month_yr = _human_month_year(econ.prior_sale_date)
        delta_abs = abs(econ.prior_sale_change_pct)
        if econ.prior_sale_change_pct < 0:
            down_p2 = [
                (
                    f"<p>Strip away the headline price and the real story is the basis reset. "
                    f"The {prop.gross_sqft:,}-square-foot property last traded in {prior_month_yr} for {prior_prose}. "
                    f"Stepping in at <strong>{ppsf_prose}</strong>{unit_clause} shaves <strong>{delta_abs:.1f} percent</strong> off that prior valuation, "
                    f"handing {buyer_clean} a margin of safety that simply did not exist during the zero-rate era.{cap_clause}</p>"
                ),
                (
                    f"<p>For {buyer_clean}, the math comes down to entry basis. "
                    f"Compared with the {prior_prose} deed recorded in {prior_month_yr}, this {price_prose} closing reprices the {prop.gross_sqft:,}-square-foot footprint "
                    f"down by <strong>{delta_abs:.1f} percent</strong> to <strong>{ppsf_prose}</strong>{unit_clause}—a reset low enough to make new leasing pencil immediately.{cap_clause}</p>"
                ),
            ]
            p2 = down_p2[v_idx % len(down_p2)]
        else:
            up_p2 = [
                (
                    f"<p>The per-foot math explains why {seller_clean} chose this moment to harvest gains—and why {buyer_clean} was willing to pay up. "
                    f"At <strong>{ppsf_prose}</strong>{unit_clause} across {prop.gross_sqft:,} square feet, the closing price represents a "
                    f"<strong>{delta_abs:.1f} percent appreciation</strong> over the {prior_prose} trade recorded in {prior_month_yr}.{cap_clause}</p>"
                ),
                (
                    f"<p>Measure the deal by replacement cost and the logic snaps into focus. "
                    f"The {price_prose} purchase equates to <strong>{ppsf_prose}</strong>{unit_clause} across {prop.gross_sqft:,} square feet, "
                    f"climbing <strong>{delta_abs:.1f} percent</strong> above the {prior_prose} price tag recorded in {prior_month_yr} while still clearing below what it costs to assemble, carry, and build comparable {prop.neighborhood} product today.{cap_clause}</p>"
                ),
                (
                    f"<p>In {prop.neighborhood}, scale and zoning scarcity drive the tape. "
                    f"Spanning {prop.gross_sqft:,} square feet on a {prop.lot_sqft:,}-square-foot lot zoned {prop.zoning}, "
                    f"the property's <strong>{ppsf_prose}</strong> clearing basis{unit_clause} delivers a <strong>{delta_abs:.1f} percent gain</strong> over its {prior_month_yr} sale at {prior_prose}.{cap_clause}</p>"
                ),
            ]
            p2 = up_p2[v_idx % len(up_p2)]
    else:
        fresh_p2 = [
            (
                f"<p>Across the property's {prop.gross_sqft:,} square feet on a {prop.lot_sqft:,}-square-foot {prop.zoning} lot, "
                f"the {price_prose} trade establishes a <strong>{ppsf_prose}</strong> clearing mark{unit_clause} for {prop.neighborhood} {prop.asset_type} product.{cap_clause}</p>"
            ),
            (
                f"<p>Run the numbers across {prop.gross_sqft:,} square feet and the buyer's thesis comes into view. "
                f"At <strong>{ppsf_prose}</strong>{unit_clause} on a {prop.lot_sqft:,}-square-foot parcel zoned {prop.zoning}, "
                f"{buyer_clean} is locking in irreplaceable {prop.neighborhood} brick well below new-construction replacement cost.{cap_clause}</p>"
            ),
            (
                f"<p>Every {prop.borough} submarket has a number where institutional buyers stop watching from the sidelines and start wiring earnest money. "
                f"In {prop.neighborhood}, that clearing level is <strong>{ppsf_prose}</strong>{unit_clause} across {prop.gross_sqft:,} square feet under {prop.zoning} zoning.{cap_clause}</p>"
            ),
        ]
        p2 = fresh_p2[v_idx % len(fresh_p2)]

    # 4. Section 2: Bespoke Capital Stack & Plumbing X-Ray (Michael Lewis / Connie Bruck)
    is_cema = bool(m and ("CEMA" in m.instrument_type.upper() or "AGMT" in m.instrument_type.upper() or "M&CON" in m.instrument_type.upper()))
    if parts["p3"] and parts["p4"]:
        p3 = f"<p>{parts['p3']}</p>"
        p4 = f"<p>{parts['p4']}</p>"
    elif econ.acquisition_debt_usd and econ.acquisition_debt_usd > 0 and m:
        debt_prose = _human_millions(econ.acquisition_debt_usd)
        eq_prose = _human_millions(econ.implied_equity_usd)
        ltv_round = f"{econ.implied_ltv_pct:.1f}".replace(".0", "")
        if is_cema:
            tax_saved_val = econ.acquisition_debt_usd * 0.028
            tax_saved = _human_millions(tax_saved_val) if tax_saved_val >= 1_000_000 else f"${int(round(tax_saved_val / 1000)) * 1000:,}"
            p3 = (
                f"<p>How you structure the debt on a {prop.borough} acquisition matters almost as much as what you pay for the deed. "
                f"<strong>{econ.primary_lender}</strong> stepped up with a <strong>{debt_prose}</strong> consolidated loan—representing "
                f"<strong>{ltv_round} percent loan-to-value</strong>—while {buyer_clean} wrote a <strong>{eq_prose}</strong> equity check behind it.</p>"
            )
            p4 = (
                f"<p>Rather than extinguishing the seller's existing note and originating a brand-new mortgage from scratch, the buyers and {lender_clean} "
                f"assigned and consolidated the debt through a CEMA structure. "
                f"Because New York City levies roughly 2.8 percent in mortgage recording taxes on new commercial debt, keeping the existing mortgage wrapper alive "
                f"saved the sponsorship roughly {tax_saved} at the closing table—capital that stays inside the property's reserve account rather than going to the Department of Finance.</p>"
            )
        else:
            debt_p3_variants = [
                (
                    f"<p>The real tell in any {prop.borough} closing sits on the debt side of the ledger. "
                    f"Alongside the deed, <strong>{buyer_clean}</strong> recorded a <strong>{debt_prose}</strong> {m.instrument_type.lower()} "
                    f"from <strong>{econ.primary_lender}</strong>, sizing the senior attachment point to <strong>{ltv_round} percent loan-to-value</strong>.</p>"
                ),
                (
                    f"<p>Follow the mortgage filings in the City Register and the capital stack tells its own story. "
                    f"<strong>{econ.primary_lender}</strong> provided a <strong>{debt_prose}</strong> {m.instrument_type.lower()} at closing, "
                    f"putting senior leverage at <strong>{ltv_round} percent of the purchase price</strong>.</p>"
                ),
                (
                    f"<p>Behind the deed transfer sits a capital structure tailored to {prop.neighborhood}'s current credit reality. "
                    f"<strong>{buyer_clean}</strong> financed the acquisition with a <strong>{debt_prose}</strong> facility from "
                    f"<strong>{econ.primary_lender}</strong>, representing <strong>{ltv_round} percent loan-to-value</strong>.</p>"
                ),
            ]
            debt_p4_variants = [
                (
                    f"<p>Pairing that {debt_prose} senior note with <strong>{eq_prose}</strong> of sponsor equity gave {lender_clean}'s credit committee "
                    f"the exact debt-yield cushion it needed on a {prop.year_built}-vintage {prop.neighborhood} asset. "
                    f"Where thinly capitalized bids stall out in underwriting, a {eq_prose} cash check at {ppsf_prose} clears the table.</p>"
                ),
                (
                    f"<p>Writing a <strong>{eq_prose}</strong> equity check behind {lender_clean}'s {debt_prose} note keeps debt service comfortably covered from day one. "
                    f"In {prop.borough}, relationship banks and private credit desks alike are rewarding sponsors who bring real skin in the game and an entry basis of {ppsf_prose}.</p>"
                ),
                (
                    f"<p>With <strong>{eq_prose}</strong> of implied equity sitting behind {lender_clean}'s {debt_prose} senior position, "
                    f"the sponsorship has both the balance-sheet protection and the operational runway to execute its business plan across all {prop.gross_sqft:,} square feet.</p>"
                ),
            ]
            p3 = debt_p3_variants[v_idx % len(debt_p3_variants)]
            p4 = debt_p4_variants[v_idx % len(debt_p4_variants)]
    else:
        cash_p3_variants = [
            (
                f"<p>Just as telling as the purchase price is what did not hit the City Register alongside the deed: a property-level mortgage. "
                f"<strong>{buyer_clean}</strong> closed <strong>{prop.address}</strong> with <strong>{price_prose}</strong> of unencumbered equity—allowing the sponsorship to move with immediate execution certainty.</p>"
            ),
            (
                f"<p>Search the ACRIS filings for a simultaneous acquisition mortgage on {prop.address} and you will come up empty. "
                f"<strong>{buyer_clean}</strong> wired the entire <strong>{price_prose}</strong> purchase price without property-level debt, taking title 100 percent unencumbered.</p>"
            ),
            (
                f"<p>While leveraged bidders spend sixty days negotiating term sheets and rate caps, <strong>{buyer_clean}</strong> bypassed the debt market entirely at closing—putting up <strong>{price_prose}</strong> in all-cash equity to lock down <strong>{prop.address}</strong>.</p>"
            ),
        ]
        cash_p4_variants = [
            (
                f"<p>Showing up with {price_prose} in cash at {ppsf_prose} remains the sharpest weapon an institutional or private buyer can bring to a New York closing table. "
                f"Once initial leasing, tax-lot assembly, or pre-development milestones are complete, the sponsor can return to the debt market on its own timetable.</p>"
            ),
            (
                f"<p>Closing unencumbered eliminates interest-rate carry during the transition phase and gives {buyer_clean} total flexibility—whether to hold the {prop.gross_sqft:,}-square-foot asset unlevered or size a permanent senior loan once net operating income stabilizes.</p>"
            ),
            (
                f"<p>In {prop.borough}'s tightest corridors, sellers routinely trade price for certainty of close. "
                f"Writing an unlevered {price_prose} check at {ppsf_prose} gave {buyer_clean} the leverage to dictate terms at contract signing and recapitalize later from a position of strength.</p>"
            ),
        ]
        p3 = cash_p3_variants[v_idx % len(cash_p3_variants)]
        p4 = cash_p4_variants[v_idx % len(cash_p4_variants)]

    # 5. Section 3: From Our Desk (Ben Rohr's conversational takeaway + sharp kicker)
    if parts["p5"]:
        p5 = f"<p>{parts['p5']}</p>"
    else:
        if not desk_kicker:
            desk_kicker = (
                f"When {lender_clean} writes {econ.implied_ltv_display or 'disciplined'} leverage on a {ppsf_prose} basis in {prop.neighborhood}, "
                f"it sets the exact benchmark every other sponsor in the submarket will be measured against this quarter."
            )
        desk_openers = [
            f"On our placement desk at Light Tower Group, {prop.address} is a live case study in how {prop.borough} deals actually cross the finish line right now.",
            f"Looking at {prop.address} from our debt and equity desk at Light Tower Group, one takeaway stands out for sponsors sizing up {prop.neighborhood}.",
            f"For sponsors watching the {prop.borough} tape from our desk at Light Tower Group, {buyer_clean}'s move at {prop.address} sends a clear signal.",
        ]
        p5 = f"<p>{desk_openers[v_idx % len(desk_openers)]} {desk_kicker}</p>"

    body_html = scrub_ai_tells(
        f"{p1}\n\n{p2}\n\n<h2>{subhead_1}</h2>\n{p3}\n\n{p4}\n\n<h2>From Our Desk</h2>\n{p5}"
    )

    meta_desc = (
        f"{buyer_clean} buys {prop.address} in {prop.neighborhood}, {prop.borough} for "
        f"{price_prose} ({ppsf_prose}) with {econ.acquisition_debt_display or 'all-cash'} financing."
    )[:160]

    return {
        "title": title,
        "subtitle": subtitle,
        "meta_description": meta_desc,
        "body_html": body_html,
        "tags": [
            prop.borough,
            prop.neighborhood,
            prop.asset_type.split("&")[0].strip(),
            lender_clean if econ.acquisition_debt_usd else "All-Cash Acquisition",
            "NYC $10M+ Deals",
        ],
    }


def verify_nyc_story(
    draft: dict[str, Any],
    dossier: NycTransactionDossier,
    econ: DealEconomics,
) -> tuple[bool, list[str]]:
    """Deterministic verification of a drafted NYC >$10M transaction story.

    Verifies narrative quality, address/price accuracy, and subheadings in `body_html`,
    while allowing raw registry codes (BBL, ACRIS Doc ID) to live cleanly in the Deal Sheet (`data_points`).
    """
    errors: list[str] = []
    title = str(draft.get("title") or "").strip()
    body = str(draft.get("body_html") or "").strip()

    if len(title) < 25:
        errors.append("Headline is too short (<25 chars).")
    if len(body) < 600:
        errors.append("Story body is too short (<600 chars).")
    if "<h2>" not in body:
        errors.append("Story body must include <h2> section subheadings.")
    if dossier.property_info.address.split()[0] not in (title + " " + body):
        errors.append(f"Primary address '{dossier.property_info.address}' missing from story.")

    price_exact = f"{econ.sale_price_usd:,.0f}"
    price_m = econ.sale_price_usd / 1_000_000.0
    price_m_1 = f"{price_m:.1f}".rstrip("0").rstrip(".")
    price_m_2 = f"{price_m:.2f}".rstrip("0").rstrip(".")
    combined = f"{title} {draft.get('subtitle', '')} {body}"
    if not any(
        needle in combined
        for needle in (
            price_exact,
            f"${price_m_1}",
            f"${price_m_2}",
            econ.sale_price_display,
            _human_millions(econ.sale_price_usd),
        )
        if needle
    ):
        errors.append(f"Sale price (${price_exact} or {econ.sale_price_display}) not found in story.")

    return (len(errors) == 0, errors)


def generate_nyc_transaction_article(
    dossier: NycTransactionDossier,
    use_llm: bool = False,
) -> dict[str, Any]:
    """Validate eligibility, compute deal math, draft & verify story, and return a site_renderer article dict.

    Note: Every story is dated on its exact `closing_date` (or `recorded_date` if `closing_date` is absent).
    """
    elig = evaluate_eligibility(dossier)
    if not elig.eligible:
        raise ValueError(
            f"Transaction {dossier.transaction_id} is ineligible for NYC >$10M desk: {elig.reason_codes}"
        )

    econ = compute_economics(dossier)
    draft: dict[str, Any] | None = None

    if use_llm:
        try:
            import os
            import requests

            env_path = REPO_ROOT / "scripts" / ".env"
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            from model_router import provider_chain

            chain = provider_chain(for_writing=True)
            for cfg in chain:
                resp = requests.post(
                    cfg["url"],
                    headers={
                        "Authorization": f"Bearer {cfg['api_key']}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": cfg["model"],
                        "messages": [
                            {"role": "system", "content": NYC_DESK_SYSTEM_PROMPT},
                            {"role": "user", "content": _build_writer_user_prompt(dossier)},
                        ],
                        "temperature": 0.4,
                        "max_tokens": 2200,
                        "response_format": {"type": "json_object"},
                    },
                    timeout=60,
                )
                resp.raise_for_status()
                raw_text = resp.json()["choices"][0]["message"]["content"]
                parsed = json.loads(raw_text)
                if isinstance(parsed, dict) and parsed.get("body_html"):
                    parsed["body_html"] = scrub_ai_tells(parsed["body_html"])
                    ok, errs = verify_nyc_story(parsed, dossier, econ)
                    if ok:
                        draft = parsed
                        break
        except Exception as exc:
            print(f"  [NYC Desk] LLM generation fell back to literary writer: {exc}")

    if draft is None:
        draft = render_literary_story(dossier, econ)
        ok, errs = verify_nyc_story(draft, dossier, econ)
        if not ok:
            raise RuntimeError(f"Literary story failed verification: {errs}")

    prop = dossier.property_info
    slug = _slugify(f"nyc-deal-{prop.address}-{prop.neighborhood}-{int(econ.sale_price_usd // 1_000_000)}m")

    # Date every story on the date the transaction closed
    close_date_str = (dossier.closing_date or dossier.recorded_date)[:10]
    pub_dt = datetime.strptime(close_date_str, "%Y-%m-%d").replace(
        hour=14, minute=0, tzinfo=timezone.utc
    )

    sources = dossier.sources or [
        {
            "name": f"NYC ACRIS Real Property Registry ({prop.address}, BBL {prop.bbl})",
            "url": "https://a836-acris.nyc.gov/DS/DocumentSearch/BBL",
        },
        {
            "name": f"NYC Department of City Planning PLUTO — BBL {prop.bbl} ({prop.building_class}, {prop.zoning})",
            "url": "https://zola.planning.nyc.gov/",
        },
    ]

    article = {
        "title": draft["title"],
        "subtitle": draft.get("subtitle", ""),
        "slug": slug,
        "date": pub_dt.strftime("%B %d, %Y").replace(" 0", " "),
        "date_iso": pub_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closingDate": close_date_str,
        "recordedDate": dossier.recorded_date,
        "category": "NYC $10M+ Transaction Desk",
        "sector": "commercial_real_estate",
        "vertical": "nyc_transactions",
        "borough": prop.borough,
        "neighborhood": prop.neighborhood,
        "bbl": prop.bbl,
        "transactionId": dossier.transaction_id,
        "price": econ.sale_price_usd,
        "editorial_format": "flagship",
        "editorial_format_label": f"NYC $10M+ Transaction Desk · {prop.borough}",
        "franchise": {
            "id": "nyc_transaction_desk",
            "name": "The Capital Stack X-Ray",
        },
        "meta_description": draft.get("meta_description", draft.get("subtitle", ""))[:160],
        "body_html": draft["body_html"],
        "data_note_label": f"Verified ACRIS & PLUTO Deal Sheet · Closed {pub_dt.strftime('%b %d, %Y').replace(' 0', ' ')} · BBL {prop.bbl}",
        "data_points": build_deal_sheet_data_points(dossier, econ),
        "tags": draft.get("tags") or [prop.borough, prop.neighborhood, "NYC $10M+ Deals"],
        "sources": sources,
        "source_count": len(sources),
        "source_name": sources[0]["name"],
        "source_url": sources[0]["url"],
        "must_read_score": 94,
        "pipeline_version": NYC_DESK_PROMPT_VERSION,
        "event_id": dossier.transaction_id,
    }
    return article
