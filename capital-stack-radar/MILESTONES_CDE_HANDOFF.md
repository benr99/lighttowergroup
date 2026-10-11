# Capital Stack Radar — Milestones C, D and E engineering handoff — 2026-10-11

## Verified now
- Existing Capital Stack Radar Railway project and development environment preserved. All newly added services have deployed successfully.
- C scenario underwriting: annual debt service, LTV / DSCR / debt yield constrained debt, initial equity, annual cash flow, debt amortization, exit cash proceeds, illustrative IRR/equity multiple, and explicit assumed-payoff refinance gap.
- D origination: public-source-linked RESEARCH_ONLY lead record, professional profile evidence, audit event, and draft-only outreach. The investment qualification API refuses promotion absent review.
- E release assessor: hourly snapshots of technical gates, evidence gates and production-security/operations gates. Release status API shows actual open items. First review = 5/6 technical, 0/8 investment evidence, 0/9 operations; therefore PRODUCTION NOT READY.
- Existing research UI integrates C/D/E and retains A/B/Release 2.2. All relevant proxied APIs require the existing bearer key.
- 29/29 initial C/D service acceptance checks passed; 20/20 live cross-service UI and production-gate checks passed after fixing serialization of JSONB release gates.
- The C/D/E integration test now repeats hourly at minute 47; E release assessment repeats hourly at minute 18.
- ACRIS intake retained at 48 tax lots every five minutes, protected by a database lease. Recent live runs each completed 48 attempted lots without failure. The last measured full coverage report was 571 successful lots / 4436 before these newer runs; query the live B coverage API for up-to-date totals, do not extrapolate.
- Five new C–E source files and tests committed on an isolated branch. Live Railway source stays authoritative until Git-controlled deployment is separately implemented.

## Railway service IDs
Project: `ac6e0eea-bc03-4a2a-ad9b-d2f3c2da07a9`
Environment: `c8d28521-cddf-4ae0-b81b-91209717c6ca`
- C underwriting `f61b41bd-37ba-4073-ab46-814ac6348678`
- D origination `3b9fc9f4-9165-4154-9361-c1effb00cbea`
- E release assessor `e6a1ad23-ccac-4a43-898e-a1c1baf38ca3`
- E release API `91205275-0e77-408e-a111-5c723c598207`
- C/D/E acceptance `6916cec8-54bd-47a4-aa47-2dcd4058767c`
- UI `88a916be-1d96-4de3-a190-b4af61f44be2`

## Hard blockers to sign-off
1. Full 4436-tax-lot ACRIS coverage, all incomplete collection rows resolved or explicitly excepted.
2. Ten real loan facilities supported by original executed instruments, amendments, collateral release histories, lender confirmation and independently verified contractual maturity/payoff.
3. Financial operating evidence: real rent rolls, T-12 NOI, property-specific costs, market cap-rate support, and ten independently reviewed valuation/refinancing models.
4. Owner/entity identity and rent-regulation legal verification; no property can be called definitively free-market based on HCR absence.
5. Ten evidence-supported actionable acquisitions, rather than synthetic scenarios or source-only lead records.
6. Production security: per-user authentication and roles/MFA, staging and rehearsed rollback, audit review, signed-off licenses, production performance/security assessment.
7. Railway Postgres point-in-time recovery and tested restoration are NOT confirmed. Railway documentation describes PITR, but no account-specific status or restore has passed.
8. Incident notification and disaster recovery procedures with proven RTO/RPO still not tested.

**Do not label Milestone E or all A–E milestones complete.** Current product is an integrated development/research system with substantial engineering tests passed and material investment-evidence and production controls open.

## Operational URLs
- Research desk: https://radar-research-ui-development.up.railway.app/universe
- GitHub branch: https://github.com/benr99/lighttowergroup/tree/capital-stack-radar-milestones-cde-2026-10-11/capital-stack-radar
- Railway project: https://railway.com/project/ac6e0eea-bc03-4a2a-ad9b-d2f3c2da07a9
