# Capital Stack Radar — Milestone A Engineering Handoff

**Status (2026-10-11):** Technical source-coverage, provisional property identity, historic regulation screening, authenticated research UI, and protected export have passed acceptance. Economic asset ownership and legal free-market status are **not** certified.

## Existing Railway identifiers (preserve)
Project `ac6e0eea-bc03-4a2a-ad9b-d2f3c2da07a9`; environment `c8d28521-cddf-4ae0-b81b-91209717c6ca`. Use existing Postgres and RADAR_API_KEY references. Never commit variable values.

| Service | Railway service ID | Cadence |
|---|---|---|
| Milestone A indexer | `1b0276ed-e374-412d-8665-b97f8bddb554` | 16 minutes past every hour |
| Milestone A integrity watch | `c5ae79bd-1057-411b-999a-e2d9f3f6ea24` | 28 minutes past every hour |
| Milestone A acceptance | `ccef071b-74ce-4ef7-96a0-615279d08f4b` | 10:42 UTC daily |
| Milestone A research API | `0622014d-066e-4749-a5b6-b8ca19834be1` | HTTP |
| HPD historic sales signals | `1b5b02ca-91ba-4ece-b33c-4fff182124a2` | 04:09 UTC Mondays |
| HPD Buildings collector | `5c014f21-1eae-4d83-8e51-810752037352` | Every ten minutes |
| DOF Exemption collector | `e94219ab-4f82-4977-9bd6-347e65f0f161` | Every ten minutes |
| Existing research UI | `88a916be-1d96-4de3-a190-b4af61f44be2` | HTTP |
| Original radar API | `5f33c252-fb9e-4e2b-aeab-a2a243fa7ef5` | HTTP |

## Verified results
- Source PLUTO tax lots: 318,610 (Manhattan 42,504 and Brooklyn 276,106).
- 70+ residential-unit qualifying tax lots: 4,436.
- Stable `LOT:{BBL}` research identifiers: 4,436; regulation review records: 4,436.
- Every candidate has two open research exception categories (identity and rent regulation), rather than an unsubstantiated verification.
- HCR historical registration matches: 2,540; unlisted but still unverified: 1,896.
- HPD/DOF collector success statuses: 4,436 candidate lots each.
- Historic HPD qualified sales source: 1,720 source rows, 82 candidate BBL matches.
- Historic HPD speculation source: 797 rows, 31 candidate BBL matches.
- Evidence ledger: at least 55,683 source evidence records.
- Independent physical HPD BIN links identified, but legal common ownership and aggregation **not** inferred.
- Database invariant gate PASSED; authenticated API, browser, proxy and 4,436-row CSV acceptance: 25/25 PASSED.
- Hourly integrity watch passed 15 hard gates on its first run.

## Research UI and API
- [UI](https://radar-research-ui-development.up.railway.app/universe)
- [Protected Milestone A API](https://radar-milestone-a-research-api-development.up.railway.app/api/milestone-a/summary)
- `GET /api/milestone-a/summary`
- `GET /api/milestone-a/assets` supports borough, identity, regulation, max_units, limit and offset
- `GET /api/milestone-a/asset?bbl=...`
- `GET /api/milestone-a/exceptions`
- `GET /api/milestone-a/export.csv`

All /api endpoints require the existing Bearer token. The research UI proxies them through its existing same-origin authorization behavior.

## Critical limitations
- These are tax-lot *research identities*, **not** verified economic rental assets. HPD BIN links are physical identifier hypotheses; 2,050 lots carry preliminary condo/co-op exceptions, and some lots contain multiple HPD buildings.
- Historical HCR listing is **not** current unit-by-unit rent-regulation certification; absence of a match is not proof of free-market.
- DOF exemptions require review of benefit type and legal restrictions. Historic LL7 and speculation sales are not current distress evidence.
- Full property-by-property legal review, unit roll verification and current ownership are open due-diligence work. Do not use an automated screen as an investment eligibility certification.
- GitHub branch contains snapshots of the five new Milestone A services, **not** every legacy Railway worker nor a connected CI/CD production deployment. Live Railway remains source of truth until controlled deployment setup is completed.

## Additional production-hardening still open
- Create a dedicated private repository or adopt this isolated branch through review; establish tests and migrations as the source of truth for deployments.
- Implement tested database backups and recovery, RBAC, secured sessions, automated staging, rollback, audit permissions.
- Improve precise source-snapshot reconciliation and automatically notify on a failing integrity watch.
- Historical HPD source file had 1,720 fetched rows but 1,714 distinct content-hash entries due identical duplicates; store a stable occurrence identifier if exact row-level preservation becomes legally or analytically necessary.

## Operational rule
Never substitute unit-regulation, lender/loan, asset-ownership or economic-property legal conclusions for source-linked preliminary evidence. Preserve existing service identifiers, data and credentials.
