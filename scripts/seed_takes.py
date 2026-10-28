#!/usr/bin/env python3
"""Seed and synchronize /takes.json with multi-sector Quick Takes + NYC $10M+ Deal Takes.

Every take adheres strictly to scripts/takes.py contracts:
- Schema version: "takes-1"
- At most 5 lines and at most 450 characters per take (including every alternate angle)
- Zero URLs, zero hashtags, zero emojis, zero banned cliches
- 3 distinct angles per story (primary take + 2 alternates) so the 'Another angle' button
  on https://lighttowergroup.co/insights.html#takes cycles through 3 sharp variations.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import takes as takes_mod  # noqa: E402
from nyc_transactions.economics import compute_economics  # noqa: E402
from nyc_transactions.generation import _clean_entity_name, _slugify, render_literary_story  # noqa: E402
from nyc_transactions.sources import get_curated_nyc_transactions  # noqa: E402


MULTI_SECTOR_TAKES: list[dict[str, Any]] = [
    {
        "object_id": "related-lands-750m-wells-fargo-loan-on-manhattan-plaza",
        "date": "2026-10-21",
        "sector": "commercial_real_estate",
        "score": 96.0,
        "title": "Related Lands $750M Wells Fargo Loan on Manhattan Plaza",
        "article_url": "https://lighttowergroup.co/insights/related-lands-750m-wells-fargo-loan-on-manhattan-plaza.html",
        "formula": "Two Numbers, One Story",
        "lines": [
            {"kind": "fact", "text": "Related Companies closed a $750M Wells Fargo loan on Manhattan Plaza, retiring a $450M Fannie Mae note."},
            {"kind": "fact", "text": "The 1,689-unit affordable complex spans a full West Side block at 400 West 43rd Street."},
            {"kind": "read", "text": "I read a $300M proceeds step-up on regulated housing as proof that major banks still stretch for fortress sponsorship."},
            {"kind": "kicker", "text": "Liquidity has not vanished. It just asks for a fifty-year track record at the door."},
        ],
        "alternates": [
            {
                "formula": "Follow the Money",
                "text": "Related Companies replaced a $450M Fannie Mae note on Manhattan Plaza with a $750M loan from Wells Fargo.\nThe property holds 1,689 residential units at 400 West 43rd Street.\nI read that lender handoff—from agency execution to a money-center bank—as a bet on long-term regulatory certainty.\nWhen a single Manhattan block pulls $750M of fresh bank paper, check who sits on the covenant.",
            },
            {
                "formula": "The Number That Doesn't Fit",
                "text": "Most borrowers bring cash to the table to refinance in 2026. Related just pulled a $750M Wells Fargo loan to retire $450M of debt on Manhattan Plaza.\nThe 1,689-unit Hell's Kitchen complex remains one of New York's flagship Mitchell-Lama assets.\nMy read is that scale and contracted cash flow still write their own rules in bank credit committees.\nCash-out refinancings still exist if you own the whole block.",
            },
        ],
    },
    {
        "object_id": "apollo-udr-forming-2-billion-multifamily-joint-venture",
        "date": "2026-10-21",
        "sector": "commercial_real_estate",
        "score": 95.0,
        "title": "Apollo, UDR Forming $2-Billion Multifamily Joint Venture",
        "article_url": "https://lighttowergroup.co/insights/apollo-udr-forming-2-billion-multifamily-joint-venture.html",
        "formula": "Follow the Money",
        "lines": [
            {"kind": "fact", "text": "Apollo is committing $1.34B of equity for a two-thirds stake in a $2B multifamily joint venture with UDR."},
            {"kind": "fact", "text": "UDR contributes 15 properties across 4,845 apartments while keeping a one-third stake and management."},
            {"kind": "read", "text": "I read this as public REITs using private balance sheets to monetize net asset value without dumping assets."},
            {"kind": "kicker", "text": "When public markets discount your bricks, sell two-thirds of the kitchen to private capital."},
        ],
        "alternates": [
            {
                "formula": "Two Numbers, One Story",
                "text": "Apollo is putting up $1.34B for two-thirds of a $2B apartment venture with UDR across 15 properties and 4,845 units.\nUDR pockets approximately $1.2B in cash proceeds while keeping operational control.\nI read this as the cleanest arbitrage in real estate right now: private LP capital pricing multifamily higher than Wall Street tickers do.\nPublic REITs do not need a wave of M&A when JV equity clears at par.",
            },
            {
                "formula": "The Second-Order Effect",
                "text": "UDR just moved 15 apartment communities (4,845 units) into a $2B joint venture backed by $1.34B from Apollo.\nUDR keeps a one-third stake and fee stream.\nMy read is that mega-JVs are quietly setting the institutional clearing floor for apartments while one-off sales stay quiet.\nWatch how many public REIT boards copy this exact term sheet before year-end.",
            },
        ],
    },
    {
        "object_id": "northwind-group-closes-1b-debt-fund",
        "date": "2026-10-21",
        "sector": "private_equity",
        "score": 94.0,
        "title": "Northwind Group Closes $1B Debt Fund",
        "article_url": "https://lighttowergroup.co/insights/northwind-group-closes-1b-debt-fund.html",
        "formula": "The Number That Doesn't Fit",
        "lines": [
            {"kind": "fact", "text": "Ran Eliasaf's Northwind Group closed its third real estate debt fund at $1B, double its $500M target."},
            {"kind": "fact", "text": "Recycling capital along the way, the fund has already originated $1.5B in senior and condo loans."},
            {"kind": "read", "text": "I read a 2x fundraising close as proof that LPs prefer owning the senior attachment point over guessing cap rates."},
            {"kind": "kicker", "text": "In a tight credit cycle, the guy writing first-lien bridge paper sleeps best."},
        ],
        "alternates": [
            {
                "formula": "Follow the Money",
                "text": "Northwind Group set out to raise $500M for its third real estate debt fund and closed at $1B.\nThe vehicle has already deployed $1.5B into loans by recycling early payoffs.\nI read that velocity as the real tell: borrowers are paying private credit for speed while regional banks sit on their hands.\nPrivate debt is no longer the backup plan. It is the clearing house.",
            },
            {
                "formula": "Two Numbers, One Story",
                "text": "$500M target. $1B hard close.\nNorthwind Group's third debt fund has already originated $1.5B in real estate loans.\nMy read is that institutional allocators are crowding into senior real estate credit because contractual yield beats waiting on cap-rate compression.\nEquity takes the headlines. Senior debt takes the distributions.",
            },
        ],
    },
    {
        "object_id": "cbre-expands-data-center-footprint-with-1b-acquisition-of-onnec-group",
        "date": "2026-10-21",
        "sector": "data_centers",
        "score": 93.0,
        "title": "CBRE Expands Data Center Footprint With $1B Acquisition Of Onnec Group",
        "article_url": "https://lighttowergroup.co/insights/cbre-expands-data-center-footprint-with-1b-acquisition-of-onnec-group.html",
        "formula": "Follow the Money",
        "lines": [
            {"kind": "fact", "text": "CBRE agreed to buy London data center installer Onnec Group for $610M cash plus up to $400M in earnouts."},
            {"kind": "fact", "text": "Onnec employs roughly 1,600 specialists wiring and fitting out white-space racks inside hyperscale halls."},
            {"kind": "read", "text": "I read a $1B bet on structured cabling as proof that the real bottleneck in AI is skilled hands inside the building."},
            {"kind": "kicker", "text": "Everyone wants to own the AI landlord. Smart money is buying the electrician."},
        ],
        "alternates": [
            {
                "formula": "Two Numbers, One Story",
                "text": "CBRE is paying $610M cash and up to $400M in earnouts for Onnec Group, a London data center fit-out specialist.\nThat puts up to $1.01B behind a company that installs cabling and racks inside server halls.\nMy read is that shells and land are only half a data center; recurring margin lives inside the rack.\nIn every gold rush, check who owns the wiring crew.",
            },
            {
                "formula": "The Second-Order Effect",
                "text": "CBRE's $610M cash plus $400M earnout deal for Onnec Group brings 1,600 data center technicians under one roof.\nI read this as commercial real estate advisory morphing into industrial services to capture hyperscale capex.\nLeasing a shell pays a fee once. Maintaining the racks pays every quarter.",
            },
        ],
    },
    {
        "object_id": "a-wave-of-new-banks-is-about-to-shake-up-a-normally-staid-industry",
        "date": "2026-10-21",
        "sector": "fed_macro",
        "score": 92.0,
        "title": "A wave of new banks is about to shake up a normally staid industry",
        "article_url": "https://lighttowergroup.co/insights/a-wave-of-new-banks-is-about-to-shake-up-a-normally-staid-industry.html",
        "formula": "History Rhymes",
        "lines": [
            {"kind": "fact", "text": "De novo bank charter filings per year have doubled versus 2017–2020 and run 5x the 2010–2016 average."},
            {"kind": "fact", "text": "After the 2008 crisis, new U.S. bank formation nearly flatlined for a decade."},
            {"kind": "read", "text": "I read a 5x jump in bank charters as fresh equity stepping in to lend while legacy banks nurse 2021 scars."},
            {"kind": "kicker", "text": "The best time to start a bank is always when the old ones are still playing defense."},
        ],
        "alternates": [
            {
                "formula": "Two Numbers, One Story",
                "text": "New bank charter applications are running at 2x the pace of 2017–2020 and about 5x the 2010–2016 post-Dodd-Frank average.\nI read this wave of de novo charters as fresh equity stepping in with zero legacy office or underwater bond books.\nFor borrowers, a new bank without yesterday's workouts is the friendliest credit committee in town.",
            },
            {
                "formula": "The Second-Order Effect",
                "text": "Annual bank chartering activity is up roughly 5x relative to the 2010–2016 average.\nMy read is that regulatory openness plus clean-sheet capital will quietly rebuild middle-market CRE lending from the bottom up.\nWatch who gets chartered this year; they will be quoting your refinancing in eighteen months.",
            },
        ],
    },
    {
        "object_id": "occ-finalizes-genius-act-stablecoin-rule",
        "date": "2026-10-21",
        "sector": "banking_credit",
        "score": 91.0,
        "title": "OCC Finalizes GENIUS Act Stablecoin Rule",
        "article_url": "https://lighttowergroup.co/insights/occ-finalizes-genius-act-stablecoin-rule.html",
        "formula": "The Clock",
        "lines": [
            {"kind": "fact", "text": "The OCC finalized its GENIUS Act rule for payment stablecoin issuers, taking effect January 18, 2027."},
            {"kind": "fact", "text": "Regulators also dropped a proposed presumption against third-party stablecoin reward arrangements."},
            {"kind": "read", "text": "I read this as supervised stablecoins turning into a permanent, regulated buyer of short-dated Treasury bills."},
            {"kind": "kicker", "text": "When the OCC writes the rulebook, compliance officers stop saying never and start asking how much."},
        ],
        "alternates": [
            {
                "formula": "Translate the Jargon",
                "text": "The OCC's final GENIUS Act stablecoin rule takes effect January 18, 2027, and drops the proposed ban on third-party reward arrangements.\nExisting U.S. issuers can also apply for waivers from prior-approval bottlenecks.\nI read that combination as Washington turning payment stablecoins into regulated narrow banks.\nKeep an eye on where community bank deposits go when digital dollars can pay partner rewards.",
            },
            {
                "formula": "The Second-Order Effect",
                "text": "January 18, 2027 is now the hard effective date for the OCC's final GENIUS Act stablecoin framework.\nThe final rule also removed a proposed presumption against third-party rewards.\nMy read is that traditional banks just got a calendar date for when on-chain dollar settlement goes mainstream.\nNine weeks is a short runway in banking.",
            },
        ],
    },
    {
        "object_id": "blackstone-s-april-housing-lands-369m-fannie-mae-facility",
        "date": "2026-10-21",
        "sector": "commercial_real_estate",
        "score": 90.0,
        "title": "Blackstone's April Housing Lands $369M Fannie Mae Facility",
        "article_url": "https://lighttowergroup.co/insights/blackstone-s-april-housing-lands-369m-fannie-mae-facility.html",
        "formula": "Follow the Money",
        "lines": [
            {"kind": "fact", "text": "Blackstone's April Housing just closed a $369M Fannie Mae credit facility arranged by Newmark."},
            {"kind": "fact", "text": "The financing covers 25 Low-Income Housing Tax Credit properties totaling 3,000+ units across eight states."},
            {"kind": "read", "text": "I read $369M of agency paper across 25 LIHTC assets as proof that affordable housing is the most liquid collateral in CRE."},
            {"kind": "kicker", "text": "Market-rate rents fluctuate. Mission-driven agency liquidity never sleeps."},
        ],
        "alternates": [
            {
                "formula": "Two Numbers, One Story",
                "text": "$369M in Fannie Mae financing across 25 affordable properties and more than 3,000 units.\nNewmark arranged the facility for Blackstone's April Housing across eight states.\nMy read is that agency credit facilities are the quiet engine keeping institutional multifamily returns intact.\nScale plus LIHTC covenants gets the sharpest spread on the board.",
            },
            {
                "formula": "The Quiet Signal",
                "text": "April Housing, backed by Blackstone, locked in a $369M Fannie Mae credit facility spanning 25 properties and 3,000+ units.\nI read this as institutional sponsors leaning hard into agency credit lines while private bank syndications take longer to clear.\nIf your basis qualifies for Fannie or Freddie, you are playing a different game than the rest of the market.",
            },
        ],
    },
    {
        "object_id": "hines-closes-591m-dst-its-largest-ever",
        "date": "2026-10-21",
        "sector": "commercial_real_estate",
        "score": 89.0,
        "title": "Hines Closes $591M DST, Its Largest Ever",
        "article_url": "https://lighttowergroup.co/insights/hines-closes-591m-dst-its-largest-ever.html",
        "formula": "The Number That Doesn't Fit",
        "lines": [
            {"kind": "fact", "text": "Hines Private Wealth Solutions closed HREX 9, DST at $591M—the largest Delaware statutory trust in firm history."},
            {"kind": "fact", "text": "The vehicle is backed by two multifamily properties in Coral Gables, Florida, and Chicago."},
            {"kind": "read", "text": "I read a record $591M 1031-exchange raise as private wealth filling the equity gap left by sidelined pensions."},
            {"kind": "kicker", "text": "Never underestimate how much equity appears when the alternative is writing a check to the IRS."},
        ],
        "alternates": [
            {
                "formula": "Follow the Money",
                "text": "Hines raised about $591M for its HREX 9 Delaware statutory trust, its largest DST ever, backed by apartments in Coral Gables and Chicago.\nI read this as 1031-exchange retail capital stepping into trophy multifamily while institutional LP committees move slowly.\nTax deferral is the most patient equity partner in commercial real estate.",
            },
            {
                "formula": "Translate the Jargon",
                "text": "A Delaware statutory trust lets 1031 sellers roll tax-deferred proceeds into institutional real estate.\nHines just closed one at $591M across Coral Gables and Chicago multifamily—its largest ever.\nMy read is that private wealth channels are no longer sidecar capital; they are driving half-billion-dollar executions.",
            },
        ],
    },
    {
        "object_id": "amazon-withdraws-application-for-data-center-campus-at-gwu-site-in-ashburn-virgi",
        "date": "2026-10-21",
        "sector": "data_centers",
        "score": 88.5,
        "title": "Amazon withdraws application for data center campus at GWU site in Ashburn, Virginia",
        "article_url": "https://lighttowergroup.co/insights/amazon-withdraws-application-for-data-center-campus-at-gwu-site-in-ashburn-virgi.html",
        "formula": "The Number That Doesn't Fit",
        "lines": [
            {"kind": "fact", "text": "Amazon withdrew its application for the Bridgefield Tech Center data center campus at the GWU site in Ashburn."},
            {"kind": "fact", "text": "As part of stepping back, the cloud giant will hand roughly 25 acres valued at $65M to Loudoun County."},
            {"kind": "read", "text": "I read a hyperscaler walking away from Ashburn dirt as proof that local zoning and power friction can veto any balance sheet."},
            {"kind": "kicker", "text": "In Data Center Alley, megawatts and zoning votes now beat a blank check."},
        ],
        "alternates": [
            {
                "formula": "The Second-Order Effect",
                "text": "Amazon scrapped its Bridgefield Tech Center data center application in Ashburn and will transfer roughly 25 acres worth about $65M to Loudoun County.\nI read that pullback as proof that existing entitled megawatts in Northern Virginia just got even scarcer.\nEvery cancelled campus in Loudoun raises the replacement value of the racks already humming next door.",
            },
            {
                "formula": "Follow the Money",
                "text": "Roughly 25 acres in Ashburn valued at around $65M are going to Loudoun County after Amazon withdrew its GWU data center campus plan.\nMy read is that hyperscalers are ruthlessly pruning sites where entitlement timelines slip.\nCapital is abundant; energized zoning is not.",
            },
        ],
    },
    {
        "object_id": "alcoa-to-sell-idle-massena-east-smelter-site-for-up-to-315m-data-center-build",
        "date": "2026-10-21",
        "sector": "data_centers",
        "score": 88.0,
        "title": "Alcoa To Sell Idle Massena East Smelter Site For Up To $315M Data Center Build",
        "article_url": "https://lighttowergroup.co/insights/alcoa-to-sell-idle-massena-east-smelter-site-for-up-to-315m-data-center-build.html",
        "formula": "The Second-Order Effect",
        "lines": [
            {"kind": "fact", "text": "Alcoa agreed to sell portions of its idled Massena East aluminum smelter in New York for up to $315M for a data center."},
            {"kind": "fact", "text": "Smelters sit on massive high-voltage substations originally built for heavy industrial loads."},
            {"kind": "read", "text": "I read this as the sharpest arbitrage in real estate: rust-belt power hookups repriced as AI compute land."},
            {"kind": "kicker", "text": "Nobody is building new aluminum smelters, but their transformers just became beachfront property."},
        ],
        "alternates": [
            {
                "formula": "Two Numbers, One Story",
                "text": "An idled aluminum smelter in Massena, New York is fetching up to $315M from a data center developer.\nAlcoa is monetizing defunct industrial acreage because the grid interconnect is already in the ground.\nMy read is that power-rich brownfields are out-trading prime suburban office parks ten to one.\nDon't value the shed; value the substation.",
            },
            {
                "formula": "History Rhymes",
                "text": "Alcoa's idled Massena East smelter site in upstate New York is selling for up to $315M for a data center build.\nFifty years ago, cheap St. Lawrence hydro power drew aluminum; today the same wires draw compute.\nI read this as industrial geography coming full circle around electrons.",
            },
        ],
    },
    {
        "object_id": "billionaire-residents-of-nyc-s-famed-pierre-remain-in-the-dark-after-contested-2",
        "date": "2026-10-21",
        "sector": "commercial_real_estate",
        "score": 87.5,
        "title": "Billionaire residents of NYC’s famed Pierre remain in the dark after contested $2B sale collapsed",
        "article_url": "https://lighttowergroup.co/insights/billionaire-residents-of-nyc-s-famed-pierre-remain-in-the-dark-after-contested-2.html",
        "formula": "The Number That Doesn't Fit",
        "lines": [
            {"kind": "fact", "text": "The contested $2B sale of New York's famed Pierre hotel and co-op on Fifth Avenue has collapsed."},
            {"kind": "fact", "text": "Billionaire co-op residents remain in the dark on next steps after months of board and buyer friction."},
            {"kind": "read", "text": "I read a collapsed $2B trophy trade as a reminder that complex co-op governance can kill a deal faster than interest rates."},
            {"kind": "kicker", "text": "Underwriting the capital stack is math. Underwriting a Fifth Avenue co-op board is theatre."},
        ],
        "alternates": [
            {
                "formula": "Follow the Money",
                "text": "A proposed $2B acquisition of The Pierre on Fifth Avenue is officially dead, leaving co-op shareholders without a deal.\nMy read is that trophy hospitality capital is available, but governance tangles between hotel operators and residential boards carry a steep discount.\nThe fancier the address, the harder the closing table.",
            },
            {
                "formula": "The Quiet Signal",
                "text": "After months of negotiations, the contested $2B sale of NYC's Pierre has fallen apart.\nI read this as proof that headline-grabbing $2B letters of intent mean very little until the capital stack and the board signatures actually clear.\nIn New York, only recorded deeds count.",
            },
        ],
    },
    {
        "object_id": "kennedy-wilson-vintage-housing-buys-foreclosed-san-diego-tower-for-multifamily-r",
        "date": "2026-10-21",
        "sector": "commercial_real_estate",
        "score": 87.0,
        "title": "Kennedy Wilson's Vintage Housing Buys Foreclosed San Diego Tower for Multifamily Redevelopment",
        "article_url": "https://lighttowergroup.co/insights/kennedy-wilson-vintage-housing-buys-foreclosed-san-diego-tower-for-multifamily-r.html",
        "formula": "Follow the Money",
        "lines": [
            {"kind": "fact", "text": "Kennedy Wilson's Vintage Housing bought 610 W. Ash St., a 177,489-SF San Diego tower, out of foreclosure from lender A10 Capital."},
            {"kind": "fact", "text": "The buyer plans to redevelop the foreclosed office building into multifamily housing."},
            {"kind": "read", "text": "I read this as the real rule of office-to-residential conversions: they only pencil after the original loan takes the haircut."},
            {"kind": "kicker", "text": "Office conversions rarely work at yesterday's basis. They work great at the lender's basis."},
        ],
        "alternates": [
            {
                "formula": "The Second-Order Effect",
                "text": "Lender A10 Capital sold the foreclosed 177,489-SF tower at 610 W. Ash St. in San Diego to Kennedy Wilson's Vintage Housing for a multifamily conversion.\nMy read is that every office foreclosure is quietly manufacturing the affordable land basis that apartment builders need.\nFirst the lender takes the keys; then the floorplates make sense.",
            },
            {
                "formula": "Two Numbers, One Story",
                "text": "177,489 square feet of foreclosed San Diego office space at 610 W. Ash St. just traded from lender A10 Capital to Kennedy Wilson's Vintage Housing.\nI read this as the second act of the office cycle finally clearing on the courthouse steps.\nDistress is how obsolete cubicles turn into apartments.",
            },
        ],
    },
    {
        "object_id": "foreclosure-auction-set-for-loop-office-to-residential-conversion",
        "date": "2026-10-21",
        "sector": "commercial_real_estate",
        "score": 86.5,
        "title": "Foreclosure Auction Set For Loop Office-To-Residential Conversion",
        "article_url": "https://lighttowergroup.co/insights/foreclosure-auction-set-for-loop-office-to-residential-conversion.html",
        "formula": "The Clock",
        "lines": [
            {"kind": "fact", "text": "A Chicago Loop office-to-residential conversion is heading to foreclosure auction over a $28.2M mortgage from Prime Finance."},
            {"kind": "fact", "text": "Court filings show the construction debt was refinanced in 2021."},
            {"kind": "read", "text": "I read a conversion itself landing in foreclosure as a warning that gutting old towers carries brutal cost risk."},
            {"kind": "kicker", "text": "Converting an office building does not automatically convert the math."},
        ],
        "alternates": [
            {
                "formula": "Follow the Money",
                "text": "An affiliate of Prime Finance is taking a Chicago Loop office-to-apartment conversion to foreclosure auction over a 2021 $28.2M mortgage.\nMy read is that 2021-vintage bridge underwritings left zero margin for construction inflation behind century-old facades.\nEven the rescue trade sometimes needs a rescue.",
            },
            {
                "formula": "History Rhymes",
                "text": "Refinanced with $28.2M from Prime Finance in 2021, a Chicago Loop office conversion is now set for foreclosure auction.\nI read this as the classic pioneer tax in adaptive reuse: the second owner usually makes the money.\nWatch what basis clears at the auction.",
            },
        ],
    },
    {
        "object_id": "forge-atlanta-developer-admits-19m-accounting-error-falls-further-behind-on-its",
        "date": "2026-10-21",
        "sector": "commercial_real_estate",
        "score": 86.0,
        "title": "Forge Atlanta Developer Admits $19M Accounting Error, Falls Further Behind On Its Loan",
        "article_url": "https://lighttowergroup.co/insights/forge-atlanta-developer-admits-19m-accounting-error-falls-further-behind-on-its.html",
        "formula": "Two Numbers, One Story",
        "lines": [
            {"kind": "fact", "text": "Forge Atlanta developer Webstar Technology Group revised its 2025 liabilities to $19.8M—up from the $1.1M previously reported."},
            {"kind": "fact", "text": "The company disclosed the correction in an Oct. 15 filing while falling further behind on its loan."},
            {"kind": "read", "text": "I read an $18.7M liability restatement alongside a loan default as why lenders demand audited sponsor financials up front."},
            {"kind": "kicker", "text": "Mistaking $19.8M of debt for $1.1M is not a rounding error. It is a workout."},
        ],
        "alternates": [
            {
                "formula": "The Number That Doesn't Fit",
                "text": "Previously reported liabilities: $1.1M. Revised liabilities in an Oct. 15 filing: $19.8M.\nForge Atlanta developer Webstar Technology Group disclosed the $19M accounting error while falling further behind on its loan.\nMy read is that higher rates expose sloppy bookkeeping faster than any auditor ever could.",
            },
            {
                "formula": "Follow the Money",
                "text": "Webstar Technology Group corrected its 2025 liabilities from $1.1M to $19.8M in an Oct. 15 filing as its Forge Atlanta loan fell deeper into arrears.\nI read this as a textbook lesson in why recourse and covenant monitoring matter when development timelines slip.",
            },
        ],
    },
    {
        "object_id": "affinius-capital-provides-94m-refi-for-dallas-area-industrial-property",
        "date": "2026-10-21",
        "sector": "commercial_real_estate",
        "score": 85.5,
        "title": "Affinius Capital Provides $94M Refi for Dallas-Area Industrial Property",
        "article_url": "https://lighttowergroup.co/insights/affinius-capital-provides-94m-refi-for-dallas-area-industrial-property.html",
        "formula": "Two Numbers, One Story",
        "lines": [
            {"kind": "fact", "text": "Affinius Capital provided a $94M refinancing for three warehouses totaling 1.2M SF at Crossroads Logistics Park in Midlothian, Texas."},
            {"kind": "fact", "text": "The three-building industrial park sits in the south Dallas logistics corridor."},
            {"kind": "read", "text": "I read $94M across 1.2M square feet as the exact attachment point where institutional industrial lenders love to live."},
            {"kind": "kicker", "text": "Modern clear heights and Texas highway frontage still clear credit committee on the first read."},
        ],
        "alternates": [
            {
                "formula": "Follow the Money",
                "text": "Affinius Capital wired a $94M refinancing across three buildings and 1.2M square feet at Crossroads Logistics Park south of Dallas.\nMy read is that stabilized Sunbelt industrial remains a core magnet for institutional credit managers.\nWhen the basis is right, $94M checks still move smoothly.",
            },
            {
                "formula": "The Quiet Signal",
                "text": "Three warehouses spanning 1.2M square feet in Midlothian, Texas just landed a $94M refinancing from Affinius Capital.\nI read this as steady, disciplined industrial credit execution while flashier sectors fight for quotes.",
            },
        ],
    },
    {
        "object_id": "nuveen-eic-backs-pivot-energy-with-500m-credit-facility",
        "date": "2026-10-21",
        "sector": "private_equity",
        "score": 85.0,
        "title": "Nuveen EIC Backs Pivot Energy With $500M Credit Facility",
        "article_url": "https://lighttowergroup.co/insights/nuveen-eic-backs-pivot-energy-with-500m-credit-facility.html",
        "formula": "Follow the Money",
        "lines": [
            {"kind": "fact", "text": "Pivot Energy closed a bilateral $500M corporate credit facility with Nuveen Energy Infrastructure Capital."},
            {"kind": "fact", "text": "The bilateral structure means a single institutional lender underwrote the entire half-billion-dollar commitment."},
            {"kind": "read", "text": "I read a one-stop $500M facility as why private infrastructure credit keeps taking share from multi-bank syndication desks."},
            {"kind": "kicker", "text": "Borrowers will gladly pay a few basis points not to herd six bank credit committees."},
        ],
        "alternates": [
            {
                "formula": "Translate the Jargon",
                "text": "A bilateral credit facility means one lender writes the whole check with no syndication risk.\nNuveen Energy Infrastructure Capital just handed Pivot Energy a $500M bilateral corporate facility.\nMy read is that certainty of execution is the most valuable currency in energy and real asset finance today.",
            },
            {
                "formula": "Two Numbers, One Story",
                "text": "One lender. $500M commitment.\nNuveen Energy Infrastructure Capital closed a bilateral $500M credit facility for Pivot Energy.\nI read this as insurance-backed infrastructure credit flexing its balance sheet where syndicated bank desks move too slowly.",
            },
        ],
    },
    {
        "object_id": "foursquare-co-founder-says-equity-holders-saw-no-returns-from-the-company-s-acqu",
        "date": "2026-10-21",
        "sector": "private_equity",
        "score": 84.5,
        "title": "Foursquare co-founder says equity holders saw no returns from the company’s acquisition",
        "article_url": "https://lighttowergroup.co/insights/foursquare-co-founder-says-equity-holders-saw-no-returns-from-the-company-s-acqu.html",
        "formula": "Follow the Money",
        "lines": [
            {"kind": "fact", "text": "Foursquare co-founder Dennis Crowley said common equity holders saw zero returns from the company's acquisition by Infillion."},
            {"kind": "fact", "text": "Years of stacked preferred rounds left the liquidation preference wall taller than the exit price."},
            {"kind": "read", "text": "I read this as a universal capital-stack lesson that applies as much to real estate as to venture: seniority eats first."},
            {"kind": "kicker", "text": "Headline valuation is vanity. Position in the waterfall is sanity."},
        ],
        "alternates": [
            {
                "formula": "Translate the Jargon",
                "text": "When Foursquare was acquired by Infillion, co-founder Dennis Crowley noted that equity holders saw no returns.\nThat is what a stacked liquidation preference waterfall does when an exit clears below peak paper marks.\nMy read is that whether you are in tech or CRE preferred equity, structure always beats storytelling.",
            },
            {
                "formula": "History Rhymes",
                "text": "Foursquare's acquisition by Infillion returned nothing to common equity holders, according to co-founder Dennis Crowley.\nI read this as the exact same waterfall math playing out in over-levered 2021 real estate syndications today.\nAlways read the preferred return clauses before celebrating the press release.",
            },
        ],
    },
    {
        "object_id": "duos-inks-20mw-colocation-deal-with-cloud-provider",
        "date": "2026-10-21",
        "sector": "data_centers",
        "score": 84.0,
        "title": "Duos inks 20MW colocation deal with cloud provider",
        "article_url": "https://lighttowergroup.co/insights/duos-inks-20mw-colocation-deal-with-cloud-provider.html",
        "formula": "The Quiet Signal",
        "lines": [
            {"kind": "fact", "text": "Duos Technologies Group signed a 10-year colocation deal for 20MW of load with a publicly traded U.S. cloud provider."},
            {"kind": "fact", "text": "A 10-year contract on 20MW gives a mid-sized operator bankable cash flow for a full decade."},
            {"kind": "read", "text": "I read a 10-year lease on a 20MW block as proof that cloud tenants are locking up regional capacity early."},
            {"kind": "kicker", "text": "Ten-year credit leases on 20MW blocks turn regional data halls into bond proxies."},
        ],
        "alternates": [
            {
                "formula": "Two Numbers, One Story",
                "text": "20MW of load. 10-year lease term.\nDuos Technologies Group inked the colocation deal with a mature publicly traded U.S. cloud provider.\nMy read is that creditworthy 10-year leases are why project finance lenders are aggressively bidding even sub-50MW data center deals.",
            },
            {
                "formula": "Follow the Money",
                "text": "A publicly traded cloud provider just committed to 20MW for 10 years with Duos Technologies Group.\nI read that lease duration as the magic key that unlocks high-leverage construction and mini-perm debt.",
            },
        ],
    },
    {
        "object_id": "ebrd-led-lenders-back-1-2-gw-solar-600-mwh-storage-plant-in-egypt",
        "date": "2026-10-21",
        "sector": "energy",
        "score": 83.5,
        "title": "EBRD-led lenders back 1.2 GW solar, 600 MWh storage plant in Egypt",
        "article_url": "https://lighttowergroup.co/insights/ebrd-led-lenders-back-1-2-gw-solar-600-mwh-storage-plant-in-egypt.html",
        "formula": "Two Numbers, One Story",
        "lines": [
            {"kind": "fact", "text": "An EBRD-led syndicate is financing a 1.2 GW solar plant paired with 600 MWh of battery storage in Minya, Egypt."},
            {"kind": "fact", "text": "Co-locating 600 MWh of storage onto a 1.2 GW array turns daytime generation into dispatchable grid power."},
            {"kind": "read", "text": "I read project finance now treating battery storage as mandatory infrastructure rather than an optional add-on."},
            {"kind": "kicker", "text": "Unfirmed megawatts struggle for debt. Stored megawatts get a syndicate."},
        ],
        "alternates": [
            {
                "formula": "Follow the Money",
                "text": "EBRD-led lenders just backed a 1.2 GW solar and 600 MWh battery project in Minya, Egypt.\nMy read is that development bank syndicates are setting a global template: solar without storage rarely clears project finance committee anymore.",
            },
            {
                "formula": "The Second-Order Effect",
                "text": "1.2 GW of solar paired with 600 MWh of battery storage in Minya, Egypt just cleared an EBRD-led project finance syndicate.\nI read this scale of solar-plus-storage as proof that battery capex curves have fallen far enough to pencil in emerging markets.",
            },
        ],
    },
    {
        "object_id": "the-budget-deficit-swells-while-the-cost-of-debt-rises",
        "date": "2026-10-20",
        "sector": "fed_macro",
        "score": 88.0,
        "title": "The budget deficit swells, while the cost of debt rises",
        "article_url": "https://lighttowergroup.co/insights/the-budget-deficit-swells-while-the-cost-of-debt-rises.html",
        "formula": "Two Numbers, One Story",
        "lines": [
            {"kind": "fact", "text": "The U.S. federal budget deficit has reached $2 trillion this fiscal year as Treasury interest costs climb."},
            {"kind": "fact", "text": "Every Treasury auction competes directly with private borrowers for long-duration fixed-income capital."},
            {"kind": "read", "text": "I read a $2T deficit as why the 10-year Treasury yield stays sticky even when the Fed trims short rates."},
            {"kind": "kicker", "text": "The Fed controls the overnight rate. The Treasury auction calendar controls your permanent mortgage."},
        ],
        "alternates": [
            {
                "formula": "Translate the Jargon",
                "text": "A $2 trillion federal budget deficit means the U.S. Treasury must continuously issue long-term supply while its own debt-service bill rises.\nMy read for real estate borrowers is simple: stop underwriting 3.5% ten-year Treasury rates into your exit cap.",
            },
            {
                "formula": "The Second-Order Effect",
                "text": "With the U.S. budget deficit hitting $2 trillion this fiscal year alongside rising debt costs, term premium is back in the bond market.\nI read this as a structural floor under long-term mortgage spreads.\nBuy for day-one cash yield, not for a bond-market bailout.",
            },
        ],
    },
    {
        "object_id": "booker-warren-push-ftc-probe-of-platform-lender-steering",
        "date": "2026-10-20",
        "sector": "banking_credit",
        "score": 85.0,
        "title": "Booker, Warren Push FTC Probe of Platform Lender Steering",
        "article_url": "https://lighttowergroup.co/insights/booker-warren-push-ftc-probe-of-platform-lender-steering.html",
        "formula": "Follow the Money",
        "lines": [
            {"kind": "fact", "text": "Senators Cory Booker and Elizabeth Warren are pushing the FTC to investigate online real estate platforms over alleged lender steering."},
            {"kind": "fact", "text": "The inquiry targets how digital portals route borrowers toward affiliated or preferred mortgage desks."},
            {"kind": "read", "text": "I read this as a reminder that whenever lead-generation and lending sit under the same roof, disclosure scrutiny eventually follows."},
            {"kind": "kicker", "text": "When the portal is free, the mortgage referral is usually the product."},
        ],
        "alternates": [
            {
                "formula": "The Second-Order Effect",
                "text": "Senators Booker and Warren are pressing the FTC to probe platform lender steering in real estate.\nMy read is that bundled portal-to-lender funnels face rising compliance friction right as mortgage originators fight for every basis point of volume.",
            },
            {
                "formula": "Translate the Jargon",
                "text": "Lender steering happens when a platform nudges a buyer toward an in-house or paying lender rather than the sharpest quote.\nBooker and Warren just asked the FTC to investigate the practice.\nI read independent debt advisory as the antidote to captive platform funnels.",
            },
        ],
    },
    {
        "object_id": "captona-closes-equity-investment-with-nexamp-in-large-community-solar-portfolio",
        "date": "2026-10-20",
        "sector": "energy",
        "score": 83.0,
        "title": "Captona Closes Equity Investment With Nexamp in Large Community Solar Portfolio",
        "article_url": "https://lighttowergroup.co/insights/captona-closes-equity-investment-with-nexamp-in-large-community-solar-portfolio.html",
        "formula": "Follow the Money",
        "lines": [
            {"kind": "fact", "text": "Captona closed a preferred equity investment with Nexamp across a 43-project, 187 MW community solar portfolio."},
            {"kind": "fact", "text": "Preferred equity lets the developer recycle capital across 43 sites without diluting project control."},
            {"kind": "read", "text": "I read preferred equity in 187 MW of solar as the exact capital-stack playbook we use in commercial real estate."},
            {"kind": "kicker", "text": "Preferred equity speaks the same language whether the asset collects rent or utility checks."},
        ],
        "alternates": [
            {
                "formula": "Two Numbers, One Story",
                "text": "43 community solar projects. 187 MW of distributed capacity.\nCaptona stepped in with a preferred equity investment alongside developer Nexamp.\nMy read is that distributed energy portfolios are now structured and traded just like multi-site real estate.",
            },
            {
                "formula": "Translate the Jargon",
                "text": "Captona structured its investment in Nexamp's 43-project, 187 MW community solar portfolio as preferred equity.\nI read that choice of instrument as institutional allocators demanding priority cash flow before common development upside.",
            },
        ],
    },
    {
        "object_id": "housing-report-city-planning-commission-adds-670-dwelling-units-and-a-long-term",
        "date": "2026-10-15",
        "sector": "local_government",
        "score": 84.0,
        "title": "Housing Report: City Planning Commission Adds 670 Dwelling Units and a Long-Term Care Facility as Summer Ends",
        "article_url": "https://lighttowergroup.co/insights/housing-report-city-planning-commission-adds-670-dwelling-units-and-a-long-term.html",
        "formula": "The Number That Doesn't Fit",
        "lines": [
            {"kind": "fact", "text": "NYC's City Planning Commission approved roughly 670 dwelling units and one care facility across all of September 2026."},
            {"kind": "fact", "text": "Those applications now move to the City Council for final land-use votes."},
            {"kind": "read", "text": "I read 670 entitled units in a city of 8.3M people as why existing New York multifamily trades at a scarcity premium."},
            {"kind": "kicker", "text": "Everyone debates New York rent growth. Almost nobody counts the monthly ULURP approvals."},
        ],
        "alternates": [
            {
                "formula": "Two Numbers, One Story",
                "text": "670 dwelling units approved by the NYC City Planning Commission in September 2026.\nThat is less than half a single large Manhattan block for the entire five boroughs.\nMy read is that New York's entitlement funnel remains the ultimate moat around existing apartment buildings.",
            },
            {
                "formula": "The Second-Order Effect",
                "text": "In September 2026, the City Planning Commission advanced roughly 670 dwelling units and a long-term care facility to the City Council.\nI read that trickle of new supply as why institutional buyers are paying sub-6% cap rates for existing outer-borough elevators.",
            },
        ],
    },
    {
        "object_id": "bowman-supervisory-modernization-after-silicon-valley-bank",
        "date": "2026-10-15",
        "sector": "fed_macro",
        "score": 83.0,
        "title": "Bowman, Supervisory Modernization After Silicon Valley Bank",
        "article_url": "https://lighttowergroup.co/insights/bowman-supervisory-modernization-after-silicon-valley-bank.html",
        "formula": "Translate the Jargon",
        "lines": [
            {"kind": "fact", "text": "Fed Governor Michelle Bowman said internal reviews substantiate critiques of Federal Reserve supervision after Silicon Valley Bank."},
            {"kind": "fact", "text": "Her remarks call for focusing bank supervision on core interest-rate and liquidity risk rather than box-checking."},
            {"kind": "read", "text": "I read this as a push to stop examiners from burying regional banks in paperwork while missing duration mismatches."},
            {"kind": "kicker", "text": "Good bank supervision reads the balance sheet before it reads the binder."},
        ],
        "alternates": [
            {
                "formula": "The Second-Order Effect",
                "text": "Fed Governor Bowman said preliminary findings substantiate important critiques of post-SVB Federal Reserve supervision.\nMy read is that a more tailored supervisory regime gives healthy regional banks room to quote commercial real estate loans again.",
            },
            {
                "formula": "History Rhymes",
                "text": "Looking back at Silicon Valley Bank, Fed Governor Bowman pointed to substantiated critiques of how the Fed supervises banks.\nI read that candor as a shift back toward core balance-sheet fundamentals.",
            },
        ],
    },
]


def _fmt_millions(amount: float) -> str:
    m = amount / 1_000_000.0
    if abs(m - round(m)) < 0.05:
        return f"${int(round(m))}M"
    return f"${m:.1f}M"


def build_nyc_transaction_takes() -> list[dict[str, Any]]:
    """Build 3-angle Quick Takes for all 30 curated NYC >$10M ACRIS transactions."""
    dossiers = get_curated_nyc_transactions()
    out: list[dict[str, Any]] = []
    dossiers_sorted = sorted(
        dossiers,
        key=lambda d: (str(d.closing_date or d.recorded_date or ""), float(d.sale_price_usd or 0)),
        reverse=True,
    )
    for idx, dossier in enumerate(dossiers_sorted, 1):
        econ = compute_economics(dossier)
        draft = render_literary_story(dossier, econ)
        prop = dossier.property_info
        slug = _slugify(f"nyc-deal-{prop.address}-{prop.neighborhood}-{int(econ.sale_price_usd // 1_000_000)}m")
        object_id = slug
        address = prop.address.strip()
        neighborhood = prop.neighborhood.split("/")[0].strip()
        borough = prop.borough.strip()
        price = float(econ.sale_price_usd)
        price_m = _fmt_millions(price)
        closing_date = str(dossier.closing_date or dossier.recorded_date)[:10]
        buyer = _clean_entity_name(dossier.buyer)
        seller = _clean_entity_name(dossier.seller)
        lender = _clean_entity_name(econ.primary_lender or "All-Cash")
        loan = float(econ.acquisition_debt_usd or 0)
        ltv = round(econ.implied_ltv_pct) if econ.implied_ltv_pct else None
        gsf = int(prop.gross_sqft or 0)
        ppsf = int(round(econ.price_per_gsf or 0))
        units = int(prop.residential_units or 0)
        prior_price = econ.prior_sale_price_usd
        prior_date = str(econ.prior_sale_date or "")[:4]
        bbl = prop.bbl

        if loan > 0 and ltv:
            loan_m = _fmt_millions(loan)
            equity_m = _fmt_millions(max(price - loan, 0))
            line1 = f"{buyer} paid {price_m} for {address} in {neighborhood}, {borough} (${ppsf:,}/SF)."
            if prior_price and prior_date:
                prior_m = _fmt_millions(float(prior_price))
                line2 = f"{lender} wired a {loan_m} loan ({ltv}% LTV); the {gsf:,}-SF asset last traded for {prior_m} in {prior_date}."
            else:
                line2 = f"{lender} funded a {loan_m} senior loan ({ltv}% LTV) alongside {equity_m} of equity across {gsf:,} SF."
            read_line = f"I read {ltv}% debt at ${ppsf:,}/SF as the exact clearing basis where NYC credit committees say yes."
            kicker_line = "Debt attachment tells you the real value faster than the brochure ever will."

            alt1 = (
                f"Two numbers on {address} in {neighborhood}: {price_m} price (${ppsf:,}/SF) and a {loan_m} loan from {lender} ({ltv}% LTV).\n"
                f"{buyer} acquired the {gsf:,}-SF asset from {seller} with {equity_m} of cash equity.\n"
                f"My read is that {ltv}% LTV is where disciplined New York debt and fresh basis shake hands.\n"
                f"Watch the senior loan per foot; that is the market's true floor."
            )
            alt2 = (
                f"Follow the stack at {address} ({bbl}): {buyer} closed at {price_m} with {loan_m} from {lender}.\n"
                + (
                    f"Across {units} units and {gsf:,} SF, the basis lands at ${ppsf:,}/SF.\n"
                    if units > 0
                    else f"Across {gsf:,} gross square feet in {neighborhood}, the basis lands at ${ppsf:,}/SF.\n"
                )
                + "I read this execution as proof that right-sized basis still draws institutional balance sheets.\n"
                + "Good sponsorship plus real cash equity clears the desk every time."
            )
            formula = "Follow the Money"
        else:
            line1 = f"{buyer} closed on {address} in {neighborhood}, {borough} for {price_m}—100% all-cash on ACRIS."
            if prior_price and prior_date:
                prior_m = _fmt_millions(float(prior_price))
                line2 = f"The {gsf:,}-SF asset traded at ${ppsf:,}/SF with zero debt, compared with a {prior_m} deed in {prior_date}."
            else:
                line2 = f"The {gsf:,}-SF property cleared from {seller} at ${ppsf:,}/SF with zero mortgage debt at closing."
            read_line = f"I read an unencumbered {price_m} check at ${ppsf:,}/SF as locking in basis now and timing debt later."
            kicker_line = "All-cash at closing is the ultimate rate hedge."

            alt1 = (
                f"{price_m} purchase price. $0 of mortgage debt at closing.\n"
                f"{buyer} acquired the {gsf:,}-SF {address} in {neighborhood} from {seller} at ${ppsf:,}/SF.\n"
                f"My read is that unencumbered closings set the sharpest basis in New York before permanent refinancing follows.\n"
                f"Close fast with cash; finance once the dust settles."
            )
            alt2 = (
                f"On ACRIS ({bbl}), {buyer} took down {address} in {neighborhood} for {price_m} (${ppsf:,}/SF).\n"
                + (
                    f"The {gsf:,}-SF building spans {units} units and closed with 100% equity.\n"
                    if units > 0
                    else f"The {gsf:,}-SF property closed 100% unencumbered from {seller}.\n"
                )
                + "I read zero closing leverage as a sponsor refusing to let lender timelines dictate a good basis.\n"
                + "Certainty of close still commands the best price."
            )
            formula = "The Number That Doesn't Fit"

        lines = [
            {"kind": "fact", "text": line1},
            {"kind": "fact", "text": line2},
            {"kind": "read", "text": read_line},
            {"kind": "kicker", "text": kicker_line},
        ]
        text = "\n".join(l["text"] for l in lines)
        score = round(80.0 + min(price / 5_000_000.0, 18.0), 2)
        out.append({
            "id": f"take-{object_id}",
            "object_id": object_id,
            "date": closing_date,
            "published_at": f"{closing_date}T14:00:00+00:00",
            "sector": "nyc_transactions",
            "title": draft["title"],
            "article_url": f"https://lighttowergroup.co/insights/{slug}.html",
            "formula": formula,
            "text": text,
            "lines": lines,
            "alternates": [
                {"formula": "Two Numbers, One Story", "text": alt1},
                {"formula": "Follow the Money", "text": alt2},
            ],
            "rank": idx,
            "score": score,
            "chars": len(text),
        })
    return out


def build_all_takes() -> list[dict[str, Any]]:
    feed: list[dict[str, Any]] = []

    for item in MULTI_SECTOR_TAKES:
        text = "\n".join(l["text"] for l in item["lines"])
        entry = {
            "id": f"take-{item['object_id']}",
            "object_id": item["object_id"],
            "date": item["date"],
            "published_at": f"{item['date']}T11:00:00+00:00",
            "sector": item["sector"],
            "title": item["title"],
            "article_url": item["article_url"],
            "formula": item["formula"],
            "text": text,
            "lines": item["lines"],
            "alternates": item["alternates"],
            "rank": 1,
            "score": float(item["score"]),
            "chars": len(text),
        }
        feed.append(entry)

    nyc_takes = build_nyc_transaction_takes()
    feed.extend(nyc_takes)

    # Validate every take & alternate against takes.py constraints
    for entry in feed:
        all_texts = [entry["text"]] + [a["text"] for a in entry.get("alternates", [])]
        for v in all_texts:
            lines = v.splitlines()
            assert 2 <= len(lines) <= takes_mod.MAX_LINES, f"Line count {len(lines)} out of bounds in {entry['id']}"
            assert len(v) <= takes_mod.MAX_CHARS, f"Char count {len(v)} > {takes_mod.MAX_CHARS} in {entry['id']}: {v}"
            assert not takes_mod._BANNED.search(v), f"Banned phrase found in {entry['id']}: {v}"

    # Assign per-day ranks by descending score
    days = {str(e["date"]) for e in feed}
    for day in days:
        same_day = sorted((e for e in feed if e["date"] == day), key=lambda e: -float(e.get("score") or 0))
        for rank, entry in enumerate(same_day, 1):
            entry["rank"] = rank

    feed.sort(key=lambda e: (str(e.get("date") or ""), -int(e.get("rank") or 999)), reverse=True)
    return feed


def sync_takes_json(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or (ROOT / "takes.json")
    feed = build_all_takes()
    payload = {
        "version": takes_mod.TAKES_VERSION,
        "updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "takes": feed,
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return feed


if __name__ == "__main__":
    written = sync_takes_json()
    print(f"Synced {len(written)} verified Quick Takes (with 3 angles each) to {ROOT / 'takes.json'}")
