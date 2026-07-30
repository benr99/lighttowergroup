# 08 — Implementation Plan: Multi-Sector Intelligence Engine

A phased implementation plan that transforms the current single-sector CRE pipeline into a 7-sector institutional intelligence engine. The plan works within the existing constraints: GitHub Actions orchestration, Netlify hosting, Python 3.11 runtime, and DeepSeek LLM (with OpenAI fallback).

---

## Phase 1: Foundation (Week 1)

**Goal:** Create the config layer and canonical data model without changing the existing pipeline. Everything runs in shadow mode — validating, classifying, and scoring but not influencing output.

### 1.1 Create the Config Directory

Create `config/` at the repository root with five JSON files. These files are the single source of truth for the entire pipeline.

#### config/sources.json
Port the existing ~90 CRE feeds into a structured format. Each entry:

```json
{
  "id": "bisnow-national",
  "name": "Bisnow National",
  "url": "https://www.bisnow.com/rss/national",
  "sector": "commercial_real_estate",
  "sector_weight": 1.0,
  "tier": "tier_1",
  "fetch_frequency": "every_run",
  "auth_required": false,
  "active": true,
  "content_type": "rss",
  "language": "en",
  "notes": "Primary CRE news source",
  "last_validated": null,
  "consecutive_failures": 0,
  "added_date": "2025-01-15"
}
```

Fields expanded:
- `sector`: One of seven canonical sector identifiers (commercial_real_estate, private_equity, data_centers, energy_infrastructure, banking_credit, federal_policy, local_government).
- `sector_weight`: Float 0.0–2.0. Use 1.0 for pure-sector sources, 0.5 for cross-sector sources (e.g., Wall Street Journal covers banking AND PE).
- `tier`: Controls fetch priority and article tier inheritance. tier_1 sources have lower evidence requirements.
- `content_type`: `rss`, `atom`, `api`, or `scraper`.
- `consecutive_failures`: Reset on success. Auto-disable at 3 (circuit breaker pattern already in editorial_intelligence.py).

Total entries: ~205 (90 existing CRE + ~115 new across 6 new sectors).

#### config/scoring_profiles.json
The 7 sector profiles from document 06-scoring-spec. Each profile defines weight multipliers for 10 scoring dimensions:

```json
{
  "commercial_real_estate": {
    "label": "Commercial Real Estate",
    "weights": {
      "transaction_significance": 1.5,
      "market_movement": 1.2,
      "policy_impact": 0.8,
      "entity_prominence": 1.0,
      "narrative_value": 1.0,
      "sector_urgency": 1.0,
      "capital_flows": 1.4,
      "geographic_significance": 1.1,
      "counterparty_quality": 1.2,
      "temporal_relevance": 0.6
    },
    "article_targets": {
      "must_cover": 5,
      "strongly_recommended": 10,
      "brief_format": 15,
      "deal_tape": 0
    },
    "voice_mode": "narrative_financial",
    "subsectors": ["office", "multifamily", "industrial", "retail", "hospitality", "healthcare_re", "life_sciences"]
  },
  "private_equity": {
    "label": "Private Equity",
    "weights": {
      "transaction_significance": 1.8,
      "market_movement": 0.9,
      "policy_impact": 0.7,
      "entity_prominence": 1.5,
      "narrative_value": 1.2,
      "sector_urgency": 0.8,
      "capital_flows": 1.6,
      "geographic_significance": 0.6,
      "counterparty_quality": 1.4,
      "temporal_relevance": 0.5
    },
    "article_targets": {
      "must_cover": 5,
      "strongly_recommended": 10,
      "brief_format": 15,
      "deal_tape": 0
    },
    "voice_mode": "narrative_financial",
    "subsectors": ["buyouts", "growth_equity", "venture_capital", "fundraising", "exits", "secondaries", "co_investment"]
  },
  "data_centers": {
    "label": "Data Centers & Digital Infrastructure",
    "weights": {
      "transaction_significance": 1.4,
      "market_movement": 1.3,
      "policy_impact": 1.2,
      "entity_prominence": 1.3,
      "narrative_value": 0.9,
      "sector_urgency": 1.4,
      "capital_flows": 1.5,
      "geographic_significance": 1.3,
      "counterparty_quality": 1.1,
      "temporal_relevance": 0.7
    },
    "article_targets": {
      "must_cover": 5,
      "strongly_recommended": 10,
      "brief_format": 15,
      "deal_tape": 0
    },
    "voice_mode": "technical_analytical",
    "subsectors": ["hyperscale", "colocation", "edge_computing", "fiber_networks", "power_procurement", "land_acquisition"]
  },
  "energy_infrastructure": {
    "label": "Energy & Infrastructure",
    "weights": {
      "transaction_significance": 1.6,
      "market_movement": 1.1,
      "policy_impact": 1.5,
      "entity_prominence": 1.2,
      "narrative_value": 0.8,
      "sector_urgency": 1.3,
      "capital_flows": 1.4,
      "geographic_significance": 1.0,
      "counterparty_quality": 1.1,
      "temporal_relevance": 0.5
    },
    "article_targets": {
      "must_cover": 5,
      "strongly_recommended": 10,
      "brief_format": 15,
      "deal_tape": 0
    },
    "voice_mode": "analytical_regulatory",
    "subsectors": ["renewable_energy", "oil_gas", "power_generation", "transmission", "energy_storage", "infrastructure_finance"]
  },
  "banking_credit": {
    "label": "Banking & Credit Markets",
    "weights": {
      "transaction_significance": 1.3,
      "market_movement": 1.5,
      "policy_impact": 1.4,
      "entity_prominence": 1.2,
      "narrative_value": 0.9,
      "sector_urgency": 1.2,
      "capital_flows": 1.5,
      "geographic_significance": 0.8,
      "counterparty_quality": 1.3,
      "temporal_relevance": 0.6
    },
    "article_targets": {
      "must_cover": 5,
      "strongly_recommended": 10,
      "brief_format": 15,
      "deal_tape": 0
    },
    "voice_mode": "analytical_regulatory",
    "subsectors": ["commercial_lending", "cmbs", "regulatory_capital", "m_and_a_advisory", "distressed_debt", "private_credit"]
  },
  "federal_policy": {
    "label": "Federal Policy & Regulatory",
    "weights": {
      "transaction_significance": 0.6,
      "market_movement": 1.3,
      "policy_impact": 2.0,
      "entity_prominence": 1.1,
      "narrative_value": 1.0,
      "sector_urgency": 1.1,
      "capital_flows": 0.8,
      "geographic_significance": 0.5,
      "counterparty_quality": 0.7,
      "temporal_relevance": 0.9
    },
    "article_targets": {
      "must_cover": 5,
      "strongly_recommended": 10,
      "brief_format": 15,
      "deal_tape": 0
    },
    "voice_mode": "analytical_regulatory",
    "subsectors": ["fomc", "sec", "cfpb", "treasury", "congressional", "tax_policy", "antitrust"]
  },
  "local_government": {
    "label": "Local Government & Municipal Finance",
    "weights": {
      "transaction_significance": 1.0,
      "market_movement": 0.7,
      "policy_impact": 1.8,
      "entity_prominence": 0.9,
      "narrative_value": 1.1,
      "sector_urgency": 1.0,
      "capital_flows": 0.9,
      "geographic_significance": 1.6,
      "counterparty_quality": 0.6,
      "temporal_relevance": 0.7
    },
    "article_targets": {
      "must_cover": 3,
      "strongly_recommended": 7,
      "brief_format": 10,
      "deal_tape": 10
    },
    "voice_mode": "analytical_regulatory",
    "subsectors": ["zoning", "permitting", "tax_increment", "municipal_bonds", "public_private_partnerships", "affordable_housing", "infrastructure_spending"]
  }
}
```

#### config/sectors.json
The sector and event-type taxonomy. Three-level hierarchy: sector → subsector → event_type.

```json
{
  "sectors": [
    {
      "id": "commercial_real_estate",
      "label": "Commercial Real Estate",
      "subsectors": [
        {"id": "office", "label": "Office", "event_types": ["lease", "sale", "financing", "development", "distress"]},
        {"id": "multifamily", "label": "Multifamily", "event_types": ["sale", "financing", "development", "regulatory"]},
        {"id": "industrial", "label": "Industrial", "event_types": ["lease", "sale", "development", "financing"]},
        {"id": "retail", "label": "Retail", "event_types": ["lease", "sale", "redevelopment", "distress"]},
        {"id": "hospitality", "label": "Hospitality", "event_types": ["sale", "financing", "development", "performance"]},
        {"id": "healthcare_re", "label": "Healthcare RE", "event_types": ["sale", "development", "lease"]},
        {"id": "life_sciences", "label": "Life Sciences", "event_types": ["lease", "development", "financing"]}
      ],
      "classification_signals": {
        "regex_patterns": [
          "\\b(commercial real estate|CRE|office building|industrial property|retail center|multifamily|apartment complex|hospitality asset)\\b",
          "\\b(square feet|sq ft|sf lease|rentable|occupancy rate|cap rate|NOI|net operating income)\\b",
          "\\b(CBRE|JLL|Cushman|Newmark|Colliers|Marcus Millichap|Eastdil|HFF)\\b"
        ],
        "exclusion_patterns": [
          "\\b(residential home|single.family home|primary residence)\\b"
        ],
        "priority_entities": [
          "Blackstone", "Brookfield", "Prologis", "Starwood", "Related Companies",
          "Tishman Speyer", "Boston Properties", "Kilroy", "Alexandria", "Hines"
        ]
      }
    },
    {
      "id": "private_equity",
      "label": "Private Equity",
      "subsectors": [
        {"id": "buyouts", "label": "Buyouts"},
        {"id": "growth_equity", "label": "Growth Equity"},
        {"id": "venture_capital", "label": "Venture Capital"},
        {"id": "fundraising", "label": "Fundraising"},
        {"id": "exits", "label": "Exits"},
        {"id": "secondaries", "label": "Secondaries"},
        {"id": "co_investment", "label": "Co-Investment"}
      ],
      "classification_signals": {
        "regex_patterns": [
          "\\b(private equity|PE firm|buyout|take.private|leveraged buyout|LBO|platform acquisition|add.on acquisition)\\b",
          "\\b(closed on|fund (IV|V|VI|VII|VIII|IX|X)|capital raise|committed capital|limited partner|lp commitment)\\b",
          "\\b(exit|IPO filing|strategic sale|secondary sale|dividend recap|recapitalization)\\b"
        ],
        "exclusion_patterns": [],
        "priority_entities": [
          "KKR", "Apollo", "Blackstone", "Carlyle", "TPG", "Thoma Bravo", "Silver Lake",
          "Vista Equity", "Bain Capital", "Warburg Pincus", "Advent", "Permira",
          "Ardian", "Lexington", "Hamilton Lane", "StepStone"
        ]
      }
    },
    {
      "id": "data_centers",
      "label": "Data Centers & Digital Infrastructure",
      "subsectors": [
        {"id": "hyperscale", "label": "Hyperscale"},
        {"id": "colocation", "label": "Colocation"},
        {"id": "edge_computing", "label": "Edge Computing"},
        {"id": "fiber_networks", "label": "Fiber Networks"},
        {"id": "power_procurement", "label": "Power Procurement"},
        {"id": "land_acquisition", "label": "Land Acquisition"}
      ],
      "classification_signals": {
        "regex_patterns": [
          "\\b(data center|datacentre|colocation|colo facility|hyperscale|hyperscaler|server farm)\\b",
          "\\b(megawatt|mw campus|critical power|power purchase agreement|ppa|renewable energy credit)\\b",
          "\\b(cloud region|availability zone|fiber route|subsea cable|interconnection|cross.connect)\\b"
        ],
        "exclusion_patterns": [
          "\\b(data center.*cloud migration|migrate.*to.*cloud|cloud.*migration strategy)\\b"
        ],
        "priority_entities": [
          "Equinix", "Digital Realty", "CyrusOne", "QTS", "CoreSite", "Vantage Data Centers",
          "Stack Infrastructure", "NTT Data Centers", "Iron Mountain", "DataBank", "EdgeConneX",
          "AWS", "Microsoft Azure", "Google Cloud", "Meta", "Apple"
        ]
      }
    },
    {
      "id": "energy_infrastructure",
      "label": "Energy & Infrastructure",
      "subsectors": [
        {"id": "renewable_energy", "label": "Renewable Energy"},
        {"id": "oil_gas", "label": "Oil & Gas"},
        {"id": "power_generation", "label": "Power Generation"},
        {"id": "transmission", "label": "Transmission"},
        {"id": "energy_storage", "label": "Energy Storage"},
        {"id": "infrastructure_finance", "label": "Infrastructure Finance"}
      ],
      "classification_signals": {
        "regex_patterns": [
          "\\b(solar farm|wind farm|battery storage|grid.interconnection|transmission line|pipeline|LNG|offshore wind)\\b",
          "\\b(gigawatt|megawatt hour|power plant|generation capacity|baseload|peaker plant)\\b",
          "\\b(energy transition|decarbonization|net.zero|IRA tax credit|production tax credit|investment tax credit)\\b"
        ],
        "exclusion_patterns": [
          "\\b(gas prices at.*pump|retail.*electricity.*bill)\\b"
        ],
        "priority_entities": [
          "NextEra", "Brookfield Renewable", "Invenergy", "Orsted", "Iberdrola", "Enel",
          "Pattern Energy", "Clearway", "AES", "Vistra", "Energy Transfer", "Kinder Morgan"
        ]
      }
    },
    {
      "id": "banking_credit",
      "label": "Banking & Credit Markets",
      "subsectors": [
        {"id": "commercial_lending", "label": "Commercial Lending"},
        {"id": "cmbs", "label": "CMBS"},
        {"id": "regulatory_capital", "label": "Regulatory Capital"},
        {"id": "m_and_a_advisory", "label": "M&A Advisory"},
        {"id": "distressed_debt", "label": "Distressed Debt"},
        {"id": "private_credit", "label": "Private Credit"}
      ],
      "classification_signals": {
        "regex_patterns": [
          "\\b(CMBS|commercial mortgage.backed|conduit loan|loan origination|balance sheet loan|portfolio lender)\\b",
          "\\b(Fed funds rate|Fed .* (hike|cut|hold)|monetary policy|base rate|SOFR|term SOFR|interest rate swap)\\b",
          "\\b(Basel III|Basel IV|capital requirement|stress test|CCAR|TLAC|GSIB surcharge)\\b"
        ],
        "exclusion_patterns": [
          "\\b(residential mortgage|mortgage rate.*homebuyer|consumer.*mortgage)\\b"
        ],
        "priority_entities": [
          "JPMorgan", "Goldman Sachs", "Morgan Stanley", "Bank of America", "Citigroup",
          "Wells Fargo", "Deutsche Bank", "Barclays", "UBS", "BNP Paribas",
          "Ares", "Oaktree", "Blue Owl", "HPS", "Goldman Alternatives"
        ]
      }
    },
    {
      "id": "federal_policy",
      "label": "Federal Policy & Regulatory",
      "subsectors": [
        {"id": "fomc", "label": "FOMC / Monetary"},
        {"id": "sec", "label": "SEC"},
        {"id": "cfpb", "label": "CFPB"},
        {"id": "treasury", "label": "Treasury"},
        {"id": "congressional", "label": "Congressional"},
        {"id": "tax_policy", "label": "Tax Policy"},
        {"id": "antitrust", "label": "Antitrust"}
      ],
      "classification_signals": {
        "regex_patterns": [
          "\\b(FOMC|Federal Open Market|Fed Chair|Federal Reserve.*(decision|statement|minutes))\\b",
          "\\b(SEC.*(rule|proposal|enforcement|fine|settlement)|registered offering|Form D|Form PF)\\b",
          "\\b(Treasury Department|Treasury Secretary|debt ceiling|Treasury issuance|Treasury auction)\\b",
          "\\b(Congress|Senate|House.*(passed|voted|bill|legislation|committee))\\b"
        ],
        "exclusion_patterns": [
          "\\b(political campaign|election|poll|approval rating)\\b"
        ],
        "priority_entities": [
          "Federal Reserve", "SEC", "CFPB", "FDIC", "OCC", "Treasury", "FHFA",
          "Jerome Powell", "Gary Gensler", "Janet Yellen"
        ]
      }
    },
    {
      "id": "local_government",
      "label": "Local Government & Municipal Finance",
      "subsectors": [
        {"id": "zoning", "label": "Zoning & Land Use"},
        {"id": "permitting", "label": "Permitting"},
        {"id": "tax_increment", "label": "Tax Increment Financing"},
        {"id": "municipal_bonds", "label": "Municipal Bonds"},
        {"id": "public_private_partnerships", "label": "Public-Private Partnerships"},
        {"id": "affordable_housing", "label": "Affordable Housing"},
        {"id": "infrastructure_spending", "label": "Infrastructure Spending"}
      ],
      "classification_signals": {
        "regex_patterns": [
          "\\b(city council|planning commission|zoning board|board of supervisors|mayor.*announced|municipal)\\b",
          "\\b(rezone|upzone|downzone|variance|conditional use permit|site plan approval|environmental impact report)\\b",
          "\\b(municipal bond|general obligation bond|revenue bond|TIF district|tax increment|special assessment)\\b"
        ],
        "exclusion_patterns": [
          "\\b(school board|pta meeting|neighborhood association)\\b",
          "\\b(local.*sports team|high school|community center.*event)\\b"
        ],
        "priority_entities": [
          "New York City", "San Francisco", "Los Angeles", "Chicago", "Washington DC",
          "Miami-Dade County", "Austin", "Seattle", "Denver", "Boston"
        ]
      }
    }
  ],
  "cross_sector_rules": {
    "description": "Rules for when a story could belong to multiple sectors",
    "default_behavior": "assign_primary_only",
    "allow_multi_label": true,
    "max_labels": 3,
    "entity_match_override": "If a priority entity from sector X appears in the title or first paragraph, sector X takes precedence over regex classification"
  }
}
```

#### config/watchlists.json
50+ tracked entities across all sectors. Structure:

```json
{
  "entities": [
    {
      "name": "Blackstone",
      "type": "asset_manager",
      "watch_reason": "Largest CRE owner globally, major PE activity",
      "aliases": ["Blackstone Real Estate", "Blackstone Group", "BX"],
      "primary_sectors": ["commercial_real_estate", "private_equity"],
      "watch_tier": "must_cover",
      "subsidiaries": ["Blackstone Mortgage Trust", "Blackstone Real Estate Income Trust", "Link Logistics"]
    },
    {
      "name": "Equinix",
      "type": "data_center_operator",
      "watch_reason": "Largest data center REIT globally",
      "aliases": ["EQIX", "Equinix Inc"],
      "primary_sectors": ["data_centers"],
      "watch_tier": "must_cover",
      "subsidiaries": []
    }
  ],
  "entity_boost_rules": {
    "description": "Stories mentioning a watched entity receive scoring boosts",
    "must_cover_entity": {"score_boost": 15, "minimum_evidence": "low"},
    "strongly_recommended_entity": {"score_boost": 10, "minimum_evidence": "low"},
    "standard_entity": {"score_boost": 5, "minimum_evidence": "medium"}
  }
}
```

Full entity list must include at least:
- CRE: Blackstone, Brookfield, Prologis, CBRE, JLL, Starwood, Related, Tishman Speyer (8)
- PE: KKR, Apollo, Carlyle, TPG, Thoma Bravo, Silver Lake, Vista Equity, Bain Capital, Warburg Pincus, Advent (10)
- Data Centers: Equinix, Digital Realty, CyrusOne, QTS, CoreSite, Vantage, Stack Infrastructure (7)
- Energy: NextEra, Brookfield Renewable, Invenergy, Orsted, Iberdrola, Enel, Pattern Energy (7)
- Banking: JPMorgan, Goldman Sachs, Morgan Stanley, Bank of America, Citigroup, Wells Fargo (6)
- Federal Policy: Federal Reserve, SEC, CFTC, Treasury, CFPB (5)
- Local Government: NYC, SF, LA, Chicago, DC, Miami-Dade, Austin (7)

#### config/thresholds.json
Tier boundaries and article targets:

```json
{
  "tier_definitions": {
    "must_cover": {"min_score": 85, "per_sector_max": 5, "evidence_requirement": "low", "label": "Must Cover"},
    "strongly_recommended": {"min_score": 70, "per_sector_max": 10, "evidence_requirement": "medium", "label": "Strongly Recommended"},
    "brief_format": {"min_score": 55, "per_sector_max": 15, "evidence_requirement": "medium", "label": "Brief"},
    "deal_tape": {"min_score": 40, "per_sector_max": 30, "evidence_requirement": "low", "label": "Deal Tape"},
    "rejected": {"min_score": 0, "per_sector_max": null, "evidence_requirement": null, "label": "Rejected"}
  },
  "per_sector_targets": {
    "articles_per_sector": 30,
    "minimum_articles_per_sector": 15,
    "maximum_articles_per_sector": 45
  },
  "signal_gate": {
    "description": "Minimum criteria before scoring. Stories below these thresholds are filtered out.",
    "minimum_source_tier": "tier_3",
    "minimum_entity_count": 0,
    "minimum_content_length": 150,
    "maximum_article_age_hours": 48,
    "require_english": true,
    "disallow_duplicate_titles": true,
    "auto_reject_categories": ["sports", "entertainment", "lifestyle", "opinion", "weather"]
  },
  "diversity_controls": {
    "max_consecutive_same_source": 3,
    "max_articles_per_source_per_sector": 8,
    "min_unique_sources_per_sector": 5,
    "max_articles_per_entity_per_day": 4
  },
  "cost_limits": {
    "max_daily_cost_usd": 3.00,
    "max_monthly_cost_usd": 90.00,
    "max_llm_calls_per_classification": 0.15,
    "max_llm_calls_per_generation": 0.02
  }
}
```

### 1.2 Create scripts/canonical_item.py

Define the `Item` dataclass with all fields from mandate Section VI. This is the single canonical format that every story passes through regardless of source or sector.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict

@dataclass
class Item:
    # --- Source & Identity ---
    item_id: str                          # UUID v4, assigned at ingestion
    source_id: str                        # maps to config/sources.json entry
    source_name: str                      # human-readable source name
    source_url: str                       # the feed URL that produced this item
    original_url: str                     # permalink to the original article

    # --- Content ---
    title: str
    description: Optional[str] = None     # RSS description or first paragraph
    full_text: Optional[str] = None       # trafilatura-extracted full text
    published_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None

    # --- Classification ---
    primary_sector: Optional[str] = None  # e.g., "private_equity"
    secondary_sectors: List[str] = field(default_factory=list)
    primary_subsector: Optional[str] = None
    event_type: Optional[str] = None
    classification_method: Optional[str] = None  # "source_prior", "regex_signals", "entity_match", "llm"
    classification_confidence: float = 0.0  # 0.0 to 1.0

    # --- Entity Extraction ---
    entities_mentioned: List[str] = field(default_factory=list)
    entity_count: int = 0
    has_watched_entity: bool = False
    watched_entities: List[str] = field(default_factory=list)

    # --- Scoring ---
    raw_score: float = 0.0               # pre-weight composite
    weighted_score: float = 0.0          # post-sector-weight composite
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    scoring_profile_used: Optional[str] = None

    # --- Ranking ---
    sector_rank: Optional[int] = None    # rank within primary sector
    tier: Optional[str] = None           # "must_cover", "strongly_recommended", etc.
    selection_status: Optional[str] = None  # "selected", "alternate", "rejected"
    rejection_reason: Optional[str] = None

    # --- Enrichment ---
    evidence_sources: List[str] = field(default_factory=list)
    evidence_level: str = "none"         # "none", "low", "medium", "high", "exhaustive"
    market_data: Optional[Dict] = None   # structured market data extracted
    related_items: List[str] = field(default_factory=list)  # item_ids of related stories

    # --- Event Clustering ---
    cluster_id: Optional[str] = None
    is_cluster_representative: bool = False

    # --- Generation ---
    article_generated: bool = False
    article_id: Optional[str] = None
    article_type: Optional[str] = None   # "flagship", "transaction_brief", "policy_analysis", etc.
    generation_status: Optional[str] = None  # "pending", "success", "failed", "retrying"
    generation_error: Optional[str] = None
    word_count: Optional[int] = None
    llm_model_used: Optional[str] = None
    llm_tokens_used: Optional[int] = None
    generation_cost_usd: Optional[float] = None

    # --- Publishing ---
    published: bool = False
    published_at: Optional[datetime] = None
    published_url: Optional[str] = None
    manifest_entry: Optional[Dict] = None

    # --- Metadata ---
    tags: List[str] = field(default_factory=list)
    language: str = "en"
    content_hash: Optional[str] = None   # deduplication hash
    version: int = 1                     # incremented on regeneration

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict for checkpoint/persistence."""
        ...

    @classmethod
    def from_dict(cls, data: dict) -> "Item":
        """Deserialize from dict."""
        ...

    def validate(self) -> List[str]:
        """Return list of validation errors."""
        ...
```

### 1.3 Create scripts/classification.py

Multi-label classifier with cascading strategy:

1. **Source-based prior** — A story from a source tagged `sector: "private_equity"` with `sector_weight: 1.0` is auto-classified as private_equity with confidence 0.95. Cross-sector sources (sector_weight < 0.7) skip this step.

2. **Regex signal matching** — Apply the `classification_signals.regex_patterns` from each sector profile. Score each sector by the count and specificity of matches. Apply `exclusion_patterns` to veto false positives. If one sector's signal score exceeds others by 2x, classify with confidence 0.85. If no clear winner, proceed to step 3.

3. **Entity matching** — Check for `priority_entities` from each sector in the title and description. If a priority entity is found, boost that sector. If multiple entity classes appear (e.g., an Apollo + Equinix article), consider multi-label classification.

4. **LLM classification** (fallback only) — For stories where steps 1-3 produce low-confidence or multi-way ties. Send title + description to DeepSeek with a classification prompt that returns JSON: `{"primary_sector": "...", "secondary_sectors": [...], "confidence": 0.X, "reasoning": "..."}`. Cache LLM classification results by content_hash to avoid duplicate calls.

5. **Confidence assignment**: source_prior = 0.95, regex_signals = 0.80–0.92, entity_match = 0.75–0.88, llm = 0.60–0.85.

**Key design constraint:** This module does NOT modify the existing pipeline. It is imported by Phase 2's ingestion.py and runs independently. Existing editorial_intelligence.py continues to function during Phase 1.

### 1.4 Create scripts/scoring_engine.py

Loads `config/scoring_profiles.json` and computes 10 dimensions × sector weights.

The 10 scoring dimensions (detailed in 06-scoring-spec):

1. **Transaction Significance** (0-20): Deal size, transaction type, market impact.
2. **Market Movement** (0-20): Price changes, volume anomalies, sector-wide trends.
3. **Policy Impact** (0-20): Regulatory, legislative, or judicial actions with sector consequences.
4. **Entity Prominence** (0-20): Whether key institutions or individuals are involved (watchlist lookup).
5. **Narrative Value** (0-20): Story quality, conflict, surprise, human angle.
6. **Sector Urgency** (0-20): Time-sensitivity (deadlines, expirations, imminent decisions).
7. **Capital Flows** (0-20): Volume of capital committed, raised, deployed, or at risk.
8. **Geographic Significance** (0-20): Market size, regulatory jurisdiction importance.
9. **Counterparty Quality** (0-20): Sophistication and credibility of parties involved.
10. **Temporal Relevance** (0-20): Freshness decay (published_at vs. now).

```python
def score_item(item: Item) -> Item:
    profile = load_scoring_profile(item.primary_sector)
    dimensions = {
        "transaction_significance": compute_transaction_significance(item),
        "market_movement": compute_market_movement(item),
        "policy_impact": compute_policy_impact(item),
        "entity_prominence": compute_entity_prominence(item),
        "narrative_value": compute_narrative_value(item),
        "sector_urgency": compute_sector_urgency(item),
        "capital_flows": compute_capital_flows(item),
        "geographic_significance": compute_geographic_significance(item),
        "counterparty_quality": compute_counterparty_quality(item),
        "temporal_relevance": compute_temporal_relevance(item)
    }
    item.dimension_scores = dimensions
    item.raw_score = sum(dimensions.values())
    item.weighted_score = sum(
        dimensions[dim] * profile["weights"][dim]
        for dim in dimensions
    )
    item.scoring_profile_used = item.primary_sector
    return item
```

Some dimension scorers can be deterministic (temporal_relevance: hours_since_publish → score). Entity prominence uses watchlist lookup. Narrative value and market movement may require LLM scoring for Tier 1-2 candidates.

### 1.5 Write Unit Tests

Test file: `tests/test_canonical_item.py`, `tests/test_classification.py`, `tests/test_scoring_engine.py`.

- **canonical_item tests**: Construction, serialization/deserialization round-trip, validation (required fields, type checks).
- **classification tests**: Known inputs produce expected sector labels. Source-based classification. Regex pattern matching. Entity matching. Multi-label scenarios. Exclusion patterns. LLM fallback (mock).
- **scoring_engine tests**: Known entity produces expected entity_prominence score. Recent vs. old article temporal_relevance. Edge cases: empty item, missing fields, unknown sector.

Minimum coverage: 80% line coverage per module.

### 1.6 Shadow Mode Validation

Run the full Phase 1 pipeline against existing editorial run data. The existing pipeline produces `bounties.json` or equivalent. Feed past run data through classification.py and scoring_engine.py. Validate:

- Classification accuracy: Spot-check 100 classified items. Compare against human judgment. Target: >90% accuracy for source-based and regex classification. >75% for LLM fallback.
- Scoring reasonableness: Top-30 items per sector should be intuitively the most important stories.
- Performance: Classification of 2000 items < 30 seconds. Scoring of 2000 items < 60 seconds.

**Phase 1 Deliverables:**
- `config/sources.json` (~205 entries)
- `config/scoring_profiles.json` (7 profiles)
- `config/sectors.json` (7 sectors, 40+ subsectors)
- `config/watchlists.json` (50+ entities)
- `config/thresholds.json` (complete tier structure)
- `scripts/canonical_item.py`
- `scripts/classification.py`
- `scripts/scoring_engine.py`
- `tests/test_canonical_item.py`
- `tests/test_classification.py`
- `tests/test_scoring_engine.py`
- Shadow run validation report

---

## Phase 2: Ingestion Expansion (Week 2)

**Goal:** Expand source universe from ~90 CRE feeds to 200+ feeds across 7 sectors. Classification runs on all stories.

### 2.1 Add New Feeds to sources.json

Add 100+ new feeds from the proposed source registry (05-source-registry.md). Prioritization:

1. **Private Equity** (first priority — highest overlap with existing CRE readership): PE Hub, Buyouts, PitchBook News, Axios Pro Rata, Fortune Term Sheet, Institutional Investor, Preqin Insights, Secondaries Investor, PEI News, AltAssets.
2. **Data Centers** (second — high growth, news-rich sector): Data Center Dynamics, Data Center Frontier, Data Center Knowledge, Light Reading, Fierce Telecom, Capacity Media, JSA News.
3. **Energy Infrastructure** (third — policy-heavy, high-impact): Utility Dive, S&P Global Platts, RTO Insider, E&E News, Greentech Media, Recharge News, Power Magazine, Hart Energy.
4. **Banking/Credit** (fourth): Reuters Finance, Bloomberg Banking, American Banker, Risk.net, Structured Finance News, Commercial Mortgage Alert, Private Debt Investor, LevFin Insights.
5. **Local Government** (fifth — hardest to source): NYC Department of City Planning, SF Planning Department, LA City Planning, Chicago City Clerk, DC Office of Zoning, Austin Build + Connect.

Each new feed entry must include:
- Verification that the RSS feed URL is valid (manual check).
- Mark `"needs_verification": true` for any unconfirmed feeds.
- A realistic `fetch_frequency` (not all feeds update daily).

### 2.2 Create scripts/ingestion.py

Refactored ingestion layer:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import feedparser
import trafilatura
import hashlib
import uuid
from datetime import datetime, timezone
from config.sources import load_sources
from scripts.canonical_item import Item
from scripts.classification import classify_item
import logging

MAX_WORKERS = 10
REQUEST_TIMEOUT = 15  # seconds
MAX_RETRIES = 2

def run_ingestion(sector_filter: Optional[str] = None) -> List[Item]:
    """
    Fetch all active sources, normalize to canonical Items.
    If sector_filter is provided, only fetch sources for that sector.
    """
    sources = load_sources(active_only=True, sector=sector_filter)
    items = []
    source_health = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_source = {
            executor.submit(fetch_source, src): src
            for src in sources
        }
        for future in as_completed(future_to_source):
            src = future_to_source[future]
            try:
                source_items, health = future.result(timeout=60)
                items.extend(source_items)
                source_health[src["id"]] = health
            except Exception as e:
                logging.error(f"Source {src['id']} failed: {e}")
                source_health[src["id"]] = {"status": "failed", "error": str(e)}

    # Classify all items
    for item in items:
        item = classify_item(item)

    # Update source health with sector coverage stats
    update_source_health_sector_stats(source_health, items)

    return items


def fetch_source(source: dict) -> Tuple[List[Item], dict]:
    """Fetch one RSS/Atom feed and normalize to Items."""
    items = []
    health = {"status": "success", "items_fetched": 0, "items_parsed": 0,
              "fetch_time_ms": 0, "error": None}

    start = time.time()
    try:
        feed = feedparser.parse(source["url"])
        health["items_fetched"] = len(feed.entries)

        for entry in feed.entries:
            try:
                item = normalize_entry(entry, source)
                items.append(item)
                health["items_parsed"] += 1
            except Exception as e:
                logging.warning(f"Failed to parse entry from {source['id']}: {e}")

    except Exception as e:
        health["status"] = "failed"
        health["error"] = str(e)

    health["fetch_time_ms"] = int((time.time() - start) * 1000)
    return items, health


def normalize_entry(entry: dict, source: dict) -> Item:
    """Convert feedparser entry + source config into canonical Item."""
    title = entry.get("title", "").strip()
    description = entry.get("summary", entry.get("description", ""))
    # Strip HTML from description
    if description:
        from html import unescape
        import re
        description = re.sub(r'<[^>]+>', '', description)
        description = unescape(description).strip()

    published = None
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
        published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

    link = entry.get("link", "")

    content_hash = hashlib.sha256(
        (source["id"] + title + (link or "")).encode()
    ).hexdigest()[:16]

    return Item(
        item_id=str(uuid.uuid4()),
        source_id=source["id"],
        source_name=source["name"],
        source_url=source["url"],
        original_url=link,
        title=title,
        description=description,
        published_at=published,
        fetched_at=datetime.now(timezone.utc),
        content_hash=content_hash,
        language=source.get("language", "en")
    )
```

### 2.3 Wire Classification into Pipeline

Every fetched item gets classified by `classification.py` immediately after normalization in `run_ingestion()`. The classification result (primary_sector, classification_method, classification_confidence) is stored on the Item.

### 2.4 Per-Source Sector Tracking

Add to source_health.json after each run:

```json
{
  "bisnow-national": {
    "status": "success",
    "items_fetched": 42,
    "items_parsed": 41,
    "classified_items": 41,
    "sector_distribution": {
      "commercial_real_estate": 38,
      "private_equity": 2,
      "banking_credit": 1
    },
    "fetch_time_ms": 3421,
    "consecutive_failures": 0,
    "last_success": "2026-07-30T06:00:00Z"
  }
}
```

### 2.5 Shadow Run Validation

Run full ingestion + classification in shadow mode (do not write output). Verify:
- Stories from all 7 sectors are successfully ingested.
- Classification accuracy across 200+ feeds: Spot-check at least 50 stories per new sector.
- No source produces 100% classification failures.

### 2.6 Adjust Based on Shadow Results

- Tune regex patterns for sectors with low classification confidence.
- Add entity aliases to watchlists.json for entities that are frequently mentioned but not recognized.
- Disable sources with persistent failures (>3 consecutive).
- Reduce LLM fallback usage if deterministic methods are sufficient.

**Phase 2 Deliverables:**
- Updated `config/sources.json` with 200+ feeds
- `scripts/ingestion.py`
- `source_health.json` auto-generation
- Shadow run report showing items per sector, classification accuracy per sector

---

## Phase 3: Scoring and Ranking (Week 3)

**Goal:** The scoring engine runs on all classified items. Rankings are produced per sector.

### 3.1 Wire Scoring into Pipeline

Every classified item from `run_ingestion()` now passes through `score_item()` from scoring_engine.py. The item's `primary_sector` determines which scoring profile is used.

```python
# In the pipeline runner:
items = run_ingestion()
for item in items:
    if item.primary_sector:
        item = score_item(item)
```

Items without a primary_sector (classification failed entirely) are logged to `unclassified.json` and skipped.

### 3.2 Create scripts/ranking.py

Within-sector ranking, diversity controls, and tier assignment.

```python
def rank_sector(items: List[Item], sector: str, config: dict) -> List[Item]:
    """
    Rank items within a sector. Apply diversity controls.
    Assign tiers. Return top N per sector target.
    """
    sector_items = [i for i in items if i.primary_sector == sector]
    sector_items.sort(key=lambda i: i.weighted_score, reverse=True)

    diversity_config = config["diversity_controls"]
    tier_config = config["tier_definitions"]
    target = config["per_sector_targets"]["articles_per_sector"]

    ranked = []
    source_counts = {}
    entity_counts = {}
    consecutive_source = {"source_id": None, "count": 0}

    for rank_idx, item in enumerate(sector_items):
        # Apply tier assignment based on weighted_score
        item.sector_rank = rank_idx + 1

        # Tier assignment
        if item.weighted_score >= tier_config["must_cover"]["min_score"]:
            item.tier = "must_cover"
        elif item.weighted_score >= tier_config["strongly_recommended"]["min_score"]:
            item.tier = "strongly_recommended"
        elif item.weighted_score >= tier_config["brief_format"]["min_score"]:
            item.tier = "brief_format"
        elif item.weighted_score >= tier_config["deal_tape"]["min_score"]:
            item.tier = "deal_tape"
        else:
            item.tier = "rejected"
            item.selection_status = "rejected"
            item.rejection_reason = f"Score {item.weighted_score:.1f} below deal_tape threshold {tier_config['deal_tape']['min_score']}"

        # Diversity: max consecutive same source
        if item.source_id == consecutive_source["source_id"]:
            consecutive_source["count"] += 1
        else:
            consecutive_source = {"source_id": item.source_id, "count": 1}

        if consecutive_source["count"] > diversity_config["max_consecutive_same_source"]:
            item.selection_status = "rejected"
            item.rejection_reason = f"Diversity: exceeded max_consecutive_same_source ({diversity_config['max_consecutive_same_source']})"
            continue

        # Diversity: max per source per sector
        src_count = source_counts.get(item.source_id, 0)
        if src_count >= diversity_config["max_articles_per_source_per_sector"]:
            item.selection_status = "rejected"
            item.rejection_reason = f"Diversity: source {item.source_id} at max articles ({diversity_config['max_articles_per_source_per_sector']})"
            continue

        # Diversity: max per entity per day
        for entity in item.watched_entities:
            ent_count = entity_counts.get(entity, 0)
            if ent_count >= diversity_config["max_articles_per_entity_per_day"]:
                item.selection_status = "rejected"
                item.rejection_reason = f"Diversity: entity {entity} at max articles ({diversity_config['max_articles_per_entity_per_day']})"
                break
        else:
            ranked.append(item)
            item.selection_status = "selected"
            source_counts[item.source_id] = src_count + 1
            for entity in item.watched_entities:
                entity_counts[entity] = entity_counts.get(entity, 0) + 1

    # Truncate to target
    selected = ranked[:target]
    alternates = ranked[target:target + 20]

    for item in selected:
        # Already have selection_status = "selected"
        pass
    for item in alternates:
        item.selection_status = "alternate"

    return selected, alternates
```

### 3.3 Sector-Aware Event Clustering

Extend `editorial_intelligence.py` event clustering to be sector-aware:
- Stories in different primary sectors are NOT clustered together unless they share watched entities.
- Clusters that span sectors generate a "cross-sector" tag.
- Cluster representatives are selected per sector (each sector in a cross-sector cluster gets its own representative).

### 3.4 Shadow Run (3-5 Days)

Run full pipeline in shadow mode for 3-5 days:
- Every step runs: ingestion → classification → scoring → ranking.
- Output is written to `shadow_output.json` but NOT to production manifests or RSS feeds.
- Monitor per-sector article counts, classification accuracy, and scoring distributions daily.

### 3.5 Manual Review of Top-30 Selections

For each sector, manually review the top 30 ranked items:
- Does the ranking make intuitive sense?
- Are any obviously important stories ranked low? (Inspect scoring breakdowns.)
- Are any trivial stories ranked high? (Adjust weights downward.)
- Are rejected stories correctly rejected? (Check rejection_reason.)

### 3.6 Document Rejection Reasons

Generate a daily `rejection_report.json`:

```json
{
  "date": "2026-07-30",
  "total_candidates": 2150,
  "total_classified": 1980,
  "total_selected": 210,
  "total_rejected": 1770,
  "rejection_by_reason": {
    "score_below_threshold": 980,
    "diversity_max_consecutive_source": 145,
    "diversity_max_per_source_per_sector": 220,
    "diversity_max_per_entity_per_day": 85,
    "content_hash_duplicate": 120,
    "age_exceeds_maximum": 95,
    "source_tier_too_low": 80,
    "auto_reject_category": 30,
    "manual_reject": 15
  },
  "rejection_by_sector": {
    "commercial_real_estate": 340,
    "private_equity": 310,
    "data_centers": 280,
    "energy_infrastructure": 260,
    "banking_credit": 300,
    "federal_policy": 150,
    "local_government": 130
  }
}
```

**Phase 3 Deliverables:**
- `scripts/ranking.py`
- Sector-aware event clustering in editorial_intelligence.py
- Shadow run reports for 3-5 days (per-sector rankings, rejection reasons)
- Manual review summary with scoring weight adjustment recommendations

---

## Phase 4: Generation and Publishing (Week 4)

**Goal:** The generation module writes articles for selected stories. The publishing module outputs to sector feeds.

### 4.1 Create Sector-Specific Writing Prompts

The existing `enhanced_prompts.py` has CRE-centric prompts. Create 6 new system prompts:

- `pe_system_prompt`: Focus on fund metrics (IRR, MOIC, DPI), firm strategy, LP dynamics, deal structure, carry waterfalls. Voice: confident, dealmaker tone. Key terms: buyout, add-on, platform, fundraising, exit, secondary, LP, GP.
- `dc_system_prompt`: Focus on megawatts, power procurement, hyperscale tenant activity, interconnection, sustainability. Voice: technical but accessible. Key terms: MW, PPA, colocation, fiber, latency, cloud on-ramp.
- `energy_system_prompt`: Focus on generation capacity, regulatory approvals, PPA structures, tax equity, interconnection queues. Voice: analytical regulatory. Key terms: GW, ITC, PTC, RPS, PURPA, FERC.
- `banking_system_prompt`: Focus on regulatory capital, loan origination, CMBS issuance, funding costs, credit quality. Voice: institutional analytical. Key terms: SOFR, LTV, DSCR, CET1, RWAs, NII.
- `fed_system_prompt`: Focus on FOMC decisions, regulatory rulemaking, enforcement actions, legislative impacts. Voice: measured, factual, policy-literate. Key terms: basis points, dual mandate, comment period, final rule, Federal Register.
- `localgov_system_prompt`: Focus on zoning changes, permit approvals, TIF districts, bond issuances, public-private partnerships. Voice: civic analytical. Key terms: upzoning, variance, NEPA, CEQA, general plan, RFP.

Each prompt must include:
- Article format instructions (headline, deck, body, source attribution, disclaimer).
- Tone and style guidelines.
- Required structural elements (the "why it matters" paragraph, the "what to watch" section).
- Prohibitions (no speculation, no investment advice, no political opinion).
- Examples of good output.

### 4.2 Create scripts/generation.py

Sector-aware article generation:

```python
def generate_article(item: Item) -> Item:
    """Route item to the correct prompt and generate an article."""
    sector = item.primary_sector
    prompt = load_prompt(sector, item.article_type)
    dossier = build_dossier(item)

    # Select article type based on tier + event_type
    if item.tier == "must_cover":
        item.article_type = "flagship" if item.evidence_level in ("high", "exhaustive") else "analysis"
    elif item.tier == "strongly_recommended":
        item.article_type = "analysis" if item.event_type in ("financing", "policy", "regulatory") else "transaction_brief"
    elif item.tier == "brief_format":
        item.article_type = "transaction_brief"
    elif item.tier == "deal_tape":
        item.article_type = "deal_tape"

    try:
        result = call_llm(prompt, dossier)
        item.article_generated = True
        item.generation_status = "success"
        item.word_count = len(result["body"].split())
        item.llm_model_used = result["model"]
        item.llm_tokens_used = result["tokens"]
        item.generation_cost_usd = estimate_cost(result)
        return item
    except Exception as e:
        item.generation_status = "failed"
        item.generation_error = str(e)
        return item
```

### 4.3 Create scripts/publishing.py

Multi-sector publishing:

```python
def publish_sector(items: List[Item], sector: str):
    """Publish all articles for a given sector."""
    # Filter to selected items for this sector
    sector_items = [i for i in items
                    if i.primary_sector == sector
                    and i.selection_status == "selected"
                    and i.article_generated]

    # Generate HTML for each article
    for item in sector_items:
        html = render_article_html(item)
        write_article_file(item, html)

    # Update sector manifest
    update_sector_manifest(sector, sector_items)

    # Update RSS feed
    generate_sector_rss(sector, sector_items)

    # Update sitemap
    update_sector_sitemap(sector, sector_items)

    # Update sector index
    update_sector_landing_page(sector, sector_items)
```

### 4.4 Create 7 Sector Landing Pages on insights.html

Update `insights.html` with:
- Filter buttons for each sector: CRE, PE, Data Centers, Energy, Banking, Federal Policy, Local Gov.
- Sub-sector dropdowns within each filter.
- Default view: "All Sectors" sorted by recency.
- Sector tabs showing: sector name, article count today, top 3 headlines.
- Infinite scroll or "Load More" for each sector (210 articles/day requires pagination).

### 4.5 Preview Mode Run

Run end-to-end in preview mode (generate articles but write to `preview/` directory, not production). Review:
- Article quality per sector (spot-check 5-10 per sector).
- Generation success rate (target >95%).
- Publishing correctness (all manifest entries, RSS items, sitemap entries valid).

### 4.6 Fix Issues

- Regenerate prompts for sectors with low-quality output.
- Fix generation failures (timeout, content too long, prompt confusion).
- Fix publishing errors (broken URLs, missing metadata).

**Phase 4 Deliverables:**
- 6 new system prompts (PE, DC, Energy, Banking, Fed, LocalGov)
- `scripts/generation.py`
- `scripts/publishing.py`
- Updated `insights.html` with sector filters
- Preview mode output and quality review report

---

## Phase 5: Cutover and Monitoring (Week 5)

**Goal:** Full cutover to the multi-sector engine. Old single-edition pipeline deprecated.

### 5.1 Enable Full Publishing

Remove the "preview mode" flag. Publishing writes to production:
- Articles go to `insights/<sector>/<article_id>.html`.
- Manifests update `insights/<sector>/manifest.json`.
- RSS feeds: `insights/<sector>/feed.xml`.
- Sitemap: updated with all 7 sector entries.
- Main `insights.html` shows all sector filters.

Back up the old single-edition pipeline files. Do not delete them yet (rollback capability).

### 5.2 Create scripts/admin_dashboard.py

Backend for the admin dashboard. Exposes:

- Per-sector output tracking: articles published today, this week, this month.
- Source health: up/down status, success rate, items fetched.
- Cost monitoring: daily total, per-sector breakdown, per-article average, projected monthly.
- Story drill-down: searchable list of all classified items with filters (sector, tier, status, source).
- Pipeline run history: timestamps, durations, phase results, errors.
- LLM usage stats: calls by phase, tokens consumed, cost.

Expose as JSON endpoints (or write to static files that `insights-admin.html` reads).

### 5.3 Add Admin Controls to insights-admin.html

Add interactive controls:
- Scoring weight sliders per dimension per sector (write changes to config/scoring_profiles.json).
- Promote/reject buttons on individual stories in candidate pool.
- Reprocess button for failed items.
- Merge story clusters (select items, click "Merge", system creates a single article covering the cluster).
- Review queue: all "flagged for review" stories (litigation, criminal, bankruptcy keywords).
- Approval workflow: all flagship articles must be approved before publishing.

### 5.4 Production Monitoring (5 Days)

Monitor daily:
1. **Volume**: Articles per sector. Are all sectors hitting minimum targets? Is any sector dominating?
2. **Quality**: Randomly spot-check 10 articles/day. Use a simple rubric: accuracy, relevance, readability, structure.
3. **Failures**: Generation failure rate. Ingestion source failure rate. Classification failures.
4. **Cost**: Daily cost vs. projections. Which phase costs most?
5. **Performance**: Pipeline runtime vs. 6-hour limit.
6. **Reader engagement**: If analytics are available — click-through rates, time on page, sector popularity.

### 5.5 Tune Based on Production Data

- Adjust scoring weights if some sectors consistently produce low-scoring candidates.
- Adjust per-sector article targets if some sectors consistently have more/less news than expected.
- Disable consistently failing sources.
- Adjust cost caps if actual costs differ from estimates.

### 5.6 Document Rollback Procedure

Create `ROLLBACK.md`:

1. Stop the GitHub Actions workflow (disable in repository settings).
2. Restore old single-edition pipeline from backup.
3. Re-enable the old workflow.
4. Revert `insights.html` to single-edition view (remove sector filters).
5. Notify stakeholders that multi-sector experiment is paused.
6. Investigate failure root cause.
7. Do NOT delete multi-sector output — it can be re-enabled once root cause is fixed.

**Phase 5 Deliverables:**
- `scripts/admin_dashboard.py`
- Updated `insights-admin.html` with admin controls
- 5-day production monitoring report
- `ROLLBACK.md`

---

## Phase 6: Continuous Improvement (Ongoing)

### 6.1 Monthly Scoring Recalibration

Based on reader engagement data:
- Track which articles get clicks and which don't. If "strongly_recommended" PE articles consistently outperform PE "must_cover" articles, adjust weightings.
- Identify scoring dimensions that don't correlate with engagement — reduce their weight.

### 6.2 A/B Testing

- Headline variants: Test different headline styles per sector.
- CTA variants: "Read the Full Analysis" vs. "See Deal Details" vs. sector-specific CTAs.
- Article length: Test brief vs. flagship length for upper-tier stories.

### 6.3 Source Expansion

- Continuously add new feeds as they become available.
- Remove feeds that have been consistently down for 30+ days.
- Explore premium API sources if budget allows (PitchBook API, Preqin API).

### 6.4 Local Government Coverage

- Municipal RSS feeds are the hardest category. Develop scrapers for high-priority jurisdictions that only publish via web pages or PDFs.
- Partner with local news aggregators if possible.

### 6.5 SQLite Migration (When Article Count > 5000)

The current JSON-file persistence model breaks down at scale. Migrate to SQLite:
- tables: items, articles, sources, pipeline_runs, costs, watchlists.
- Benefits: queryable history, faster lookups, smaller disk footprint, transactions.
- Keep JSON export as backup/portability format.

### 6.6 Distributed Workers (If Latency > 4 Hours)

If single-run latency exceeds 4 hours:
- Split the GitHub Actions workflow into separate jobs with artifact passing.
- Job 1: Ingestion + Classification.
- Job 2: Scoring + Ranking.
- Job 3: Generation.
- Job 4: Publishing.
- Each job passes artifacts (JSON files) via GitHub Actions artifact upload/download.
- Alternatively: explore GitHub Actions larger runners (more CPU/memory).

### 6.7 Automated Quality Regression Tests

Maintain a "golden set" of 50 articles across all sectors representing target quality. After any prompt change, regenerate these articles and compare against the golden set using automated similarity and quality metrics.

---

## Timeline Summary

| Phase | Duration | Key Output | Cumulative Items |
|-------|----------|------------|------------------|
| 1: Foundation | Week 1 | Config + data model + shadow validation | ~500 lines of config + 3 modules |
| 2: Ingestion | Week 2 | 200+ feeds + classification on all | Full ingestion running |
| 3: Scoring/Ranking | Week 3 | Per-sector rankings + manual review | Full pipeline in shadow |
| 4: Generation/Publishing | Week 4 | Sector prompts + preview output | Full pipeline previewing |
| 5: Cutover | Week 5 | Production + admin dashboard | Live multi-sector engine |
| 6: Continuous | Ongoing | Iterative improvements | Sustained operation |

---

## Dependency Graph

```
Phase 1 (Foundation)
    │
    ├── canonical_item.py ──────────────────────────────┐
    ├── classification.py ──────────────────────────────┤
    │                                                   │
    ▼                                                   │
Phase 2 (Ingestion)                                     │
    │                                                   │
    ├── ingestion.py ───────────────────────────────────┤
    │       │                                           │
    │       └── classification.py (integrated) ────────┤
    │                                                   │
    ▼                                                   ▼
Phase 3 (Scoring/Ranking)
    │
    ├── scoring_engine.py (integrated with ingestion)
    ├── ranking.py
    │
    ▼
Phase 4 (Generation/Publishing)
    │
    ├── generation.py
    ├── publishing.py
    │
    ▼
Phase 5 (Cutover)
    │
    ├── admin_dashboard.py
    └── insights-admin.html
```

## Go/No-Go Gates

| Gate | After Phase | Criteria |
|------|------------|----------|
| Proceed to Phase 2 | Phase 1 | Classification accuracy >85%. Scoring produces reasonable rankings. |
| Proceed to Phase 3 | Phase 2 | All 7 sectors have >50 classified items/day. Source failure rate <40%. |
| Proceed to Phase 4 | Phase 3 | Manual review confirms top-30 rankings are defensible per sector. Rejection reasons valid. |
| Proceed to Phase 5 | Phase 4 | Preview articles pass quality review. >95% generation success rate. Publishing correct. |
| Stay in Production | Phase 5 | 5-day monitoring shows stable operation. Cost within budget. |
