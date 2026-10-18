"""Deterministic eligibility and financial math for the NYC >$10M Transaction Desk."""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

from .models import (
    NYC_BOROUGHS,
    DealEconomics,
    EligibilityResult,
    NycTransactionDossier,
)

MIN_THRESHOLD_USD = 10_000_000.0


def format_usd(amount: float | None) -> str:
    if amount is None or amount <= 0:
        return ""
    if amount >= 1_000_000_000:
        val = amount / 1_000_000_000
        return f"${val:,.2f}B".replace(".00B", "B")
    if amount >= 1_000_000:
        val = amount / 1_000_000
        if abs(val - round(val)) < 0.005:
            return f"${int(round(val)):,}M"
        if abs(val * 10 - round(val * 10)) < 0.05:
            return f"${val:,.1f}M"
        return f"${val:,.2f}M"
    return f"${int(round(amount)):,}"


def normalize_borough(raw: str) -> str:
    key = str(raw or "").strip().lower()
    return NYC_BOROUGHS.get(key, "")


def evaluate_eligibility(
    dossier: NycTransactionDossier,
    *,
    min_threshold_usd: float = MIN_THRESHOLD_USD,
) -> EligibilityResult:
    reasons: list[str] = []
    borough = normalize_borough(dossier.property_info.borough)
    if not borough:
        reasons.append("outside_nyc_five_boroughs")
        return EligibilityResult(status="excluded", reason_codes=reasons)
    dossier.property_info.borough = borough

    if dossier.is_related_party_or_nominal:
        reasons.append("related_party_or_nominal_transfer")
        return EligibilityResult(status="excluded", reason_codes=reasons)

    if dossier.property_info.is_single_condo_or_coop_unit:
        reasons.append("single_residential_condo_or_coop_excluded")
        return EligibilityResult(status="excluded", reason_codes=reasons)

    if dossier.interest_conveyed_pct < 50.0:
        reasons.append("minority_partial_interest_only")
        return EligibilityResult(status="excluded", reason_codes=reasons)

    price = float(dossier.sale_price_usd or 0.0)
    if price <= 0:
        reasons.append("unknown_or_zero_consideration")
        return EligibilityResult(status="uncertain", reason_codes=reasons)

    if abs(price - min_threshold_usd) < 0.01:
        reasons.append("exact_10m_boundary_queue")
        return EligibilityResult(status="boundary_review", reason_codes=reasons)

    if price < min_threshold_usd:
        reasons.append("below_10m_threshold")
        return EligibilityResult(status="excluded", reason_codes=reasons)

    reasons.append("strictly_above_10m_nyc_asset")
    return EligibilityResult(status="eligible", reason_codes=reasons)


def _years_between(d1: str, d2: str) -> float | None:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%B %d, %Y"):
        try:
            dt1 = datetime.strptime(str(d1)[:10], fmt)
            dt2 = datetime.strptime(str(d2)[:10], fmt)
            diff_days = abs((dt2 - dt1).days)
            if diff_days > 0:
                return round(diff_days / 365.25, 1)
        except ValueError:
            continue
    if len(str(d1)) >= 4 and len(str(d2)) >= 4 and str(d1)[:4].isdigit() and str(d2)[:4].isdigit():
        y_diff = abs(int(str(d2)[:4]) - int(str(d1)[:4]))
        if y_diff > 0:
            return float(y_diff)
    return None


def compute_economics(dossier: NycTransactionDossier) -> DealEconomics:
    price = float(dossier.sale_price_usd or 0.0)
    prop = dossier.property_info
    unsupported: list[str] = []

    econ = DealEconomics(
        sale_price_usd=price,
        sale_price_display=format_usd(price),
    )

    if prop.gross_sqft and prop.gross_sqft > 0 and price > 0:
        ppsf = round(price / prop.gross_sqft)
        econ.price_per_gsf = float(ppsf)
        econ.price_per_gsf_display = f"${ppsf:,}/GSF"
    else:
        unsupported.append("price_per_gsf (missing gross_sqft)")

    if prop.buildable_sqft and prop.buildable_sqft > 0 and price > 0:
        pbpsf = round(price / prop.buildable_sqft)
        econ.price_per_buildable_sf = float(pbpsf)
        econ.price_per_buildable_sf_display = f"${pbpsf:,}/BSF"

    if prop.total_units and prop.total_units > 0 and price > 0:
        ppu = round(price / prop.total_units)
        econ.price_per_unit = float(ppu)
        unit_label = "key" if "hotel" in prop.asset_type.lower() else "unit"
        econ.price_per_unit_display = f"${ppu:,}/{unit_label}"
    else:
        unsupported.append("price_per_unit (no unit count)")

    # Debt: only sum active new-money mortgages or the consolidated CEMA balance, never assignment-only docs
    active_mortgages = [
        m for m in dossier.mortgages
        if m.amount_usd > 0 and not m.is_modification_or_assignment_only
    ]
    if active_mortgages:
        # If there is a CEMA/consolidated agreement with total balance, or distinct senior + building notes:
        total_debt = sum(m.amount_usd for m in active_mortgages)
        econ.acquisition_debt_usd = total_debt
        econ.acquisition_debt_display = format_usd(total_debt)
        econ.primary_lender = active_mortgages[0].lender or "Recorded Lender"
        econ.debt_instrument_label = active_mortgages[0].instrument_type or "Senior Mortgage"
        if price > 0 and total_debt <= price * 1.25:
            ltv = round((total_debt / price) * 100.0, 1)
            econ.implied_ltv_pct = ltv
            econ.implied_ltv_display = f"{ltv:.1f}%".replace(".0%", "%")
            if total_debt < price:
                equity = price - total_debt
                econ.implied_equity_usd = equity
                econ.implied_equity_display = format_usd(equity)
    else:
        unsupported.append("acquisition_debt (none recorded or disclosed)")

    # Prior sale comparison (only if same scope)
    comparable_priors = [p for p in dossier.prior_sales if p.same_scope and p.price_usd > 0]
    if comparable_priors:
        prior = comparable_priors[0]
        econ.prior_sale_price_usd = prior.price_usd
        econ.prior_sale_price_display = format_usd(prior.price_usd)
        econ.prior_sale_date = prior.closing_date
        delta_usd = price - prior.price_usd
        delta_pct = round((delta_usd / prior.price_usd) * 100.0, 1)
        econ.prior_sale_change_usd = delta_usd
        econ.prior_sale_change_pct = delta_pct
        sign = "+" if delta_pct > 0 else ""
        econ.prior_sale_change_display = f"{sign}{delta_pct:.1f}% vs. {prior.closing_date[:4]} ({format_usd(prior.price_usd)})"
        econ.hold_period_years = _years_between(prior.closing_date, dossier.closing_date)
    else:
        unsupported.append("prior_sale_comparison (no comparable prior deed)")

    if dossier.noi_usd and dossier.noi_usd > 0 and price > 0:
        cap = round((dossier.noi_usd / price) * 100.0, 2)
        econ.cap_rate_pct = cap
        econ.cap_rate_display = f"{cap:.2f}%"
    else:
        unsupported.append("cap_rate (in-place NOI not disclosed)")

    econ.unsupported_metrics = unsupported
    dossier.economics = econ
    return econ


def build_ammo_sheet(dossier: NycTransactionDossier) -> dict[str, Any]:
    """Produce the verified JSON dictionary fed into the NYC feature writer."""
    if dossier.eligibility is None:
        dossier.eligibility = evaluate_eligibility(dossier)
    econ = dossier.economics or compute_economics(dossier)
    prop = dossier.property_info
    return {
        "transaction_id": dossier.transaction_id,
        "address": prop.address,
        "borough": prop.borough,
        "neighborhood": prop.neighborhood,
        "bbl": prop.bbl,
        "bin": prop.bin_number,
        "asset_type": prop.asset_type,
        "building_class": prop.building_class,
        "closing_date": dossier.closing_date,
        "recorded_date": dossier.recorded_date,
        "buyer": dossier.buyer or "Undisclosed Buyer LLC",
        "seller": dossier.seller or "Undisclosed Seller LLC",
        "broker": dossier.broker,
        "sale_price_usd": int(round(econ.sale_price_usd)),
        "sale_price_display": econ.sale_price_display,
        "gross_sqft": prop.gross_sqft,
        "gross_sqft_display": f"{prop.gross_sqft:,} SF" if prop.gross_sqft else "",
        "buildable_sqft": prop.buildable_sqft,
        "total_units": prop.total_units,
        "stories": prop.stories,
        "year_built": prop.year_built,
        "zoning": prop.zoning,
        "price_per_gsf_display": econ.price_per_gsf_display,
        "price_per_buildable_sf_display": econ.price_per_buildable_sf_display,
        "price_per_unit_display": econ.price_per_unit_display,
        "acquisition_debt_display": econ.acquisition_debt_display,
        "primary_lender": econ.primary_lender,
        "debt_instrument_label": econ.debt_instrument_label,
        "implied_ltv_display": econ.implied_ltv_display,
        "implied_equity_display": econ.implied_equity_display,
        "prior_sale_price_display": econ.prior_sale_price_display,
        "prior_sale_date": econ.prior_sale_date,
        "prior_sale_change_display": econ.prior_sale_change_display,
        "hold_period_years": econ.hold_period_years,
        "cap_rate_display": econ.cap_rate_display,
        "unsupported_metrics": econ.unsupported_metrics,
        "notes": dossier.notes,
    }


def render_deal_facts_panel_html(dossier: NycTransactionDossier) -> str:
    """Render the Deal Facts & Capital Stack HTML callout for the article page."""
    ammo = build_ammo_sheet(dossier)
    rows: list[tuple[str, str]] = [
        ("Property", f"{ammo['address']} ({ammo['neighborhood'] + ', ' if ammo['neighborhood'] else ''}{ammo['borough']})"),
        ("Sale Price", ammo["sale_price_display"]),
    ]
    if ammo["price_per_gsf_display"]:
        rows.append(("Price / GSF", f"{ammo['price_per_gsf_display']} ({ammo['gross_sqft_display']})"))
    if ammo["price_per_buildable_sf_display"]:
        rows.append(("Price / BSF", ammo["price_per_buildable_sf_display"]))
    if ammo["price_per_unit_display"]:
        rows.append(("Price / Unit", f"{ammo['price_per_unit_display']} ({ammo['total_units']} units)"))
    if ammo["buyer"]:
        rows.append(("Buyer", ammo["buyer"]))
    if ammo["seller"]:
        rows.append(("Seller", ammo["seller"]))
    if ammo["acquisition_debt_display"]:
        debt_str = ammo["acquisition_debt_display"]
        if ammo["primary_lender"]:
            debt_str += f" · {ammo['primary_lender']}"
        if ammo["implied_ltv_display"]:
            debt_str += f" ({ammo['implied_ltv_display']} LTV)"
        rows.append(("Senior Debt", debt_str))
    if ammo["prior_sale_change_display"]:
        rows.append(("Basis vs. Prior Sale", ammo["prior_sale_change_display"]))
    if ammo["bbl"]:
        rows.append(("BBL / Class", f"{ammo['bbl']}" + (f" · Class {ammo['building_class']}" if ammo["building_class"] else "")))

    items_html = "".join(
        f'<div class="data-point">'
        f'<span class="data-point-value">{html.escape(val)}</span>'
        f'<span class="data-point-label">{html.escape(label)}</span>'
        f'</div>'
        for label, val in rows[:6]
    )
    return f'<div class="data-points" aria-label="NYC Transaction Deal Sheet">{items_html}</div>'
