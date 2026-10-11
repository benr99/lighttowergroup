# Capital Stack Radar — Milestone B progress (2026-10-11)

## Status: IN PROGRESS; NOT SIGNED OFF
Latest live authenticated acceptance suite: 21/21 tests passed, validating the research infrastructure and truthfulness of completion flags; this **does not** imply Milestone B's investment-evidence acceptance gates have passed.

### Latest measured source coverage
- Total target tax lots: 4,436.
- Last checked: 576 attempted; 571 successful, 5 partial, zero errors; 3,860 unattempted (12.87% successful coverage). These are point-in-time counts and not forecasts. Two partial properties were subsequently reported repaired; rerun the coverage endpoint for current totals.
- 20,637 distinct indexed ACRIS Master documents; 22,028 property-to-document evidence links.
- Ten original research dossiers: 452 indexed financing events and 23 explicit source-derived reference edges. The 452 events were grouped into 429 **provisional reference components**, not verified loans.
- Separate Parties/Legals enrichment: 105 document source checks successful as observed, no failures in those batches. Verify fresh counts from API for current coverage.
- Zero independently verified current principal balances, actual loan maturities, legally confirmed financing facilities or certified distressed acquisitions.

### Deployed services (preserve Railway IDs)
Project `ac6e0eea-bc03-4a2a-ad9b-d2f3c2da07a9`, environment `c8d28521-cddf-4ae0-b81b-91209717c6ca`.
- Core ACRIS intake `c40d0d79-b7c6-4479-8c19-b3a02327b7e9`: 48 candidates every 5 minutes; bounded source pagination and DB lease; source upsert can be retried.
- Explicit ACRIS reference collector `dc3facba-687f-4272-85bc-be48837028c5`: every 5 minutes on the 4,9,14,... minute marks.
- Party and collateral document evidence `2462fa5d-b3c4-4a92-93fe-10b15a1e630a`: 35 documents every 5 minutes.
- Partial source pagination repair `8c8852c0-1bbc-4db3-8ff5-bf40b51ce7df`: 23 and 43 minutes past the hour.
- Reference-connected research graph `c13efd5f-a21a-47ca-8fa2-03943b2c2520`: 31 minutes past each hour.
- Milestone B research API `8dba3fba-ba8f-4ce4-b9ae-ccd663933f29`: authenticated HTTP.
- Milestone B acceptance `bcb2da94-cb65-46f5-9ab7-93e580b360b7`: 37 minutes past every hour.
- Existing research UI `88a916be-1d96-4de3-a190-b4af61f44be2`: displays Milestone B evidence; continues to proxy Milestone A and Release 2.2.
- All other infrastructure and data retained.

### Routes and tests
- `GET /api/milestone-b/coverage` authenticated.
- `GET /api/milestone-b/research-queue?limit=10` authenticated.
- `GET /api/milestone-b/dossier?bbl=<10-digit BBL>` authenticated.
- Research UI: https://radar-research-ui-development.up.railway.app/universe
- Independent API: https://radar-milestone-b-research-api-development.up.railway.app
- Authenticated suite checks authorization, 4,436-lot denominator, collection-count reconciliation, ten dossiers, document-component count, precise evidence caveats, input validation, client-side browser script, UI proxy and unauthorized rejection; 21/21 passed at 12:13 UTC.

### Open acceptance gates, despite successful software tests
1. Full 4,436-lot ingestion with complete or explicitly documented exceptions (last measured successful: 571).
2. All selected primary mortgage and amendment images, legal facility linkage and independent legal review.
3. Verified contractual maturities, extensions, current creditor and current payoff or explicitly unobtainable terms.
4. Ten defensible signed-off loan-family dossiers; none are signed off.
5. Independent loan-collateral relationship and borrower/lender party audit; don't count a recorded instrument amount as outstanding debt.
6. Staging/production Git-controlled deployment, disaster recovery tests, and source-license and information-security reviews are still unfinished.
7. Later Milestones C, D and E (underwriting, opportunity scoring, origination CRM, production security) are NOT complete.

**Important source distinction:** ACRIS Master and Legals/Parties indexes are public-record metadata. A source-complete index still does not prove every signed legal instrument or private loan balance has been obtained. No distressed acquisition qualification is claimed.

This branch is an engineering snapshot, not a CI/CD-backed deployment. Do not overwrite existing Railway secrets, project IDs, service IDs or legacy tables.