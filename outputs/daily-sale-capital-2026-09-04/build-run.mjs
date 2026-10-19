import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const source = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-03/light-tower-multifamily-sale-capital-2026-09-03.xlsx";
const outputDir = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-04";
const outputPath = `${outputDir}/light-tower-multifamily-sale-capital-2026-09-04.xlsx`;
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(source));
const sheetName = "Run 2026-09-04";
const sheet = workbook.worksheets.add(sheetName);
sheet.showGridLines = false;

const navy = "#102A43";
const slate = "#486581";
const paleBlue = "#EAF2F8";
const green = "#D9EAD3";
const amber = "#FFF2CC";
const red = "#FCE4D6";
const gray = "#F3F4F6";
const white = "#FFFFFF";

sheet.getRange("A1:O1").merge();
sheet.getRange("A1").values = [["Light Tower Group — Daily $10M+ Multifamily Sale & Capital Opportunity Engine"]];
sheet.getRange("A1:O1").format = { fill: navy, font: { bold: true, color: white, size: 16 }, horizontalAlignment: "left", verticalAlignment: "center" };
sheet.getRange("A1:O1").format.rowHeight = 30;
sheet.getRange("A2:O2").merge();
sheet.getRange("A2").values = [["Run date: September 4, 2026 (America/New_York)  |  Report-only  |  Targeted public-source sweep"]];
sheet.getRange("A2:O2").format = { fill: paleBlue, font: { color: navy, italic: true }, verticalAlignment: "center" };
sheet.getRange("A2:O2").format.rowHeight = 22;
sheet.getRange("A4:O4").merge();
sheet.getRange("A4").values = [["Executive readout"]];
sheet.getRange("A4:O4").format = { fill: slate, font: { bold: true, color: white }, verticalAlignment: "center" };
sheet.getRange("A5:O6").merge();
sheet.getRange("A5").values = [["No new qualified lead cleared every hard gate. Two continuing active-sale leads remain in the action queue. Washington Plaza's Tier 1 record was crawled today; 3675 Dunn Drive remains marked currently available on its public Tier 1 listing (the platform snapshot was crawled last week). No prospect outreach was drafted, queued, scheduled, implied, or sent. Coverage is targeted public-source research in the named MSAs only—never universal MSA, Florida, or North Carolina coverage."]];
sheet.getRange("A5:O6").format = { fill: gray, wrapText: true, verticalAlignment: "top", borders: { preset: "outside", style: "thin", color: "#D9E2EC" } };
sheet.getRange("A5:O6").format.rowHeight = 30;

sheet.getRange("A8:O8").merge();
sheet.getRange("A8").values = [["Action queue — 85+ priority and 75–84 qualified only"]];
sheet.getRange("A8:O8").format = { fill: navy, font: { bold: true, color: white }, verticalAlignment: "center" };
const headers = [["Lead ID", "Classification", "$10M Gate", "Asset / Address / MSA", "Units", "Owner / Sponsor / Lender / Broker", "Observed facts", "Inference", "Counterargument", "Sale", "Capital", "Fit", "Execution", "Evidence", "Contact", "Score", "Tier / source / date", "Verified public contact", "Light Tower angle"]];
sheet.getRange("A9:S9").values = headers;
sheet.getRange("A9:S9").format = { fill: slate, font: { bold: true, color: white }, wrapText: true, horizontalAlignment: "center", verticalAlignment: "center", borders: { preset: "all", style: "thin", color: "#D9E2EC" } };
sheet.getRange("A9:S9").format.rowHeight = 34;
const actionRows = [
  ["LA-010", "Active Sale", "$15.95M asking", "3675 Dunn Drive, Los Angeles, CA 90034 | Los Angeles MSA", 18, "KW Commercial | Alex Galuz; owner not independently verified", "Tier 1 listing calls the 2019, Class A, 18-unit apartment property currently available; asking $15.95M; listing date 2026-08-03.", "Fresh conventional marketing supports buyer financing, sale advisory, or senior refinance / recap.", "Confirm current seller authority, rent roll / cap-rate assumptions, and any recorded affordability covenant before engagement.", 35, 0, 15, 9, 15, 5, null, "Tier 1 direct listing | observed 2026-09-04 | https://www.loopnet.com/Listing/3675-Dunn-Dr-Los-Angeles-CA/41534752/", "Alex Galuz, KW Commercial | +1 310-466-0888", "Buyer financing; acquisition-sale advisory; senior refinance / recap"],
  ["CHI-004", "Active Sale", "$12.0M asking", "Washington Plaza, 5501 W Washington Blvd, Chicago, IL 60644 | Chicago MSA", 172, "33 Realty | Brian Mond and George Benitez; owner not independently verified", "Tier 1 listing is currently available; 172 apartments; $12.0M asking; stated 98% occupancy; listing date 2026-07-22.", "Live marketing supports buyer financing, sale advisory, or value-add refinance / recap.", "Confirm subsidy contracts, deferred maintenance, seller authority, and rent-roll quality before engagement.", 35, 0, 14, 9, 15, 5, null, "Tier 1 direct listing | observed 2026-09-04 | https://www.loopnet.com/Listing/5501-W-Washington-Blvd-Chicago-IL/41395207/", "Brian Mond | +1 773-615-2626; George Benitez | +1 239-443-0768", "Buyer financing; acquisition-sale advisory; senior refinance"]
];
sheet.getRange("A10:S11").values = actionRows;
sheet.getRange("P10").formulas = [["=SUM(J10:O10)"]];
sheet.getRange("P11").formulas = [["=SUM(J11:O11)"]];
sheet.getRange("A10:S11").format = { wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: "#D9E2EC" } };
sheet.getRange("A10:S11").format.rowHeight = 96;
sheet.getRange("A10:C11").format.fill = green;
sheet.getRange("P10:P11").format = { fill: green, font: { bold: true }, horizontalAlignment: "center", verticalAlignment: "center", borders: { preset: "all", style: "thin", color: "#D9E2EC" } };
sheet.getRange("E10:E11").format.numberFormat = "#,##0";
sheet.getRange("J10:P11").format.numberFormat = "0";

sheet.getRange("A13:S13").merge();
sheet.getRange("A13").values = [["Watch — 65–74; not actionable until the precise verification step below is completed"]];
sheet.getRange("A13:S13").format = { fill: "#8A6D1D", font: { bold: true, color: white }, verticalAlignment: "center" };
sheet.getRange("A14:E14").values = [["Lead", "Classification", "Score", "Reason held", "Concrete next verification step"]];
sheet.getRange("A14:E14").format = { fill: amber, font: { bold: true, color: navy }, wrapText: true, verticalAlignment: "center", borders: { preset: "all", style: "thin", color: "#D9E2EC" } };
const watchRows = [
  ["CHI-001 — Drexel Terraces", "Capital Event", 74, "Latest corroborated catalyst is stale.", "Pull current Cook County docket / receiver order; verify servicer, borrower, balance, and sale or workout timetable."],
  ["CHI-003 — 4520–26 S. Drexel Blvd.", "Capital Event", 74, "Primary foreclosure record remains unverified.", "Obtain Cook County primary docket and receiver order; then verify servicer and sale timetable."],
  ["FL-003 — California Club Apartments", "Watch", 74, "Current mandate and restrictions unverified.", "Obtain exclusive mandate, current OM / rent roll, named broker, and restriction confirmation."],
  ["FL-001 — Gables Galiano", "Watch", 73, "Extended marketing; mandate freshness uncertain.", "Obtain current broker mandate, seller intent, and price-flexibility confirmation."],
  ["NY-001 — 30-Unit MF Portfolio Sale", "Watch", 73, "Portfolio regulatory status and mandate unverified.", "Obtain current mandate, component-building regulatory checks, and current pricing."],
  ["LA-009 — 1400 Venice Blvd.", "Watch", 72, "Mandatory dated listing record absent.", "Obtain a dated exclusive / MLS record, current availability, and OM."],
  ["LA-003 — Nabi Apartments", "Watch", 72, "Listing date and covenant status unresolved.", "Obtain current mandate, dated listing, covenant status, and T-12."],
  ["LA-008 — The Cooper Hollywood", "Watch", 71, "RSO status unresolved.", "Obtain HCIDLA RSO determination and OM rent-regulation disclosure."],
  ["FL-006 — The Genesis Clearwater", "Capital Event", 71, "Foreclosure report lacks primary debt / lien evidence.", "Pull Pinellas complaint, mortgage / assignment, balance, lender-borrower linkage, restriction evidence, and current deal contact."],
  ["FL-007 — 650 SW 1st St., Miami", "Watch", 70, "Mixed-use / price gate unresolved.", "Obtain signed sale mandate with explicit total ask, rent roll, retail-income share, restriction confirmation, and named broker contact."],
  ["FL-005 — The Wave Apartments, Tampa", "Capital Event", 69, "Default reporting lacks primary record.", "Pull Hillsborough complaint, mortgage / assignment, lender-borrower linkage, and restriction evidence."],
  ["FL-008 — 300 Majorca Ave., Coral Gables", "Watch", 68, "Market date, rental status, and covenants unresolved.", "Obtain current mandate, listing date, rental-versus-condo status, and covenant confirmation."]
];
sheet.getRange("A15:E26").values = watchRows;
sheet.getRange("A15:E26").format = { wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: "#D9E2EC" } };
sheet.getRange("A15:E26").format.rowHeight = 40;
sheet.getRange("C15:C26").format = { fill: amber, font: { bold: true }, horizontalAlignment: "center", verticalAlignment: "center", borders: { preset: "all", style: "thin", color: "#D9E2EC" } };

sheet.getRange("A28:S28").merge();
sheet.getRange("A28").values = [["Exclusions and coverage gaps"]];
sheet.getRange("A28:S28").format = { fill: "#9B3A1D", font: { bold: true, color: white }, verticalAlignment: "center" };
sheet.getRange("A29:D29").values = [["Item", "Classification", "Reason", "Source / coverage note"]];
sheet.getRange("A29:D29").format = { fill: red, font: { bold: true, color: navy }, wrapText: true, verticalAlignment: "center", borders: { preset: "all", style: "thin", color: "#D9E2EC" } };
const excludedRows = [
  ["1020 SW 2nd St., Miami", "Excluded", "20 apartments at $325,000/unit imply about $6.5M—below the $10M gate.", "Tier 1 direct listing | 2026-07-29 market date | https://www.loopnet.com/Listing/1020-SW-2nd-St-Miami-FL/41479349/"],
  ["PHI-006 — 2328–2344 N. 2nd St.", "Excluded", "33 apartments plus 3,750 SF retail and four townhome-approved parcels: materially mixed / development-inclusive.", "Tier 1 direct listing | https://www.loopnet.com/Listing/2328-2344-N-2nd-St-Philadelphia-PA/41009347/"],
  ["Retained legacy exclusions", "Excluded", "Development / mixed-use: 2629 NW 17th and Sunshine (Miami); RSO / affordable or un-cleared covenant: The Peake, Centennial, Metropolitan Building; student / rent-by-bed Philadelphia items; stale or no-longer-advertised Kenmore East.", "Retained from prior verified screenings; do not promote without new primary evidence."],
  ["Coverage gaps", "Coverage limitation", "No newly verified $10M+ action lead in NYC; named North Carolina MSAs; Orlando, Jacksonville, Fort Myers, Naples, Sarasota, Palm Bay, Lakeland, or Daytona Beach.", "A targeted public-source sweep only; absence from this report is not evidence that an eligible property does not exist."]
];
sheet.getRange("A30:D33").values = excludedRows;
sheet.getRange("A30:D33").format = { wrapText: true, verticalAlignment: "top", borders: { preset: "all", style: "thin", color: "#D9E2EC" } };
sheet.getRange("A30:D33").format.rowHeight = 54;
sheet.getRange("A30:B33").format.fill = red;

sheet.getRange("A35:S35").merge();
sheet.getRange("A35").values = [["Controls: No outreach was drafted, queued, scheduled, implied, or sent. Outreach requires the user's explicit approval of named lead IDs for this specific run. Historical $20M tabs were not modified."]];
sheet.getRange("A35:S35").format = { fill: gray, font: { italic: true, color: navy }, wrapText: true, verticalAlignment: "center", borders: { preset: "outside", style: "thin", color: "#D9E2EC" } };
sheet.getRange("A35:S35").format.rowHeight = 28;

const widths = { A: 18, B: 16, C: 18, D: 34, E: 9, F: 31, G: 42, H: 34, I: 35, J: 8, K: 8, L: 8, M: 10, N: 10, O: 9, P: 9, Q: 43, R: 32, S: 34 };
for (const [col, width] of Object.entries(widths)) sheet.getRange(`${col}:${col}`).format.columnWidth = width;
sheet.freezePanes.freezeRows(9);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan" });
console.log(errors.ndjson);
const check = await workbook.inspect({ kind: "table", range: `${sheetName}!A8:S11`, include: "values,formulas", tableMaxRows: 4, tableMaxCols: 19 });
console.log(check.ndjson);
await fs.mkdir(outputDir, { recursive: true });
const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(outputPath);
console.log(`SAVED ${outputPath}`);
