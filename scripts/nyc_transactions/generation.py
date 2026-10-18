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

    if econ.implied_equity_usd and econ.implied_equity_usd > 0:
        points.append(
            {
                "value": f"${econ.implied_equity_usd:,.0f}",
                "label": f"Implied Equity · {int(dossier.interest_conveyed_pct)}% Fee Simple",
            }
        )

    if econ.prior_sale_change_display and econ.prior_sale_price_usd:
        points.append(
            {
                "value": econ.prior_sale_change_display.split("(")[0].strip(),
                "label": f"Prior Sale: ${econ.prior_sale_price_usd:,.0f} ({econ.prior_sale_date})",
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


def _extract_note_parts(dossier: NycTransactionDossier) -> tuple[str, str, str, str]:
    scene_hook = ""
    street_context = ""
    subhead_1 = "Inside the Capital Stack"
    desk_kicker = ""
    plain_notes: list[str] = []

    for n in dossier.notes:
        if n.startswith("SUBHEAD::"):
            subhead_1 = n.split("SUBHEAD::", 1)[1].strip()
        elif n.startswith("KICKER::"):
            desk_kicker = n.split("KICKER::", 1)[1].strip()
        else:
            plain_notes.append(n.strip())

    if plain_notes:
        scene_hook = plain_notes[0]
    if len(plain_notes) > 1:
        street_context = plain_notes[1]
    return scene_hook, street_context, subhead_1, desk_kicker


def _build_writer_user_prompt(dossier: NycTransactionDossier) -> str:
    ammo = build_ammo_sheet(dossier)
    scene_hook, street_context, subhead_1, desk_kicker = _extract_note_parts(dossier)
    return f"""Write a flagship NYC >$10M Transaction Desk feature story in the style of a Wall Street Journal Page One feature × New York Magazine × The Real Deal × Commercial Observer's Finance Desk.

=== VERIFIED DEAL AMMO SHEET (JSON) ===
{json.dumps(ammo, indent=2, ensure_ascii=False)}
=======================================

=== NARRATIVE SCENE & CONTEXT ===
- Scene Hook: {scene_hook}
- Street & Deal Context: {street_context}
- Suggested Feature Subheading: {subhead_1}
- Desk Takeaway Thesis: {desk_kicker}
=================================

REQUIREMENTS:
1. "title": A magnetic, magazine-grade headline (under 105 characters) that names the principals/buyer, the address or neighborhood, the dollar figure, and the story angle.
2. "subtitle": A crisp 1-sentence deck (20–35 words) highlighting the human stakes, per-foot/per-door basis, and lender.
3. "meta_description": SEO meta description (135–160 characters) naming the address, neighborhood, sale price, buyer, and lender.
4. "body_html": 450–700 words of smooth, human-crafted HTML using ONLY `<p>`, `<h2>`, `<strong>`, and `<em>` tags:
   - Opening Lede (2 `<p>` paragraphs, no heading): Scene-setting hook + Nut Graf on what the price per foot/door means.
   - `<h2>{subhead_1}</h2>` (2 `<p>` paragraphs): Unpack the debt, LTV, CEMA/agency/life-co/bridge structure, and seller-vs.-buyer math without repeating the Deal Sheet verbatim.
   - `<h2>From Our Desk</h2>` (1–2 `<p>` paragraphs): Ben Rohr's conversational, first-person placement-desk takeaway ending with a sharp kicker line.
   - DO NOT put raw BBL codes, ACRIS Doc IDs, ISO dates (YYYY-MM-DD), or "via ... LLC" inside `body_html`.
5. "tags": Array of 5–6 specific tags (borough, neighborhood, asset class, lender, "NYC $10M+ Deals").

Return ONLY a valid JSON object."""


def render_literary_story(dossier: NycTransactionDossier, econ: DealEconomics) -> dict[str, Any]:
    """Craft a smooth, magazine-grade WSJ/NYT/TRD/CO feature story using the 60-Book & Anti-AI framework."""
    prop = dossier.property_info
    scene_hook, street_context, subhead_1, desk_kicker = _extract_note_parts(dossier)

    buyer_clean = dossier.buyer.split(" via ")[0].strip()
    seller_clean = dossier.seller.split(" via ")[0].strip()
    m = dossier.mortgages[0] if dossier.mortgages else None
    lender_clean = (econ.primary_lender or "balance-sheet capital").split("(")[0].strip()

    price_prose = _human_millions(econ.sale_price_usd)
    price_short = econ.sale_price_display or price_prose
    close_human = _human_date(dossier.closing_date)
    ppsf_int = int(round(econ.price_per_gsf)) if econ.price_per_gsf else 0
    ppsf_prose = f"${ppsf_int:,} a square foot" if ppsf_int else "an institutional basis"

    # Build a magnetic headline and deck tailored to the deal dynamics
    if econ.prior_sale_change_pct is not None and econ.prior_sale_price_usd:
        delta_abs = abs(econ.prior_sale_change_pct)
        prior_yr = econ.prior_sale_date[:4]
        if econ.prior_sale_change_pct <= -15.0:
            title = f"{buyer_clean} Snaps Up {prop.address} for {price_short} in a {int(round(delta_abs))}% {prop.neighborhood} Basis Reset"
        elif econ.prior_sale_change_pct < 0:
            title = f"{buyer_clean} Takes Down {prop.neighborhood}'s {prop.address} for {price_short} at ${ppsf_int:,} a Foot"
        else:
            title = f"Why {buyer_clean} Just Paid {price_prose} for {prop.address} in {prop.neighborhood}"
    else:
        title = f"{buyer_clean} Closes {price_prose} Purchase of {prop.address} in {prop.neighborhood}"

    if econ.acquisition_debt_usd and econ.acquisition_debt_usd > 0:
        debt_prose = _human_millions(econ.acquisition_debt_usd)
        subtitle = (
            f"Backed by a {debt_prose} loan from {lender_clean}, the {prop.neighborhood} trade clears at "
            f"{ppsf_prose} and shows exactly where New York credit committees are drawing the line."
        )
    else:
        subtitle = (
            f"The {price_prose} closing in {prop.neighborhood} sets a fresh {ppsf_prose} benchmark "
            f"across {prop.gross_sqft:,} square feet."
        )

    # Paragraph 1: Scene-setting Lede (Blundell / Wolfe / Talese)
    if scene_hook and street_context:
        p1 = (
            f"<p>{scene_hook} {street_context} "
            f"When the deed closed on {close_human}, <strong>{buyer_clean}</strong> had officially taken down "
            f"<strong>{prop.address}</strong> from <strong>{seller_clean}</strong> for <strong>{price_prose}</strong>, "
            f"with <strong>{dossier.broker}</strong> brokering the trade.</p>"
        )
    else:
        p1 = (
            f"<p>On {close_human}, <strong>{buyer_clean}</strong> closed on the {prop.stories}-story "
            f"{prop.asset_type.lower()} at <strong>{prop.address}</strong> in {prop.neighborhood}, {prop.borough}, "
            f"paying <strong>{price_prose}</strong> to <strong>{seller_clean}</strong> in a transaction arranged by "
            f"<strong>{dossier.broker}</strong>.</p>"
        )

    # Paragraph 2: The Nut Graf (McPhee / Didion benchmark translation)
    unit_clause = ""
    if econ.price_per_unit and prop.residential_units > 0:
        unit_clause = (
            f"—or <strong>${int(round(econ.price_per_unit)):,} a door</strong> across its "
            f"{prop.residential_units} apartments—"
        )
    elif "hotel" in prop.asset_type.lower() and econ.price_per_unit:
        unit_clause = (
            f"—or <strong>${int(round(econ.price_per_unit)):,} a key</strong> across its "
            f"{prop.total_units} rooms—"
        )

    cap_clause = (
        f" Even better for the buyers, the in-place rent roll hands them a verified "
        f"<strong>{econ.cap_rate_pct:.2f} percent going-in cap rate</strong> from day one."
        if econ.cap_rate_pct
        else ""
    )

    if econ.prior_sale_change_pct is not None and econ.prior_sale_price_usd:
        prior_prose = _human_millions(econ.prior_sale_price_usd)
        prior_month_yr = _human_month_year(econ.prior_sale_date)
        delta_abs = abs(econ.prior_sale_change_pct)
        if econ.prior_sale_change_pct < 0:
            p2 = (
                f"<p>Look past the headline figure and the story is all about the basis reset. "
                f"The {prop.gross_sqft:,}-square-foot building last traded in {prior_month_yr} for {prior_prose}. "
                f"Stepping in at {ppsf_prose}{unit_clause} shaves <strong>{delta_abs:.1f} percent</strong> off that prior valuation, "
                f"giving {buyer_clean} a margin of safety that would have been unthinkable at the top of the cycle.{cap_clause}</p>"
            )
        else:
            p2 = (
                f"<p>Look past the sticker price and the trade tells a clear story about replacement cost in {prop.borough}. "
                f"At <strong>{ppsf_prose}</strong>{unit_clause} across {prop.gross_sqft:,} square feet, the closing price marks a "
                f"<strong>{delta_abs:.1f} percent step-up</strong> over the {prior_prose} basis recorded in {prior_month_yr}. "
                f"In today's five-borough construction market, buying modern or well-maintained brick at {ppsf_prose} still beats the time and cost of digging a foundation from scratch.{cap_clause}</p>"
            )
    else:
        p2 = (
            f"<p>At <strong>{ppsf_prose}</strong>{unit_clause} across {prop.gross_sqft:,} square feet, "
            f"the trade establishes a clean clearing mark for {prop.neighborhood} {prop.asset_type.lower()} assets.{cap_clause}</p>"
        )

    # Section 2: Bespoke Capital Stack & Plumbing X-Ray (Michael Lewis / Connie Bruck)
    is_cema = bool(m and ("CEMA" in m.instrument_type.upper() or "AGMT" in m.instrument_type.upper()))
    if econ.acquisition_debt_usd and econ.acquisition_debt_usd > 0 and m:
        debt_prose = _human_millions(econ.acquisition_debt_usd)
        eq_prose = _human_millions(econ.implied_equity_usd)
        ltv_round = f"{econ.implied_ltv_pct:.1f}".replace(".0", "")
        if is_cema:
            tax_saved = _human_millions(econ.acquisition_debt_usd * 0.028)
            p3 = (
                f"<p>How you structure the debt on a {prop.borough} acquisition matters almost as much as what you pay for the deed. "
                f"<strong>{econ.primary_lender}</strong> stepped up with a <strong>{debt_prose}</strong> senior loan—representing "
                f"<strong>{ltv_round} percent loan-to-value</strong>—while the buyers wrote a <strong>{eq_prose}</strong> equity check behind it.</p>"
            )
            p4 = (
                f"<p>Rather than extinguishing the seller's old note and originating a scratch mortgage, the buyers and {lender_clean} "
                f"kept the existing mortgage wrapper alive through a Consolidation, Extension, and Modification Agreement, or CEMA. "
                f"Because New York City levies a roughly 2.8 percent mortgage recording tax on new commercial debt, that single piece of legal plumbing "
                f"saved the deal upwards of {tax_saved} at the closing table—cash that stays in the property's capex and leasing reserve instead of going to the Department of Finance.</p>"
            )
        else:
            p3 = (
                f"<p>The real tell in any {prop.borough} closing sits on the debt side of the ledger. "
                f"To fund the purchase, {buyer_clean} locked in a <strong>{debt_prose}</strong> {m.instrument_type.lower()} "
                f"from <strong>{econ.primary_lender}</strong> at <strong>{ltv_round} percent loan-to-value</strong>.</p>"
            )
            p4 = (
                f"<p>That loan commitment meant the buyers only needed to write a <strong>{eq_prose}</strong> equity check "
                f"to control a {prop.stories}-story, {prop.year_built}-vintage {prop.neighborhood} asset. "
                f"Credit committees aren'tstretching to 75 percent leverage anymore, but when a sponsor brings {eq_prose} of real cash equity "
                f"and a basis of {ppsf_prose}, lenders like {lender_clean} are wide open for business.</p>"
            ).replace("aren'tstretching", "aren't stretching")
    else:
        p3 = (
            f"<p>Notably, the deed hit the city register without a simultaneous acquisition mortgage—signaling an all-cash close "
            f"or balance-sheet credit line that allowed {buyer_clean} to move with speed and certainty.</p>"
        )
        p4 = (
            f"<p>In a market where financing contingencies can stall a closing for sixty days, showing up with unencumbered equity at "
            f"{ppsf_prose} remains the sharpest weapon a buyer can bring to the negotiating table—with the option to place permanent debt once initial leasing is complete.</p>"
        )

    # Section 3: From Our Desk (Ben Rohr's conversational takeaway + sharp kicker)
    if not desk_kicker:
        desk_kicker = (
            f"When {lender_clean} writes {econ.implied_ltv_display or 'conservative'} leverage on a {ppsf_prose} basis in {prop.neighborhood}, "
            f"it sets the exact benchmark every other sponsor in the submarket will be measured against this quarter."
        )

    p5 = (
        f"<p>When we look at {prop.address} on our placement desk at Light Tower Group, the lesson for New York sponsors comes down to "
        f"the marriage of entry basis and lender selection. {buyer_clean} didn't try to fight the tape—they bought {prop.neighborhood} footage at "
        f"{ppsf_prose} and paired it with the exact lender bucket built for this business plan. {desk_kicker}</p>"
    )

    body_html = scrub_ai_tells(
        f"{p1}\n\n{p2}\n\n<h2>{subhead_1}</h2>\n{p3}\n\n{p4}\n\n<h2>From Our Desk</h2>\n{p5}"
    )

    meta_desc = (
        f"{buyer_clean} buys {prop.address} in {prop.neighborhood}, {prop.borough} for "
        f"{price_prose} ({ppsf_prose}) with {econ.acquisition_debt_display or 'equity'} financing from {lender_clean}."
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
            lender_clean,
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
