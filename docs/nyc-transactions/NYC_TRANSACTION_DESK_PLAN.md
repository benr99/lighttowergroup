# NYC transaction desk development plan

Date: October 18, 2026  
Status: Implemented & Live (`scripts/nyc_transactions/`, `config/nyc_transactions.json`, `insights.html`)  
Companion: [Implementation and editorial prompts](NYC_TRANSACTION_DESK_PROMPT.md)

## Editorial purpose

Build a dedicated Light Tower reporting desk for New York City buildings and development sites that trade for more than $10 million. Cover Manhattan, Brooklyn, Queens, the Bronx, and Staten Island. The reader should finish a story understanding the property, the people involved, the deal economics, and the decision the transaction makes visible.

The competitive advantage comes from accumulating knowledge: a persistent property and transaction history, a reliable account of the capital stack, local context, and a recognizable editorial judgment. Each new story should benefit from everything the desk has already learned about that building, sponsor, lender, and neighborhood.

The standard is *The Real Deal* × *Commercial Observer*'s Finance Desk × Light Tower Group's Principal Desk Read: active-verb hooks, basis/hold-period tension, surgical capital-stack analysis, and Benjamin Rohr's first-person placement desk takeaway.

This desk is integrated into the live Intelligence experience at `insights.html` via the `NYC $10M+ Deals` filter (`vertical: "nyc_transactions"`) and `scripts/nyc_transactions/cli.py`.

## What the repository has today

These findings describe the local working tree inspected on October 15, 2026. The checkout has existing modifications, including intelligence code and page changes. They must be preserved. This review did not establish which local changes are deployed or audit live workflow runs.

| Component | Observed behavior | Implication for the new desk |
| --- | --- | --- |
| `.github/workflows/daily-insights-agent.yml` | Scheduled default selects v4 through `scripts/insights_v3.py --pipeline v4`; v2 and v3 remain selectable. V4 passes a daily target and article limit of 70. | The active configuration is broader and more volume oriented than some older editorial documents describe. Give NYC its own queue and budget. |
| `scripts/insights_v3.py` | Orchestrates ingestion, classification, event clustering, memory, enrichment, slate selection, generation, and publication. | Reuse infrastructure through adapters; do not make exhaustive NYC coverage compete for the general publication slate. |
| `config/sources.json` | Contains NYC publications. The Real Deal NYC and Crain's entries are inactive; Commercial Observer, Bisnow New York, Real Estate Weekly, and New York YIMBY are active in configuration. | Configuration is not a successful fetch. Audit actual access and maintain an explicit gap register. |
| `scripts/intelligence_object.py` | Defines event objects, source references, evidence levels, facts, and novelty states. | Useful evidence and interchange types; add persistent property, transaction, and lifecycle identities. |
| `scripts/event_clustering.py` | Uses headline, entity, amount, and scale similarity to consolidate documents. | Helpful for discovery; insufficient to establish that two deeds concern the same closing or that two sales at one address are different events. |
| `scripts/retrieval.py`, `source_health.py` | Provide retrieval status, throttling, source health, and access handling. | Reuse operational controls and distinguish blocked, partial, and full evidence. |
| `scripts/research_dossier.py` | Builds source-grounded facts, quotations, gaps, and archive context; independence is approximated using domains. | Add active transaction research and source lineage. Three websites repeating one release are one evidence origin. |
| `scripts/v4_generation.py` | Uses a bounded writer and `claim_verifier.verify_draft`; retains the v3 publisher contract. | Preserve bounded runtime, but use a dedicated NYC writing contract and explicit analysis verification. |
| `scripts/claim_verifier.py`, `voice_gate.py` | Claim verification currently sets `MAX_VIEWS = 0`. A separate gate supports voice tied to verified facts; v4 imports and calls `verify_draft`, not that voice gate. | Simply adding a witty prompt will not create the intended product. Facts, calculations, inference, and voice need different validation paths. |
| `scripts/structured_sources.py` | Implements SEC EDGAR intake; its docstring identifies DOB and ACRIS as future additions. | No comprehensive NYC recorded-sale intake is implemented here today. |
| `scripts/v3_publish.py`, `daily_news_agent.py` | Render articles and update manifests, feeds, sitemap, and related links. Publisher skips an existing slug. | Reuse presentation and output contracts; deliberately implement corrections and updates, since skip-existing is not an update strategy. |
| `insights.html`, `edition.js`, `editions/README.md` | Insights grid fetches `insights.json` and filters by category; edition rendering separately consumes edition structures. | Integrate the new franchise into the grid first; decide edition placement explicitly. A new tag alone will not create the complete experience. |

Older 15-stage editorial architecture documents are design references, not evidence that every stage runs in v4. In particular, do not resurrect the old nested generation process just to support this desk.

## Coverage contract

Use these initial defaults as explicit, editable product decisions.

| Question | Initial rule |
| --- | --- |
| Geography | Physical assets within the five NYC boroughs. An NYC-headquartered buyer does not make an out-of-city asset eligible. |
| Threshold | Strictly greater than $10,000,000 USD in supported sale consideration. Exactly $10 million goes to a boundary queue. Keep the operator configurable. |
| Assets | Whole buildings, including multifamily, office, retail, hotel, industrial, mixed use, and whole townhouses; also land and development sites. |
| Individual residences | Exclude individual condo and co-op apartment sales from the core desk by default. Treat bulk unit packages as an explicitly labeled adjacent case. |
| Transaction types | Core coverage is completed building/site sales. Track contracts, foreclosure proceedings, auctions, note sales, ground leases, partial interests, and recapitalizations with distinct event types and completion states. |
| Development news | Track material filings, approvals, financing, demolition, construction, conversion, and completion for covered assets. Add development-only watchlist entries when the proposed project scale is credibly above $10 million, without calling project cost a sale price. |
| Debt | Acquisition debt belongs in the sale dossier. A refinancing above $10 million does not independently qualify as a $10 million property sale. |
| Partial interests | Store stake percentage, stake consideration, and any supported implied whole-asset value separately. Do not treat a small stake in a valuable building as an eligible whole-building sale. |
| Portfolios | Create one parent closing with child assets. Store total consideration once. Count assets separately from closings; do not assign the whole price to every parcel. Unknown per-asset allocations remain unknown. |
| Mixed portfolios | Preserve NYC and non-NYC members. A portfolio above the threshold does not prove each NYC asset qualifies; show such assets as portfolio-associated until allocation evidence resolves eligibility. |
| Low or nominal consideration | Investigate related-party transfers, entity restructurings, and non-market deeds; do not call them market sales or infer a price from a mortgage. |
| Uncertain prices | Store reported ranges and conflicts. An approximate $10 million report is threshold-uncertain; research it without asserting eligibility. |

Every discovered candidate receives a recorded disposition. Every confirmed qualifying sale receives a property-linked research dossier and a publishable transaction account when the evidence permits. Aim for a substantial story on each sale, not just the most famous properties. Thin evidence creates a visible reporting backlog and a shorter verified account; it never licenses invented detail or makes the deal disappear.

Track three separate promises: detection coverage, research completion, and published coverage. Reconciliation can measure coverage of accessible public datasets and configured news sources. It cannot prove discovery of undisclosed entity transfers or every transaction on the day it closes. Publish a clear coverage methodology rather than claiming omniscience.

## Discovery and reconciliation

### News discovery

Maintain an NYC source registry with outlet, section, access method, licensing status, update cadence, last successful fetch, and observed borough coverage. Start by auditing the existing registry. Candidate additions for access testing include PincusCo, Traded, borough reporting, and relevant property, lender, broker, and sponsor announcements. These are candidates, not verified working integrations.

Search by address variants, building name, BBL, buyer and seller entities, principals, lender, prior acquisition, and transaction amount. Use national outlets only when the asset is in scope. Query the wider web after discovery; the research universe must extend beyond articles that arrived in the original feed window.

Store publication date, event date, discovery date, and retrieval date separately. Record which outlet broke the news. Preserve original reporting credit even when later primary documents settle the numbers. Licensed access or publisher-approved methods may expand coverage; a blocked source remains a measured gap. Search snippets can identify a lead but cannot serve as full article evidence.

### Public records

ACRIS provides deeds and document images for Manhattan, Brooklyn, Queens, and the Bronx. Staten Island document research requires the Richmond County Clerk route. The current ACRIS page also discusses Staten Island transfer-tax submissions; that does not make its deed-search coverage a five-borough service. See [NYC ACRIS](https://www.nyc.gov/site/finance/property/acris.page) and [NYC recording guidance](https://www.nyc.gov/site/finance/property/property-recording-property-related-documents.page).

Use approved structured data or subscription access for volume intake, then inspect underlying instruments as needed. ACRIS publishes bandwidth restrictions and directs high-volume users toward subscription services; do not implement unrestricted portal crawling. Validate dataset schemas, available dates, pagination, update cadence, permitted access, and join keys before selecting an adapter.

The [DOF rolling sales files](https://www.nyc.gov/site/finance/property/property-rolling-sales-data.page) cover the five boroughs and list sales over the last 12 months for tax classes 1, 2, and 4, excluding utility properties. Use them as a lagged reconciliation source, not a real-time or complete economic-transaction census. Annualized files support longer history. Check the glossary before interpreting fields and portfolio rows.

For development and property context, test current DOB NOW/BIS access, planning and zoning data, parcel/building datasets, HPD records where relevant, and primary financing or court documents. [DOB's building-data guide](https://www.nyc.gov/site/buildings/dob/find-building-data.page) is the starting inventory. Preserve dataset vintage and distinguish tax-lot attributes from an individual building's attributes. Verify current project-specific regulatory claims against official sources when reporting them.

### Proposed cadence and gap management

Poll permitted news and structured sources several times each business day. Reconcile new public records daily where data availability supports it. Run a weekly borough-by-borough sales reconciliation and a monthly historical catch-up. These are proposed operating cadences; no automation is created by this plan.

Use overlap windows and persistent watermarks, not a rolling news lookback alone. Rescan a configurable 90-day event window for late filings and corrections; run a 12-month initial sales backfill. Record both source publication latency and closing-to-recording latency. Separate newly discovered old sales from genuinely new market activity.

Every run reports attempted sources, successful sources, coverage gaps, last checked record dates, new candidates, confirmed sales, pending matches, excluded transfers, completed dossiers, and overdue stories by borough. A Staten Island source outage must remain visible even if Manhattan intake is healthy.

## Persistent research model

The desk needs four durable identities: property, transaction, development project, and published story. Link them through typed relationships. One property may contain multiple buildings; one sale can involve multiple parcels; one project can span several sales.

Use canonical BBLs where available, BINs for building records, and normalized address aliases. Preserve leading zeroes and source-specific identifiers. Maintain historical lot splits, mergers, condominium lot relationships, and address changes. A provisional address-based identity must be resolvable without losing its evidence or creating a second story.

Minimum transaction record:

- Immutable internal transaction ID, external document IDs, event type, lifecycle status, related event IDs, parent portfolio, and asset membership.
- Address aliases, borough, neighborhood with provenance, BBLs, BINs, property use, unit/key counts, area measures and their definitions, condition and development status where supported.
- Legal buyer and seller, supported sponsor/principal relationships, lender roles, and uncertainty about beneficial ownership. Similar LLC names do not prove common ownership.
- Contract, closing, document, recording, first-report, discovery, publication, and update dates as separate nullable fields.
- Consideration amount, currency, price basis, allocation basis, interest transferred, and eligibility decision with reason codes.
- Current and historical financing instruments; supported principal, commitment, funded balance, rate, term, maturity, amortization, and collateral scope. Unknown fields remain null.
- Claim ledger, source ledger, conflict ledger, quote ledger, calculation ledger, assumptions, comparable selection, and reporting gaps.
- Research status, queue age, next action, editorial angle, review findings, public story URL, corrections, and version history.

Represent each material claim as a value plus unit, effective date, source ID, document/page or text span, retrieval status, verification state, and competing evidence. Represent each calculation as a formula version, input claim IDs, assumptions, result, unit, rounding, and comparability caveats. Model assertions are never evidence.

Keep lifecycle and workflow states separate. A transaction can be `closed` while its research status is `needs_primary_document`; its story can be `published` while a later financing update is `under_review`.

## Reporting workflow for each transaction

1. **Resolve identity and eligibility.** Find the actual property and event; establish price basis, borough, transferred interest, and completion status. Link duplicate reports without collapsing a later resale or financing into the earlier closing.
2. **Assemble the evidence.** Retrieve accessible coverage and primary documents; record independent origins, original reporting credit, disagreements, and missing pages. Sanitize external material as untrusted input.
3. **Reconstruct the property history.** Establish prior ownership and sale price, material financing and redevelopment, occupancy and use, and relevant neighborhood history. Follow the building through time rather than collecting unrelated color.
4. **Research the people and incentives.** Identify the parties and documented business histories. Ask what the structure permits or constrains. Treat private motives as unknown unless a source establishes them.
5. **Build the economic account.** Calculate supported price measures, capital-stack relationships, historical changes, and relevant comps. List what cannot be calculated and why.
6. **Find the story.** Propose two or three angles, select the strongest, and state the evidence that could defeat it. A transaction need not represent a citywide trend to deserve coverage.
7. **Deepen the reporting.** Search targeted gaps before drafting. Prepare questions for buyer, seller, lender, broker, and affected people when their perspective would change the story. Outreach is a human reporting task; draft questions without automatically contacting anyone.
8. **Draft and verify.** Write from the approved evidence and calculations. Verify facts, math, inference, and quotations separately, then assess the surviving article for coherence.
9. **Publish and remember.** Publish the version that meets the evidence standard, attach methodology and source credit, update the property history, and queue unresolved follow-ups.

Full features normally need authoritative transaction evidence and multiple independent evidence origins supporting the economics, context, and human story. A deed plus independently sourced property history can be more useful than five copied articles. A verified public-record sale may receive a shorter account without a journalist having written about it first. Do not make quotations or arbitrary source counts prerequisites that erase underreported boroughs.

## Financial analysis standards

Compute numbers in code using typed units and validated denominators. The writer interprets results; it does not do the arithmetic.

| Measure | Required inputs and restrictions |
| --- | --- |
| Price per square foot | Supported consideration divided by relevant area. Label gross, rentable, land, or buildable area. Do not silently substitute among them. |
| Price per unit or key | Applicable consideration divided by supported residential units or hotel keys. Mixed-use allocation must be disclosed or the ratio withheld. |
| Prior-sale change | Comparable interest and asset scope at both dates. Absolute and percentage price change are nominal price comparisons, not total investment returns. |
| Cap rate | Matching annual NOI divided by price. State actual, trailing, or stabilized period; preserve the expense definition. No NOI means no asserted cap rate. |
| Debt yield | Matching annual NOI divided by relevant debt balance. A historical mortgage face amount may not be that balance. |
| DSCR | Matching NOI divided by annual debt service. Payment type, interest rate, amortization, and period must be known or explicitly assumed. |
| Leverage | Debt divided by the appropriate value or cost denominator. Debt/price is not automatically appraised LTV; distinguish LTV and LTC. |
| Development basis | Acquisition plus documented budget components; show what is excluded. Compare buildable-area prices only on a consistent entitlement basis. |
| Scenarios | Disclosed hypothetical inputs, deterministic calculations, and a separate display labeled illustrative. Never present modeled economics as the actual deal terms. |

Distinguish new money from assignments, modifications, consolidations, extensions, and satisfactions. Do not sum every recorded mortgage document into a capital stack. A recorded lien is evidence of an instrument, not proof of the funded balance, current exposure, or sponsor equity.

Use comparables selected by asset type, micro-market, transaction date, scale, condition, tenancy, interest conveyed, and development status. Explain exclusions. A tiny comp set can frame the deal but cannot establish a broad market conclusion. Keep market data publication dates and underlying measurement periods visible.

For applicable stories, investigate rent regulation, affordability commitments, tax benefits and expirations, zoning, development rights, landmarks, environmental obligations, and building energy requirements. Report verified applicability and economics; do not assume a rule applies because a building is in NYC.

## Narrative and voice

The story starts with the most revealing supported detail: an unusual price comparison, a long ownership period, a lender's position, a changed use, or the people whose daily lives intersect with the building. The opening earns attention; the next paragraphs explain what traded and why the detail matters.

Weave financing into the narrative at the moment it explains a decision. A technical appendix cannot rescue a story whose main argument ignores the capital stack. Explain a term once when readers need it and keep moving.

Humanity comes from actual tenants, merchants, owners, employees, neighborhood institutions, documented history, and real reporting notes. Wit comes from precise observation and financial irony. Never invent a sidewalk scene, quotation, interview, personal visit, private feeling, or insider access. Do not turn residents' difficulties into a punchline. Ben's first-person experience requires an authentic supplied note.

Possible architectures include a building's second life, the gap between price and economic basis, a seller's documented change in strategy, a buyer entering a different market, or a financing structure that explains an otherwise puzzling price. Choose the architecture after research. Avoid assigning every deal the same dramatic plot.

Proposed formats:

- **Transaction story:** usually 700–1,200 words, with a clear angle, economics, human or historical context, uncertainty, and a useful ending.
- **Deep feature:** usually 1,200–1,800 words when evidence and reporting justify the space.
- **Verified transaction account:** usually 250–500 words while important reporting remains open; a candidate for later expansion.
- **Development follow-up:** evidence-sized coverage of a material new project stage, linked to the sale and property history.

Word counts guide editing. They are never minimum content quotas. All confirmed qualifying transactions remain eligible for substantive treatment regardless of story score. Scoring prioritizes research effort and homepage placement.

Each article includes a compact deal facts panel, links near material claims, original reporting credit, published/updated timestamps, and any material correction. An optional economics panel shows calculation inputs and definitions. Research gaps belong near affected claims; do not bury a disputed price in a generic footer.

End on a concrete unresolved question or observable next milestone when one exists. Avoid generic claims that a single sale signals confidence, distress, recovery, or a new era.

## Separate validation for facts and analysis

Use five claim types: `reported_fact`, `derived_metric`, `analysis`, `voice`, and `reporting_note`.

Reported facts require attributable evidence. Derived metrics require reproducible calculations from verified inputs. Analysis requires referenced premises, a bounded conclusion, and a stated alternative where material. Voice may add personality without adding facts, allegations, or implied reporting. A reporting note can establish a visit or conversation only when an authentic note is supplied and approved for use.

Reuse current fact checks where compatible. Add an NYC-specific calculation and analysis adapter, and evaluate the existing voice gate before reuse. Keep current general-pipeline behavior stable. Do not paste computed numbers into synthetic source text to make a quotation check pass, and do not simply enable unchecked opinion in the shared verifier.

Block release for unsupported core facts, unresolved material price/identity conflicts, incorrect calculations, invented quotes or experience, or unreviewed serious allegations. If failed sentences are removed, re-evaluate the thesis, references, transitions, and conclusion; a collection of individually safe sentences is not necessarily a sound article.

Human editorial review is the proposed launch policy for this new franchise, not a permission request for preparing this plan. It establishes the voice and catches failures the pilot needs to reveal. After demonstrated quality, verified accounts may become eligible for automatic release; long features and sensitive reporting should retain editorial review.

## Software architecture and Intelligence integration

Use a dedicated `scripts/nyc_transactions/` package and `config/nyc_transactions.json`. Give the desk independent discovery watermarks, candidate records, research queue, prompt versions, budgets, and reports. Reuse retrieval, provider routing, evidence types, logging, rendering, and deployment infrastructure through explicit interfaces.

Proposed modules: `models.py`, `sources.py`, `registry.py`, `resolve.py`, `eligibility.py`, `research.py`, `economics.py`, `editor.py`, `generation.py`, `verification.py`, `publication.py`, and `cli.py`. Choose final boundaries after inspecting current interfaces; these names are a starting map, not a requirement to create empty files.

For the pilot, use durable versioned JSON records under a private desk state directory with atomic writes and locks, and publish only selected public fields under `data/nyc-transactions/`. Never upload raw licensed articles, private notes, or full internal evidence with the public site. The repo is also the static site deployment source, so hidden filenames alone do not establish privacy. Validate deploy exclusions and artifact access. Move the internal registry to a database if concurrent editing and record volume outgrow the pilot store.

The desk discovers continuously and publishes independently. Existing broad-market selection must not filter out an otherwise eligible NYC sale. A single publication coordinator should serialize all writers to shared files. Prefer staging a complete output bundle, validating it, then promoting it together. Do not run two unattended jobs that overwrite `insights.json`, feed, sitemap, or the same edition document.

At the adapter boundary preserve `DraftResult` and `IntelligenceObject` compatibility where useful. Inspect the actual writer/publisher contract rather than forcing the new desk through legacy slate selection.

Add explicit manifest fields such as `vertical: nyc_transactions`, `transaction_id`, `property_ids`, `borough`, `transaction_type`, `closing_date`, `price`, `price_basis`, and `coverage_status`. Keep `category` compatible with existing CRE filters. Update `update_manifest` and relevant summary serializers; arbitrary article keys are not guaranteed to survive them.

Add an NYC Buildings entry on `insights.html`, backed by the vertical field, with borough, use, transaction type, date, and address search. Let readers distinguish closed sales, development updates, and reporting still in progress. Preserve existing sector navigation and mobile behavior. Deal facts should be readable without opening an internal research interface.

Create linked property histories and a public transaction ledger once the data is reliable. The existing `transactions.html` may serve a different commercial purpose; inspect it before proposing reuse. Do not mix Light Tower's own deal credentials with independently reported market transactions.

Choose featured NYC stories for the general Intelligence page by editorial quality; keep the full desk discoverable in its own view. If adding an edition section, extend edition schema and `edition.js` deliberately and retain old editions. A new NYC run must not replace the broad-market latest edition with an NYC-only payload.

Implement stable canonical story URLs and explicit versions. Minor corrections update the story with a log; material new lifecycle events may get a new linked article. Preserve prior versions internally. Link general and NYC coverage of the same transaction and prevent duplicate distribution.

## Implementation sequence and completion gates

### Phase 1 — Coverage model and evidence access

Define the coverage rules, source registry, access gaps, typed records, event identities, and fixture corpus. Test actual access to the intended structured data and Staten Island route. Import a 12-month sales baseline in shadow mode and manually reconcile a sample in every borough. Deliver a source-access report and coverage methodology before calling the intake comprehensive.

Completion gate: fixtures correctly distinguish a sale from a mortgage, exact-threshold cases, multi-parcel portfolios, partial interests, non-NYC assets, and nominal transfers. Every candidate has an explanation; the registry survives reruns.

### Phase 2 — Research and financial analysis

Implement targeted research, source lineage, property histories, conflict handling, and deterministic calculations. Prioritize primary evidence and retrieve history beyond the news lookback. Record failed and blocked searches. Produce reusable dossiers without generating public pages.

Completion gate: manually audit at least 15 real transactions, with representation from all five boroughs and different asset types. Do not manufacture a qualifying recent transaction to meet the borough sample; widen the historical window and record that choice. Every displayed metric can be reproduced from its evidence and assumptions.

### Phase 3 — Editorial pilot

Implement angle selection, a bounded writer, separate verification routes, and final coherence review. Draft approximately ten representative stories: straightforward, underreported, disputed, development-heavy, and financially complex. Ben edits these into an approved voice reference set. Identify which stories need original reporting and prepare interview questions without sending them.

Completion gate: no unsupported material factual claims, invented experience, or math errors in the reviewed pilot; every piece has an identifiable deal-specific argument. Editor scores reporting, financial understanding, local knowledge, readability, narrative, humanity, wit, and uncertainty from 1 to 5. Target at least 4 in reporting, finance, and readability; an average never overrides a factual failure. Do not score humor by counting jokes.

### Phase 4 — Page integration and review publication

Add manifest metadata, NYC filters, article facts/economics panels, related-property links, staged publication, and update handling. Ship behind a feature flag in preview/review mode first. Test combined existing and new content. Inspect desktop and mobile layouts, source links, empty results, long addresses, and keyboard controls.

Completion gate: general Insights remains usable, NYC content survives full rebuilds, repeated publication is idempotent, corrections update the intended canonical story, and simultaneous desk/general runs cannot lose index entries.

### Phase 5 — Scheduled operation and coverage audit

Only after the pilot passes, enable the chosen schedule and release policy. Run a 30-day observation period with weekly reconciliation. Measure detection, dossier completion, and publication coverage separately. Report cost per researched/published deal, stage latency, backlog age, source outages, corrections, and late-discovered sales.

Initial service targets: accessible qualifying news enters the registry within one business day; each confirmed eligible sale gets a first research pass within two business days; stories with sufficient evidence reach editorial review within five business days. These clocks start at discovery and do not imply instant public-record availability. Never drop old queue items merely to keep the dashboard green.

For observable reconciliation datasets, target at least 95% of manually adjudicated eligible closings matched or explicitly queued during the pilot, with every borough reported separately. This is a pilot acceptance target, not a present coverage claim. Set the final service target after measuring volume and source latency.

## Runtime and operating controls

Set independent daily discovery, retrieval, research, and generation budgets. Before buying access or choosing exact model spend, measure the first real dossiers. Report requests, tokens, search/retrieval cost, elapsed time, and completed outputs by transaction. Do not borrow the historic per-article estimates in older architecture documents as current prices.

Initial bounds: three research rounds per transaction, at most one writer revision after review, explicit per-source and per-run limits, and persistent checkpoints. Use deterministic code for identity, eligibility, arithmetic, and state transitions; reserve model work for ambiguous extraction, synthesis, writing, and review. Cache by evidence hashes, effective dates, schema versions, and prompt versions. A changed source or assumption invalidates dependent calculations and text.

Return distinct run outcomes: `healthy_no_new_sales`, `completed`, `partial_source_coverage`, `budget_exhausted_with_backlog`, and `failed`. Unlike the current general workflow's zero-output publication failure gate, this desk must allow a successful day with no newly eligible sale. An outage yielding zero discoveries must not look like a quiet market.

Launch responsibility is explicit: the automated desk collects and prepares; Ben owns the publication's editorial judgment; a developer owns pipeline reliability and access configuration. Log each release decision and correction. A claimed standard of reporting has to be maintained through edits, follow-ups, and accountability as well as prompts.
