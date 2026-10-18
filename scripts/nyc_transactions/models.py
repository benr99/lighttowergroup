"""Durable data structures for the NYC >$10M Transaction Desk."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


NYC_BOROUGHS = {
    "manhattan": "Manhattan",
    "brooklyn": "Brooklyn",
    "queens": "Queens",
    "bronx": "Bronx",
    "the bronx": "Bronx",
    "staten island": "Staten Island",
    "1": "Manhattan",
    "2": "Bronx",
    "3": "Brooklyn",
    "4": "Queens",
    "5": "Staten Island",
}


@dataclass
class PropertyIdentity:
    address: str
    borough: str
    neighborhood: str = ""
    bbl: str = ""
    bin_number: str = ""
    building_class: str = ""
    asset_type: str = "Commercial"
    gross_sqft: int = 0
    lot_sqft: int = 0
    buildable_sqft: int = 0
    total_units: int = 0
    residential_units: int = 0
    stories: int = 0
    year_built: int = 0
    zoning: str = ""
    is_single_condo_or_coop_unit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MortgageRecord:
    document_id: str
    instrument_type: str  # "MTGE", "AGMT" (CEMA), "BUILDING_LOAN", etc.
    amount_usd: float
    lender: str = ""
    recorded_date: str = ""
    term_years: float | None = None
    rate_notes: str = ""
    is_modification_or_assignment_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PriorSaleRecord:
    closing_date: str
    price_usd: float
    buyer: str = ""
    seller: str = ""
    document_id: str = ""
    same_scope: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EligibilityResult:
    status: str  # "eligible" | "excluded" | "boundary_review" | "uncertain"
    reason_codes: list[str] = field(default_factory=list)

    @property
    def eligible(self) -> bool:
        return self.status == "eligible"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DealEconomics:
    sale_price_usd: float
    sale_price_display: str
    price_per_gsf: float | None = None
    price_per_gsf_display: str = ""
    price_per_buildable_sf: float | None = None
    price_per_buildable_sf_display: str = ""
    price_per_unit: float | None = None
    price_per_unit_display: str = ""
    acquisition_debt_usd: float | None = None
    acquisition_debt_display: str = ""
    primary_lender: str = ""
    debt_instrument_label: str = ""
    implied_ltv_pct: float | None = None
    implied_ltv_display: str = ""
    implied_equity_usd: float | None = None
    implied_equity_display: str = ""
    prior_sale_price_usd: float | None = None
    prior_sale_price_display: str = ""
    prior_sale_date: str = ""
    prior_sale_change_usd: float | None = None
    prior_sale_change_pct: float | None = None
    prior_sale_change_display: str = ""
    hold_period_years: float | None = None
    cap_rate_pct: float | None = None
    cap_rate_display: str = ""
    unsupported_metrics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NycTransactionDossier:
    transaction_id: str
    property_info: PropertyIdentity
    sale_price_usd: float
    closing_date: str
    recorded_date: str = ""
    buyer: str = ""
    seller: str = ""
    broker: str = ""
    transaction_type: str = "Building Sale"
    interest_conveyed_pct: float = 100.0
    is_portfolio: bool = False
    portfolio_has_situs_allocations: bool = True
    is_related_party_or_nominal: bool = False
    noi_usd: float | None = None
    mortgages: list[MortgageRecord] = field(default_factory=list)
    prior_sales: list[PriorSaleRecord] = field(default_factory=list)
    sources: list[dict[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    eligibility: EligibilityResult | None = None
    economics: DealEconomics | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
