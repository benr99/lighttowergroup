import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const source = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-04/light-tower-multifamily-sale-capital-2026-09-04.xlsx";
const outputDir = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-05";
const outputPath = `${outputDir}/light-tower-multifamily-sale-capital-2026-09-05.xlsx`;
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(source));
const sheet = wb.worksheets.add("Run 2026-09-05");
sheet.showGridLines = false;

const navy = "#102A43", slate = "#486581", pale = "#EAF2F8", green = "#D9EAD3", amber = "#FFF2CC", red = "#FCE4D6", gray = "#F3F4F6", white = "#FFFFFF";
const border = { preset: "all", style: "thin", color: "#D9E2EC" };
const section = (range, label, color = navy) => { sheet.getRange(range).merge(); sheet.getRange(range.split(":")[0]).values = [[label]]; sheet.getRange(range).format = { fill: color, font: { bold: true, color: white }, verticalAlignment: "center" }; };

sheet.getRange("A1:S1").merge();
sheet.getRange("A1").values = [["Light Tower Group — Daily $10M+ Multifamily Sale & Capital Opportunity Engine"]];
sheet.getRange("A1:S1").format = { fill: navy, font: { bold: true, color: white, size: 16 }, verticalAlignment: "center" };
sheet.getRange("A1:S1").format.rowHeight = 30;
sheet.getRange("A2:S2").merge();
sheet.getRange("A2").values = [["Run date: September 5, 2026 (America/New_York)  |  Report-only  |  Targeted public-source sweep"]];
sheet.getRange("A2:S2").format = { fill: pale, font: { color: navy, italic: true }, verticalAlignment: "center" };
sheet.getRange("A2:S2").format.rowHeight = 22;
section("A4:S4", "Executive readout", slate);
sheet.getRange("A5:S6").merge();
sheet.getRange("A5").values = [["Two newly verified Los Angeles MSA active-sale leads cleared every hard gate: LA-011 Park.1915 ($18.0M / 36 units) and LA-012 The Palms ($14.95M / 48 units). Continuing LA-010 3675 Dunn Drive and CHI-004 Washington Plaza remain available. Nabi now has a dated live listing but remains Watch because a project-level affordability/covenant check is still required. No prospect outreach was drafted, queued, scheduled, implied, or sent. Coverage is targeted public-source research in named MSAs only—never universal coverage."]];
sheet.getRange("A5:S6").format = { fill: gray, wrapText: true, verticalAlignment: "top", borders: { preset: "outside", style: "thin", color: "#D9E2EC" } };
sheet.getRange("A5:S6").format.rowHeight = 30;

section("A8:S8", "Action queue — 85+ priority and 75–84 qualified only");
const headers = [["Lead ID", "Classification", "$10M Gate", "Asset / Address / MSA", "Units", "Owner / Sponsor / Lender / Broker", "Observed facts", "Inference", "Counterargument", "Sale", "Capital", "Fit", "Execution", "Evidence", "Contact", "Score", "Tier / source / date", "Verified public contact", "Light Tower angle"]];
sheet.getRange("A9:S9").values = headers;
sheet.getRange("A9:S9").format = { fill: slate, font: { bold: true, color: white }, wrapText: true, horizontalAlignment: "center", verticalAlignment: "center", borders: border };
sheet.getRange("A9:S9").format.rowHeight = 34;
const actions = [
  ["LA-011", "Active Sale", "$18.0M asking", "Park.1915, 1915 Park Ave, Los Angeles, CA 90026 | Los Angeles MSA", 36, "Marcus & Millichap | Neema Ahadian, Jeffrey Estrada; owner/sponsor (CIM) not independently verified", "New Tier 1 exclusive listing: 36-unit conventional apartment asset completed 2025; $18.0M ask; 4.52% cap rate; live listing date 2026-08-17.", "Fresh conventional marketing supports acquisition-sale advisory, buyer financing, senior refinance or recapitalization.", "Confirm rent roll, seller authority, occupancy, and any project-level affordability covenant before engagement.", 35, 0, 15, 9, 15, 5, null, "Tier 1 M&M exclusive + Tier 1 LoopNet | 2026-09-05 / listed 2026-08-17 | https://www.marcusmillichap.com/properties/304677/park1915", "Neema Ahadian | (310) 909-5444; Jeffrey Estrada | (310) 909-5423", "Buyer financing; acquisition-sale advisory; senior refinance / recap"],
  ["LA-012", "Active Sale", "$14.95M asking", "The Palms, 3929 W 242nd St, Torrance, CA 90505 | Los Angeles MSA", 48, "Marcus & Millichap | Tyler Leeson; owner not independently verified", "New Tier 1 exclusive listing: 48-unit conventional garden apartment asset built 1961; $14.95M ask; 5.36% cap; MLS listed 2026-08-17 and repriced 2026-08-24.", "Fresh, price-adjusted marketing supports acquisition-sale advisory, buyer financing, senior refinance or recapitalization.", "City source indicates no permanent local RSO, but confirm state-law applicability, project covenants, rent roll, seller authority, and renovation claims before engagement.", 35, 0, 13, 9, 15, 5, null, "Tier 1 M&M exclusive + MLS corroboration | 2026-09-05 | https://www.marcusmillichap.com/properties/308515/the-palms", "Tyler Leeson | (949) 419-3326 | tleeson@marcusmillichap.com", "Buyer financing; acquisition-sale advisory; value-add senior refinance / recap"],
  ["LA-010", "Active Sale", "$15.95M asking", "3675 Dunn Drive, Los Angeles, CA 90034 | Los Angeles MSA", 18, "KW Commercial | Alex Galuz; owner not independently verified", "Continuing Tier 1 listing: 2019 Class A, 18-unit apartment property; $15.95M ask; dated 2026-08-03; public listing index remains for-sale.", "Live marketing supports buyer financing, acquisition-sale advisory, or senior refinance / recap.", "Confirm current seller authority, rent roll / cap-rate assumptions, and any recorded affordability covenant before engagement.", 35, 0, 15, 9, 15, 5, null, "Tier 1 direct listing | observed 2026-09-05 | https://www.loopnet.com/Listing/3675-Dunn-Dr-Los-Angeles-CA/41534752/", "Alex Galuz, KW Commercial | +1 310-466-0888", "Buyer financing; acquisition-sale advisory; senior refinance / recap"],
  ["CHI-004", "Active Sale", "$12.0M asking", "Washington Plaza, 5501 W Washington Blvd, Chicago, IL 60644 | Chicago MSA", 172, "33 Realty | Brian Mond and George Benitez; owner not independently verified", "Continuing Tier 1 listing currently available: 172 apartments; $12.0M ask; 98% stated occupancy; listed 2026-07-22.", "Live marketing supports buyer financing, acquisition-sale advisory, or value-add senior refinance / recap.", "Confirm subsidy contracts, deferred maintenance, seller authority, and rent-roll quality before engagement.", 35, 0, 14, 9, 15, 5, null, "Tier 1 direct listing | observed 2026-09-05 | https://www.loopnet.com/Listing/5501-W-Washington-Blvd-Chicago-IL/41395207/", "Brian Mond | +1 773-615-2626; George Benitez | +1 239-443-0768", "Buyer financing; acquisition-sale advisory; senior refinance"]
];
sheet.getRange("A10:S13").values = actions;
sheet.getRange("P10:P13").formulas = [["=SUM(J10:O10)"],["=SUM(J11:O11)"],["=SUM(J12:O12)"],["=SUM(J13:O13)"]];
sheet.getRange("A10:S13").format = { wrapText: true, verticalAlignment: "top", borders: border };
sheet.getRange("A10:S13").format.rowHeight = 96;
sheet.getRange("A10:C13").format.fill = green;
sheet.getRange("P10:P13").format = { fill: green, font: { bold: true }, horizontalAlignment: "center", verticalAlignment: "center", borders: border };
sheet.getRange("E10:E13").format.numberFormat = "#,##0";
sheet.getRange("J10:P13").format.numberFormat = "0";

section("A15:S15", "Watch — 65–74; not actionable until the precise verification step below is completed", "#8A6D1D");
sheet.getRange("A16:E16").values = [["Lead", "Classification", "Score", "Reason held", "Concrete next verification step"]];
sheet.getRange("A16:E16").format = { fill: amber, font: { bold: true, color: navy }, wrapText: true, verticalAlignment: "center", borders: border };
const watch = [
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
sheet.getRange("A17:E29").values = watch;
sheet.getRange("A17:E29").format = { wrapText: true, verticalAlignment: "top", borders: border };
sheet.getRange("A17:E29").format.rowHeight = 42;
sheet.getRange("C17:C29").format = { fill: amber, font: { bold: true }, horizontalAlignment: "center", verticalAlignment: "center", borders: border };

section("A31:S31", "Exclusions and coverage gaps", "#9B3A1D");
sheet.getRange("A32:D32").values = [["Item", "Classification", "Reason", "Source / coverage note"]];
sheet.getRange("A32:D32").format = { fill: red, font: { bold: true, color: navy }, wrapText: true, verticalAlignment: "center", borders: border };
sheet.getRange("A33:D36").values = [
  ["1020 SW 2nd St., Miami", "Excluded", "20 apartments at $325,000/unit imply about $6.5M—below the $10M gate.", "Tier 1 direct listing | https://www.loopnet.com/Listing/1020-SW-2nd-St-Miami-FL/41479349/"],
  ["PHI-006 — 2328–2344 N. 2nd St.", "Excluded", "33 apartments plus 3,750 SF retail and four townhome-approved parcels: materially mixed / development-inclusive.", "Tier 1 direct listing | https://www.loopnet.com/Listing/2328-2344-N-2nd-St-Philadelphia-PA/41009347/"],
  ["Retained legacy exclusions", "Excluded", "Development/mixed-use: 2629 NW 17th and Sunshine (Miami); RSO/affordable or un-cleared covenant: The Peake, Centennial, Metropolitan Building; student/rent-by-bed Philadelphia items; unverified availability: Kenmore East.", "Retained from prior verified screenings; do not promote without new primary evidence."],
  ["Coverage gaps", "Coverage limitation", "No newly verified action lead in NYC; named North Carolina MSAs; Orlando, Jacksonville, Fort Myers, Naples, Sarasota, Palm Bay, Lakeland, or Daytona Beach.", "Targeted public-source sweep only; absence is not evidence that an eligible property does not exist."]
];
sheet.getRange("A33:D36").format = { wrapText: true, verticalAlignment: "top", borders: border };
sheet.getRange("A33:D36").format.rowHeight = 54;
sheet.getRange("A33:B36").format.fill = red;
sheet.getRange("A38:S38").merge();
sheet.getRange("A38").values = [["Controls: No outreach was drafted, queued, scheduled, implied, or sent. Outreach requires the user's explicit approval of named lead IDs for this specific run. Historical $20M tabs were not modified."]];
sheet.getRange("A38:S38").format = { fill: gray, font: { italic: true, color: navy }, wrapText: true, verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: "#D9E2EC" } };
sheet.getRange("A38:S38").format.rowHeight = 28;
const widths = { A:18,B:16,C:18,D:34,E:9,F:31,G:42,H:34,I:35,J:8,K:8,L:8,M:10,N:10,O:9,P:9,Q:43,R:34,S:34 };
for (const [col, width] of Object.entries(widths)) sheet.getRange(`${col}:${col}`).format.columnWidth = width;
sheet.freezePanes.freezeRows(9);
const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "formula error scan" });
console.log(errors.ndjson);
const check = await wb.inspect({ kind: "table", range: "Run 2026-09-05!A8:S13", include: "values,formulas", tableMaxRows: 6, tableMaxCols: 19, tableMaxCellChars: 60 });
console.log(check.ndjson);
await fs.mkdir(outputDir, { recursive: true });
const out = await SpreadsheetFile.exportXlsx(wb);
await out.save(outputPath);
console.log(`SAVED ${outputPath}`);
