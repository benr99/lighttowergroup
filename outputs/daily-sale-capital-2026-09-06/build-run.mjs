import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-06";
const outputPath = `${outputDir}/light-tower-multifamily-sale-capital-2026-09-06.xlsx`;
const wb = Workbook.create();
const sheet = wb.worksheets.add("Run 2026-09-06");
sheet.showGridLines = false;

const navy = "#102A43", slate = "#486581", pale = "#EAF2F8", green = "#D9EAD3", amber = "#FFF2CC", red = "#FCE4D6", gray = "#F3F4F6", white = "#FFFFFF";
const border = { preset: "all", style: "thin", color: "#D9E2EC" };
const section = (range, label, color = navy) => { sheet.getRange(range).merge(); sheet.getRange(range.split(":")[0]).values = [[label]]; sheet.getRange(range).format = { fill: color, font: { bold: true, color: white }, verticalAlignment: "center" }; };

sheet.getRange("A1:S1").merge();
sheet.getRange("A1").values = [["Light Tower Group — Daily $10M+ Multifamily Sale & Capital Opportunity Engine"]];
sheet.getRange("A1:S1").format = { fill: navy, font: { bold: true, color: white, size: 16 }, verticalAlignment: "center" };
sheet.getRange("A1:S1").format.rowHeight = 30;
sheet.getRange("A2:S2").merge();
sheet.getRange("A2").values = [["Run date: September 6, 2026 (America/New_York)  |  Report-only  |  Targeted public-source sweep"]];
sheet.getRange("A2:S2").format = { fill: pale, font: { color: navy, italic: true }, verticalAlignment: "center" };
sheet.getRange("A2:S2").format.rowHeight = 22;
section("A4:S4", "Executive readout", slate);
sheet.getRange("A5:S6").merge();
sheet.getRange("A5").values = [["New: PHI-009 International City Apartments is a 1,068-unit Philadelphia MSA sale process reported independently on August 31 and September 1; the verified 2019 portfolio value was $141M, but the current asking price is undisclosed. Continuing LA-011 Park.1915, LA-012 The Palms, LA-010 3675 Dunn Drive, and CHI-004 Washington Plaza remain publicly available. New Van Nuys 68-unit listing is Watch only because its market date is not published. No prospect outreach was drafted, queued, scheduled, implied, or sent. Coverage is targeted public-source research in named MSAs only—never universal coverage."]];
sheet.getRange("A5:S6").format = { fill: gray, wrapText: true, verticalAlignment: "top", borders: { preset: "outside", style: "thin", color: "#D9E2EC" } };
sheet.getRange("A5:S6").format.rowHeight = 30;

section("A8:S8", "Action queue — 85+ priority and 75–84 qualified only");
const headers = [["Lead ID", "Classification", "$10M Gate", "Asset / Address / MSA", "Units", "Owner / Sponsor / Lender / Broker", "Observed facts", "Inference", "Counterargument", "Sale", "Capital", "Fit", "Execution", "Evidence", "Contact", "Score", "Tier / source / date", "Verified public contact", "Light Tower angle"]];
sheet.getRange("A9:S9").values = headers;
sheet.getRange("A9:S9").format = { fill: slate, font: { bold: true, color: white }, wrapText: true, horizontalAlignment: "center", verticalAlignment: "center", borders: border };
sheet.getRange("A9:S9").format.rowHeight = 34;
const actions = [
  ["PHI-009", "Pre-Marketing / Quiet Sale", "$141M verified 2019 portfolio value; current ask undisclosed", "International City Apartments, 7900 & 8400 Lindbergh Blvd, Philadelphia, PA 19153 | Philadelphia MSA", 1068, "AJH Management (seller); Newmark sale team: Carl Fiebig, Erin Miller, Maura Kate Spellman, Chris Koehler, Marybeth Farris, Griffin McGovern", "New: two independent Tier 2 reports (Aug. 31 and Sept. 1) state AJH has put the 1,068-unit, 64-building conventional apartment complex on the market; 2019 acquisition value was $141M and Newmark is marketing a value-add sale process.", "Large, current sale process supports sale advisory, buyer financing, bridge / preferred equity, recapitalization, or seller/lender dialogue.", "No public current asking price or OM; confirm seller authority, current bidding process, rent restrictions / subsidy exposure, tax abatement, T-12, and capital plan before engagement.", 32, 0, 15, 9, 15, 5, null, "Tier 2 Bisnow (2026-08-31) + Private Real Estate Daily (2026-09-01); Newmark contact verification | https://www.bisnow.com/news/philadelphia/multifamily/largest-apartment-complex-for-sale-international-city ; https://www.nmrk.com/people/carl-fiebig", "Carl Fiebig, Newmark | 215-470-5826 | Carl.Fiebig@nmrk.com; Erin Miller, Newmark | Erin.Miller@nmrk.com", "Sale advisory; buyer financing; bridge / preferred equity; recapitalization; lender dialogue"],
  ["LA-011", "Active Sale", "$18.0M asking", "Park.1915, 1915 Park Ave, Los Angeles, CA 90026 | Los Angeles MSA", 36, "Marcus & Millichap | Neema Ahadian, Jeffrey Estrada; owner/sponsor (CIM) not independently verified", "Continuing Tier 1 exclusive: 36-unit conventional apartment asset completed 2025; $18.0M ask; 4.52% cap; live listing dated 2026-08-17 and currently available Sept. 6.", "Fresh conventional marketing supports acquisition-sale advisory, buyer financing, senior refinance or recapitalization.", "Confirm rent roll, seller authority, occupancy, and any project-level affordability covenant before engagement.", 35, 0, 15, 9, 15, 5, null, "Tier 1 M&M exclusive + Tier 1 LoopNet | observed 2026-09-06 / listed 2026-08-17 | https://www.marcusmillichap.com/properties/304677/park1915", "Neema Ahadian | (310) 909-5444; Jeffrey Estrada | (310) 909-5423", "Buyer financing; acquisition-sale advisory; senior refinance / recap"],
  ["LA-012", "Active Sale", "$14.95M asking", "The Palms, 3929 W 242nd St, Torrance, CA 90505 | Los Angeles MSA", 48, "Marcus & Millichap | Tyler Leeson; owner not independently verified", "Continuing Tier 1 exclusive / current MLS: 48-unit conventional garden apartment asset built 1961; $14.95M ask; 5.36% cap; listed 2026-08-17 and repriced 2026-08-24. Public MLS page says for sale and was rechecked Sept. 6.", "Fresh, price-adjusted marketing supports acquisition-sale advisory, buyer financing, senior refinance or recapitalization.", "City source indicates no permanent local RSO, but confirm state-law applicability, project covenants, rent roll, seller authority, and renovation claims before engagement.", 35, 0, 13, 9, 15, 5, null, "Tier 1 M&M exclusive + current MLS corroboration | observed 2026-09-06 | https://www.redfin.com/CA/Torrance/3929-W-242nd-St-90505/home/7720293", "Tyler Leeson | (949) 419-3326 | tleeson@marcusmillichap.com", "Buyer financing; acquisition-sale advisory; value-add senior refinance / recap"],
  ["LA-010", "Active Sale", "$15.95M asking", "3675 Dunn Drive, Los Angeles, CA 90034 | Los Angeles MSA", 18, "KW Commercial | Alex Galuz; owner not independently verified", "Continuing Tier 1 listing: 2019 Class A, 18-unit apartment property; $15.95M ask; dated 2026-08-03; currently available Sept. 6.", "Live marketing supports buyer financing, acquisition-sale advisory, or senior refinance / recap.", "Confirm current seller authority, rent roll / cap-rate assumptions, and any recorded affordability covenant before engagement.", 35, 0, 15, 9, 15, 5, null, "Tier 1 direct listing | observed 2026-09-06 | https://www.loopnet.com/Listing/3675-Dunn-Dr-Los-Angeles-CA/41534752/", "Alex Galuz, KW Commercial | +1 310-466-0888", "Buyer financing; acquisition-sale advisory; senior refinance / recap"],
  ["CHI-004", "Active Sale", "$12.0M asking", "Washington Plaza, 5501 W Washington Blvd, Chicago, IL 60644 | Chicago MSA", 172, "33 Realty | Brian Mond and George Benitez; owner not independently verified", "Continuing Tier 1 listing currently available Sept. 6: 172 apartments; $12.0M ask; 98% stated occupancy; listed 2026-07-22.", "Live marketing supports buyer financing, acquisition-sale advisory, or value-add senior refinance / recap.", "Confirm subsidy contracts, deferred maintenance, seller authority, and rent-roll quality before engagement.", 35, 0, 14, 9, 15, 5, null, "Tier 1 direct listing | observed 2026-09-06 | https://www.loopnet.com/Listing/5501-W-Washington-Blvd-Chicago-IL/41395207/", "Brian Mond | +1 773-615-2626; George Benitez | +1 239-443-0768", "Buyer financing; acquisition-sale advisory; senior refinance"]
];
sheet.getRange("A10:S14").values = actions;
sheet.getRange("P10:P14").formulas = [["=SUM(J10:O10)"],["=SUM(J11:O11)"],["=SUM(J12:O12)"],["=SUM(J13:O13)"],["=SUM(J14:O14)"]];
sheet.getRange("A10:S14").format = { wrapText: true, verticalAlignment: "top", borders: border };
sheet.getRange("A10:S14").format.rowHeight = 96;
sheet.getRange("A10:C14").format.fill = green;
sheet.getRange("P10:P14").format = { fill: green, font: { bold: true }, horizontalAlignment: "center", verticalAlignment: "center", borders: border };
sheet.getRange("E10:E14").format.numberFormat = "#,##0";
sheet.getRange("J10:P14").format.numberFormat = "0";

section("A16:S16", "Watch — 65–74; not actionable until the precise verification step below is completed", "#8A6D1D");
sheet.getRange("A17:E17").values = [["Lead", "Classification", "Score", "Reason held", "Concrete next verification step"]];
sheet.getRange("A17:E17").format = { fill: amber, font: { bold: true, color: navy }, wrapText: true, verticalAlignment: "center", borders: border };
const watch = [
  ["LA-014 — 13724 Victory Blvd.", "Watch", 73, "Direct broker site reports a current $22.9M / 68-unit / 2022-built conventional multifamily offering in Van Nuys, but does not publish the listing date, so the mandatory date gate is incomplete.", "Obtain a dated exclusive / MLS record, current OM, named asset-level broker, rent roll, seller authority, and covenant confirmation before promotion."],
  ["CHI-001 — Drexel Terraces", "Capital Event", 74, "Latest corroborated catalyst is stale.", "Pull current Cook County docket / receiver order; verify servicer, borrower, balance, and sale or workout timetable."],
  ["CHI-003 — 4520–26 S. Drexel Blvd.", "Capital Event", 74, "Primary foreclosure record remains unverified.", "Obtain Cook County primary docket and receiver order; then verify servicer and sale timetable."],
  ["FL-003 — California Club Apartments", "Watch", 74, "Current mandate and restrictions unverified.", "Obtain exclusive mandate, current OM / rent roll, named broker, and restriction confirmation."],
  ["FL-001 — Gables Galiano", "Watch", 73, "Extended marketing; mandate freshness uncertain.", "Obtain current broker mandate, seller intent, and price-flexibility confirmation."],
  ["NY-001 — 30-Unit MF Portfolio Sale", "Watch", 73, "Portfolio regulatory status and mandate unverified.", "Obtain current mandate, component-building regulatory checks, and current pricing."],
  ["LA-009 — 1400 Venice Blvd.", "Watch", 72, "Mandatory dated listing record absent.", "Obtain a dated exclusive / MLS record, current availability, and OM."],
  ["LA-003 — Nabi Apartments", "Watch", 72, "New dated active listing clears the date gate, but historic CDFI/project-covenant record requires regulatory confirmation.", "Obtain recorded affordability covenant / title confirmation and current T-12; then reassess for action status."],
  ["LA-008 — The Cooper Hollywood", "Watch", 71, "RSO status unresolved.", "Obtain HCIDLA RSO determination and OM rent-regulation disclosure."],
  ["FL-006 — The Genesis Clearwater", "Capital Event", 71, "Foreclosure report lacks primary debt / lien evidence.", "Pull Pinellas complaint, mortgage / assignment, balance, lender-borrower linkage, restriction evidence, and current deal contact."],
  ["FL-007 — 650 SW 1st St., Miami", "Watch", 70, "Mixed-use / price gate unresolved.", "Obtain signed sale mandate with explicit total ask, rent roll, retail-income share, restriction confirmation, and named broker contact."],
  ["FL-005 — The Wave Apartments, Tampa", "Capital Event", 69, "Default reporting lacks primary record.", "Pull Hillsborough complaint, mortgage / assignment, lender-borrower linkage, and restriction evidence."],
  ["FL-008 — 300 Majorca Ave., Coral Gables", "Watch", 68, "Market date, rental status, and covenants unresolved.", "Obtain current mandate, listing date, rental-versus-condo status, and covenant confirmation."],
  ["LA-013 — Park Terrace Apartments", "Watch", 68, "Current $10.8M / 51-unit listing has 1979 vintage and an aged May listing date; exact certificate-of-occupancy / RSO status is unresolved.", "Confirm City RSO status, recorded covenants, current exclusive mandate, and rent roll before action-queue promotion."]
];
sheet.getRange("A18:E31").values = watch;
sheet.getRange("A18:E31").format = { wrapText: true, verticalAlignment: "top", borders: border };
sheet.getRange("A18:E31").format.rowHeight = 42;
sheet.getRange("C18:C31").format = { fill: amber, font: { bold: true }, horizontalAlignment: "center", verticalAlignment: "center", borders: border };

section("A33:S33", "Exclusions and coverage gaps", "#9B3A1D");
sheet.getRange("A34:D34").values = [["Item", "Classification", "Reason", "Source / coverage note"]];
sheet.getRange("A34:D34").format = { fill: red, font: { bold: true, color: navy }, wrapText: true, verticalAlignment: "center", borders: border };
sheet.getRange("A35:D38").values = [
  ["1020 SW 2nd St., Miami", "Excluded", "20 apartments at $325,000/unit imply about $6.5M—below the $10M gate.", "Tier 1 direct listing | https://www.loopnet.com/Listing/1020-SW-2nd-St-Miami-FL/41479349/"],
  ["PHI-006 — 2328–2344 N. 2nd St.", "Excluded", "33 apartments plus 3,750 SF retail and four townhome-approved parcels: materially mixed / development-inclusive.", "Tier 1 direct listing | https://www.loopnet.com/Listing/2328-2344-N-2nd-St-Philadelphia-PA/41009347/"],
  ["Retained legacy exclusions", "Excluded", "Development/mixed-use: 2629 NW 17th and Sunshine (Miami); RSO/affordable or un-cleared covenant: The Peake, Centennial, Metropolitan Building; student/rent-by-bed Philadelphia items; unverified availability: Kenmore East.", "Retained from prior verified screenings; do not promote without new primary evidence."],
  ["Coverage gaps", "Coverage limitation", "No newly verified action lead in NYC; named North Carolina MSAs; Orlando, Jacksonville, Fort Myers, Naples, Sarasota, Palm Bay, Lakeland, or Daytona Beach.", "Targeted public-source sweep only; absence is not evidence that an eligible property does not exist."]
];
sheet.getRange("A35:D38").format = { wrapText: true, verticalAlignment: "top", borders: border };
sheet.getRange("A35:D38").format.rowHeight = 54;
sheet.getRange("A35:B38").format.fill = red;
sheet.getRange("A40:S40").merge();
sheet.getRange("A40").values = [["Controls: No outreach was drafted, queued, scheduled, implied, or sent. Outreach requires the user's explicit approval of named lead IDs for this specific run. Historical $20M tabs were not modified."]];
sheet.getRange("A40:S40").format = { fill: gray, font: { italic: true, color: navy }, wrapText: true, verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: "#D9E2EC" } };
sheet.getRange("A40:S40").format.rowHeight = 28;
const widths = { A:18,B:16,C:18,D:34,E:9,F:31,G:42,H:34,I:35,J:8,K:8,L:8,M:10,N:10,O:9,P:9,Q:43,R:34,S:34 };
for (const [col, width] of Object.entries(widths)) sheet.getRange(`${col}:${col}`).format.columnWidth = width;
sheet.freezePanes.freezeRows(9);
const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "formula error scan" });
console.log(errors.ndjson);
const check = await wb.inspect({ kind: "table", range: "Run 2026-09-06!A8:S14", include: "values,formulas", tableMaxRows: 7, tableMaxCols: 19, tableMaxCellChars: 60 });
console.log(check.ndjson);
await fs.mkdir(outputDir, { recursive: true });
const out = await SpreadsheetFile.exportXlsx(wb);
await out.save(outputPath);
console.log(`SAVED ${outputPath}`);
