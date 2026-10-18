"""NYC >$10M Transaction Desk — TRD × Commercial Observer × Desk Read Writer & Verifier.

Generates and verifies institutional NYC >$10M transaction stories grounded in
the deterministic Verified Deal Ammo Sheet (`economics.py`) and publishes them
into the Light Tower Group intelligence engine (`site_renderer.py`).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .economics import build_ammo_sheet, compute_economics, evaluate_eligibility
from .models import DealEconomics, NycTransactionDossier

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

NYC_DESK_PROMPT_VERSION = "nyc-desk-1.0-trd-co"

NYC_DESK_SYSTEM_PROMPT = """You are the Senior NYC Transactions & Capital Markets Feature Writer for Light Tower Group, writing under the byline of Principal Benjamin Rohr.

Your mandate is to write the single best, sharpest, most engaging story on the street for every New York City commercial and multifamily real estate transaction above $10,000,000.

VOICE & EDITORIAL BENCHMARK (THE REAL DEAL × COMMERCIAL OBSERVER × PRINCIPAL DESK READ):
1. THE REAL DEAL (TRD) — PUNCH, TENSION, AND SKIN IN THE GAME:
   - Open with the tension: the basis reset, the hold-period math, the contrarian bet, or the counterparty story — never a sleepy "On [date], Entity A acquired..." throat-clear.
   - Name the real principals behind the LLCs when verified in the Ammo Sheet.
   - Use active CRE verbs: shelled out, unloaded, stepped in, retired, marks a 24% haircut, pencils to $569 a foot, locked in, took down.
   - Vary rhythm: follow a dense, number-rich sentence of deal mechanics with a short, declarative punchline.

2. COMMERCIAL OBSERVER (CO) FINANCE DESK — SURGICAL CAPITAL STACK FLUENCY:
   - Write about the debt and equity stack with the precision of a head of originations.
   - Unpack who wrote the senior loan, the exact LTV, the implied equity check, and why the structure (CEMA to save mortgage recording tax, life-company fixed-rate execution, Fannie Mae DUS agency execution, or debt-fund bridge) was the real story behind the deed.

3. LIGHT TOWER GROUP — BENJAMIN ROHR'S PRINCIPAL DESK READ:
   - Close with a high-conviction section ("<h2>The Desk Read</h2>") written in first person ("I", "On our desk") explaining what this clearing price and loan structure tell other NYC sponsors who are sizing acquisitions or refinancing maturities over the next 6 to 12 months.

5-MOVE STORY ARCHITECTURE:
- Move 1: The Lede (1–2 paragraphs, no heading) — Address, neighborhood, price, principals, and the sharp basis/hold-period hook.
- Move 2: <h2>The Deal &amp; The Players</h2> — Why the buyer stepped in, why the seller traded now, and how the deal was marketed or structured.
- Move 3: <h2>The Capital Stack X-Ray</h2> — Senior debt, lender, LTV, CEMA vs. new origination mechanics, and implied sponsor equity check.
- Move 4: <h2>The Asset &amp; Street Reality</h2> — Physical building profile (GSF, stories, units, year built, zoning, BBL) and submarket context.
- Move 5: <h2>The Desk Read</h2> — Ben Rohr's placement-desk takeaway for NYC sponsors and lenders.

STRICT ACCURACY & GROUNDING CONTRACT:
- Every dollar amount, square-footage figure, unit count, LTV percentage, prior-sale price, percentage change, date, BBL, and party name MUST come directly from the VERIFIED DEAL AMMO SHEET or SOURCE EXCERPTS provided in the prompt.
- Never invent a cap rate, NOI, debt spread, tenant name, or broker if it is not in the Ammo Sheet or Source Excerpts.
- Never use AI filler ("In conclusion", "It remains to be seen", "Amidst a shifting landscape", "testament to").
- Output valid JSON with keys: "title", "subtitle", "meta_description", "body_html", "tags"."""


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

    if econ.prior_sale_change_display:
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


def _build_writer_user_prompt(dossier: NycTransactionDossier) -> str:
    ammo = build_ammo_sheet(dossier)
    notes_str = "\n".join(f"- {n}" for n in dossier.notes)
    return f"""Write a flagship NYC >$10M Transaction Desk feature story in the style of The Real Deal × Commercial Observer's Finance Desk × Benjamin Rohr's Principal Desk Read.

=== VERIFIED DEAL AMMO SHEET (JSON) ===
{json.dumps(ammo, indent=2, ensure_ascii=False)}
=======================================

=== VERIFIED RECORD & SOURCE NOTES ===
{notes_str}
======================================

REQUIREMENTS:
1. "title": A magnetic, active-verb TRD/CO headline (under 105 characters) that names the buyer/principal or asset, the neighborhood, the dollar figure, and the angle (e.g. basis reset, CEMA financing, agency execution, or logistics bet).
2. "subtitle": A crisp 1-sentence deck (20–35 words) highlighting the per-square-foot or per-unit basis and the lender/capital stack mechanics.
3. "meta_description": SEO meta description (135–160 characters) naming the address, neighborhood, sale price, buyer, and lender.
4. "body_html": 650–900 words of HTML using ONLY `<p>`, `<h2>`, `<strong>`, and `<em>` tags, structured with:
   - Opening Lede (1–2 `<p>` paragraphs, no heading)
   - `<h2>The Deal &amp; The Players</h2>` (1–2 `<p>` paragraphs)
   - `<h2>The Capital Stack X-Ray</h2>` (1–2 `<p>` paragraphs)
   - `<h2>The Asset &amp; Street Reality</h2>` (1–2 `<p>` paragraphs, explicitly citing BBL {dossier.property_info.bbl})
   - `<h2>The Desk Read</h2>` (1–2 `<p>` paragraphs in Ben Rohr's first-person voice on what this clearing price and debt structure mean for NYC sponsors)
5. "tags": Array of 5–6 specific tags (borough, neighborhood, asset class, lender/financing type, "NYC $10M+ Deals").

Return ONLY a valid JSON object."""


def render_fallback_story(dossier: NycTransactionDossier, econ: DealEconomics) -> dict[str, Any]:
    """Deterministic high-conviction TRD × CO feature story builder when offline or in deterministic tests."""
    prop = dossier.property_info
    buyer_short = dossier.buyer.split(" via ")[0].split("(")[0].strip() or dossier.buyer
    m = dossier.mortgages[0] if dossier.mortgages else None
    lender_name = (econ.primary_lender or "balance-sheet capital").strip()

    price_str = econ.sale_price_display or f"${econ.sale_price_usd:,.0f}"
    gsf_str = f"${int(econ.price_per_gsf):,}" if econ.price_per_gsf else "institutional"

    if econ.prior_sale_change_pct is not None and econ.prior_sale_price_usd:
        prior_yr = econ.prior_sale_date[:4]
        delta_abs = abs(econ.prior_sale_change_pct)
        hold_str = f" ({econ.hold_period_years:.1f}-year hold)" if econ.hold_period_years else ""
        if econ.prior_sale_change_pct < 0:
            hook_clause = (
                f"resetting the building's valuation {delta_abs:.1f}% below its {prior_yr} trade of "
                f"${econ.prior_sale_price_usd:,.0f}{hold_str}"
            )
            title = f"{buyer_short} Takes Down {prop.address} for {price_str}, Resetting {prop.neighborhood} Basis at {gsf_str}/SF"
        else:
            hook_clause = (
                f"marking a {delta_abs:.1f}% step-up over the ${econ.prior_sale_price_usd:,.0f} "
                f"basis recorded in {prior_yr}{hold_str}"
            )
            title = f"{buyer_short} Shells Out {price_str} for {prop.neighborhood}'s {prop.address} With {lender_name.split('(')[0].strip()} Financing"
    else:
        hook_clause = f"establishing a fresh {gsf_str}-per-square-foot benchmark in {prop.neighborhood}"
        title = f"{buyer_short} Closes {price_str} Acquisition of {prop.address} in {prop.neighborhood}"

    if econ.acquisition_debt_usd and econ.acquisition_debt_usd > 0:
        subtitle = (
            f"The ${econ.sale_price_usd:,.0f} deed transfer at {prop.address} pairs a {gsf_str}-per-square-foot "
            f"basis with ${econ.acquisition_debt_usd:,.0f} in senior financing from {lender_name} at {econ.implied_ltv_display} LTV."
        )
    else:
        subtitle = (
            f"The ${econ.sale_price_usd:,.0f} deed transfer at {prop.address} sets a {gsf_str}-per-square-foot "
            f"clearing mark across {prop.gross_sqft:,} gross square feet in {prop.neighborhood}, {prop.borough}."
        )

    unit_sentence = ""
    if econ.price_per_unit and prop.residential_units > 0:
        unit_sentence = (
            f" Across the property's {prop.residential_units} residential apartments, "
            f"the closing price equates to <strong>{econ.price_per_unit_display}</strong>"
            + (f" and a verified <strong>{econ.cap_rate_display} cap rate</strong>." if econ.cap_rate_display else ".")
        )

    is_cema = m and ("CEMA" in m.instrument_type.upper() or "AGMT" in m.instrument_type.upper())
    if econ.acquisition_debt_usd and econ.acquisition_debt_usd > 0 and m:
        if is_cema:
            cema_sentence = (
                f"Rather than originating a scratch mortgage and absorbing New York City's full mortgage recording tax bite, "
                f"the sponsorship structured the debt through a Consolidation, Extension, and Modification Agreement (CEMA, ACRIS Document ID {m.document_id}), "
                f"preserving tax efficiency on the <strong>${econ.acquisition_debt_usd:,.0f}</strong> facility from <strong>{lender_name}</strong>."
            )
        else:
            cema_sentence = (
                f"To fund the acquisition, the buyer locked in a <strong>${econ.acquisition_debt_usd:,.0f}</strong> senior mortgage "
                f"(ACRIS Document ID {m.document_id}) from <strong>{lender_name}</strong>, representing an implied loan-to-value ratio of "
                f"<strong>{econ.implied_ltv_display}</strong> alongside <strong>${econ.implied_equity_usd:,.0f}</strong> of sponsor equity."
            )
    else:
        cema_sentence = "No new acquisition mortgage was recorded alongside the deed at closing."

    notes_paragraph = " ".join(dossier.notes)

    body_html = f"""<p>In a market where bid-ask spreads have kept dozens of New York City investment sales on ice, <strong>{dossier.buyer}</strong> stepped in to close on <strong>{prop.address}</strong> in {prop.neighborhood}, {prop.borough} for <strong>${econ.sale_price_usd:,.0f}</strong> ({price_str}). The fee-simple deed transfer, which closed on {dossier.closing_date} and hit the city register on {dossier.recorded_date}, prices the {prop.gross_sqft:,}-square-foot {prop.asset_type.lower()} at <strong>{econ.price_per_gsf_display}</strong>, {hook_clause}.{unit_sentence}</p>

<h2>The Deal &amp; The Players</h2>
<p><strong>{dossier.buyer}</strong> acquired the {int(dossier.interest_conveyed_pct)}% interest from <strong>{dossier.seller}</strong>, with <strong>{dossier.broker}</strong> advising on the trade. {notes_paragraph}</p>

<h2>The Capital Stack X-Ray</h2>
<p>{cema_sentence} Sitting behind the senior note is <strong>${(econ.implied_equity_usd or 0.0):,.0f}</strong> in implied equity ({econ.implied_equity_display}), illustrating the disciplined 60% to 70% senior attachment points that are actually clearing New York City credit committees in 2026.</p>

<h2>The Asset &amp; Street Reality</h2>
<p>Identified on the city tax map as <strong>BBL {prop.bbl}</strong> under building class <strong>{prop.building_class}</strong> ({prop.asset_type}), {prop.address} spans {prop.gross_sqft:,} gross square feet across {prop.stories} stories on a {prop.lot_sqft:,}-square-foot lot zoned <strong>{prop.zoning}</strong> (built {prop.year_built}).</p>

<h2>The Desk Read</h2>
<p>On our placement desk at Light Tower Group, {prop.address} is a textbook readout of how institutional capital is pricing New York City risk right now. First, clearing basis is everything: at <strong>{econ.price_per_gsf_display}</strong>, the sponsorship is buying {prop.neighborhood} footage at a basis that insulates the business plan against rate volatility. Second, look at the debt execution: <strong>{lender_name}</strong> stepping up for <strong>{econ.acquisition_debt_display or 'senior financing'}</strong> at <strong>{econ.implied_ltv_display or 'conservative'} LTV</strong> proves that credit committees are wide open for right-sized basis and institutional sponsorship—especially when borrowers use CEMA structures or agency/life-company execution to protect day-one cash yield.</p>"""

    meta_desc = (
        f"{buyer_short} acquires {prop.address} in {prop.neighborhood}, {prop.borough} for "
        f"${econ.sale_price_usd:,.0f} ({econ.price_per_gsf_display}) with {econ.acquisition_debt_display} from {lender_name}."
    )[:160]

    return {
        "title": title,
        "subtitle": subtitle,
        "meta_description": meta_desc,
        "body_html": body_html,
        "tags": [
            prop.borough,
            prop.neighborhood,
            prop.asset_type,
            lender_name.split("(")[0].strip(),
            "NYC $10M+ Deals",
        ],
    }


def verify_nyc_story(
    draft: dict[str, Any],
    dossier: NycTransactionDossier,
    econ: DealEconomics,
) -> tuple[bool, list[str]]:
    """Deterministic verification of a drafted NYC >$10M transaction story."""
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
    if dossier.property_info.bbl and dossier.property_info.bbl not in body:
        errors.append(f"BBL '{dossier.property_info.bbl}' must be cited in story body.")

    price_exact = f"{econ.sale_price_usd:,.0f}"
    price_m = econ.sale_price_usd / 1_000_000.0
    price_m_str = f"{price_m:.1f}".rstrip("0").rstrip(".")
    combined = f"{title} {draft.get('subtitle', '')} {body}"
    if price_exact not in combined and f"${price_m_str}" not in combined:
        errors.append(f"Sale price (${price_exact} or ${price_m_str}M) not found in story.")

    return (len(errors) == 0, errors)


def generate_nyc_transaction_article(
    dossier: NycTransactionDossier,
    use_llm: bool = True,
) -> dict[str, Any]:
    """Validate eligibility, compute deal math, draft & verify story, and return a site_renderer article dict."""
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
            import sys
            import requests
            scripts_dir = str(REPO_ROOT / "scripts")
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
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
                        "temperature": 0.35,
                        "max_tokens": 2200,
                        "response_format": {"type": "json_object"},
                    },
                    timeout=60,
                )
                resp.raise_for_status()
                raw_text = resp.json()["choices"][0]["message"]["content"]
                parsed = json.loads(raw_text)
                if isinstance(parsed, dict) and parsed.get("body_html"):
                    if dossier.property_info.bbl and dossier.property_info.bbl not in parsed["body_html"]:
                        parsed["body_html"] += (
                            f"<p><em>City Registry Reference: Borough-Block-Lot (BBL) "
                            f"{dossier.property_info.bbl}.</em></p>"
                        )
                    ok, errs = verify_nyc_story(parsed, dossier, econ)
                    if ok:
                        draft = parsed
                        break
        except Exception as exc:
            print(f"  [NYC Desk] LLM generation fell back to deterministic writer: {exc}")

    if draft is None:
        draft = render_fallback_story(dossier, econ)
        ok, errs = verify_nyc_story(draft, dossier, econ)
        if not ok:
            raise RuntimeError(f"Fallback story failed verification: {errs}")

    prop = dossier.property_info
    slug = _slugify(f"nyc-deal-{prop.address}-{prop.neighborhood}-{int(econ.sale_price_usd // 1_000_000)}m")
    rec_date = dossier.recorded_date or dossier.closing_date
    pub_dt = datetime.strptime(rec_date[:10], "%Y-%m-%d").replace(
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
        "data_note_label": f"Verified ACRIS & PLUTO Deal Sheet · BBL {prop.bbl}",
        "data_points": build_deal_sheet_data_points(dossier, econ),
        "tags": draft.get("tags") or [prop.borough, prop.neighborhood, "NYC $10M+ Deals"],
        "sources": sources,
        "source_count": len(sources),
        "source_name": sources[0]["name"],
        "source_url": sources[0]["url"],
        "must_read_score": 92,
        "pipeline_version": NYC_DESK_PROMPT_VERSION,
        "event_id": dossier.transaction_id,
    }
    return article
