import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = "C:/Users/Ben/Downloads/Lighttowergroupsite";
const prior = `${root}/outputs/daily-sale-capital-2026-09-06/light-tower-multifamily-sale-capital-2026-09-06.xlsx`;
const outputDir = `${root}/outputs/daily-sale-capital-2026-09-07`;
const outputPath = `${outputDir}/light-tower-multifamily-sale-capital-2026-09-07.xlsx`;

const file = await FileBlob.load(prior);
const workbook = await SpreadsheetFile.importXlsx(file);
const sheet = workbook.worksheets.add("Run 2026-09-07");
sheet.showGridlines = false;

const dark = "#17365D";
const blue = "#D9EAF7";
const lightBlue = "#EAF3F8";
const amber = "#FFF2CC";
const red = "#FCE4D6";
const green = "#E2F0D9";
const font = { name: "Arial", size: 10, color: "#1F1F1F" };

sheet.getRange("A1:Z1").merge();
sheet.getRange("A1").values = [["Light Tower Group — $10M+ Multifamily Sale & Capital Opportunity Engine"]];
sheet.getRange("A1").format = { font: { name: "Arial", size: 14, bold: true, color: dark } };
sheet.getRange("A2:Z2").merge();
sheet.getRange("A2").values = [["Run date: September 7, 2026  |  Report-only  |  Targeted public-source coverage; not universal MSA or statewide coverage"]];
sheet.getRange("A2").format = { font: { name: "Arial", size: 10, italic: true, color: "#555555" } };

sheet.getRange("A4:B7").values = [
  ["Action queue", "5 continuing leads"],
  ["Priority 85+", "None"],
  ["Qualified 75–84", "5"],
  ["New qualified leads", "None"],
];
sheet.getRange("D4:E7").values = [
  ["Watch 65–74", "15 leads"],
  ["Excluded", "8 categories"],
  ["$10M Gate", "Required for action queue"],
  ["Outreach", "Requires named-lead approval"],
];
sheet.getRange("A4:A7").format = { fill: blue, font: { name: "Arial", size: 10, bold: true, color: dark } };
sheet.getRange("D4:D7").format = { fill: blue, font: { name: "Arial", size: 10, bold: true, color: dark } };
sheet.getRange("B4:B7").format = { fill: "#F9FBFD", font };
sheet.getRange("E4:E7").format = { fill: "#F9FBFD", font };

const actionHeaders = [[
  "Lead ID", "Status", "Classification", "$10M Gate", "Asset / Address", "MSA", "Units", "Owner / Sponsor / Lender / Listing Broker",
  "Observed facts", "Inference", "Counterargument", "Sale process 35", "Capital event 20", "Fit 15", "Execution 10", "Evidence / recency 15", "Public contacts 5", "Score", "Sources / dates", "Verified public contact", "Light Tower angle"
]];
sheet.getRange("A9:U9").values = actionHeaders;
const actions = [
  ["LA-011", "Continuing", "Active Sale", 18000000, "Park.1915, 1915 Park Ave.", "Los Angeles", 36, "Marcus & Millichap", "Tier 1 listing current; 2025 construction; listed Aug. 17, 2026.", "Near-term sale advisory and acquisition-finance conversation.", "Confirm rent restrictions, CO, seller authority, rent roll, and actual 2025 results.", 34, 0, 15, 10, 15, 5, null, "LoopNet | listed Aug. 17, 2026 | crawled Sep. 6 | https://www.loopnet.com/Listing/1915-Park-Avenue-Los-Angeles-CA/41776924/", "Neema Ahadian (310) 909-5444; Jeffrey Estrada (310) 909-5423", "Sale advisory; buyer financing; senior refinance"],
  ["LA-010", "Continuing", "Active Sale", 15950000, "3675 Dunn Dr.", "Los Angeles", 18, "Alex Galuz, KW Commercial", "Tier 1 listing remains available; Class A, 2019 construction; listed Aug. 3, 2026.", "Buyer financing and structured recapitalization potential.", "Confirm seller authority, affordability covenant, current rent roll, and actual debt.", 34, 0, 15, 10, 15, 5, null, "LoopNet | listed Aug. 3, 2026 | current search crawl Sep. 7 | https://www.loopnet.com/Listing/3675-Dunn-Dr-Los-Angeles-CA/41534752/", "Alex Galuz (310) 466-0888", "Sale advisory; buyer financing; senior refinance; recapitalization"],
  ["CHI-004", "Continuing", "Active Sale", 12000000, "Washington Plaza, 5501 W Washington Blvd.", "Chicago", 172, "33 Realty", "Tier 1 listing current; 98% occupancy; listed Jul. 22, 2026.", "Buyer financing, bridge, or recapitalization potential.", "Confirm subsidy contracts, deferred maintenance, seller authority, rent roll, and capex plan.", 33, 0, 15, 10, 15, 5, null, "LoopNet | listed Jul. 22, 2026 | crawled Sep. 1 | https://www.loopnet.com/Listing/5501-W-Washington-Blvd-Chicago-IL/41395207/", "Brian Mond (773) 615-2626; George Benitez (239) 443-0768", "Sale advisory; buyer financing; bridge; recapitalization"],
  ["LA-012", "Continuing", "Active Sale", 14950000, "The Palms, 3929 W 242nd St.", "Los Angeles", 48, "Marcus & Millichap", "Tier 1 listing current; conventional 48-unit garden asset; listed Aug. 17, 2026.", "Dated exclusive marketing supports buyer financing and a value-add capital plan.", "Verify rent-control status, seller authority, rent roll, capex plan, and restrictions.", 32, 0, 15, 10, 15, 5, null, "LoopNet | listed Aug. 17, 2026 | crawled Sep. 7 | https://www.loopnet.com/Listing/3929-W-242nd-St-Torrance-CA/41776427/", "Tyler Leeson (714) 713-9086", "Sale advisory; buyer financing; bridge; preferred equity"],
  ["PHI-009", "Continuing", "Pre-Marketing / Quiet Sale", 141000000, "International City Apartments, 7900 & 8400 Lindbergh Blvd.", "Philadelphia", 1068, "AJH Management; Newmark", "Two recent Tier 2 reports identify a Newmark-led sale process for a 44-acre, 64-building apartment complex.", "Institutional sale process may need sale advisory, buyer financing, preferred equity, recapitalization, or lender dialogue.", "Obtain OM, bid timing, seller authority, price, restrictions, T-12, and capex plan.", 32, 0, 15, 9, 15, 5, null, "Bisnow Aug. 31 + Hoodline Sep. 1 | https://www.bisnow.com/news/philadelphia/multifamily/largest-apartment-complex-for-sale-international-city | https://hoodline.com/2026/09/eastwick-s-1-068-unit-international-city-apartments-hits-market-tests-philly-rent-ceiling/", "Carl Fiebig (215) 470-5826, Carl.Fiebig@nmrk.com; Erin Miller, Newmark", "Sale advisory; buyer financing; bridge; preferred equity; recapitalization; lender dialogue"],
];
sheet.getRange("A10:U14").values = actions;
sheet.getRange("R10").formulas = [["=SUM(L10:Q10)"]];
sheet.getRange("R10:R14").fillDown();

sheet.getRange("A16:H16").merge();
sheet.getRange("A16").values = [["Watch — 65–74: evidence or product gates still open"]];
sheet.getRange("A16").format = { fill: amber, font: { name: "Arial", size: 11, bold: true, color: dark } };
sheet.getRange("A17:F17").values = [["Lead ID", "Classification", "Asset / MSA", "Score", "Reason held", "Precise next verification step"]];
const watch = [
  ["CHI-003", "Watch", "4520–26 S. Drexel, Chicago", 74, "Secondary foreclosure reporting is not a current primary record.", "Obtain Cook County docket, receiver order, complaint, payoff, and current marketing status."],
  ["LA-014", "Watch", "13724 Victory Blvd., Van Nuys / Los Angeles", 73, "No listing date, OM, or asset-level contact is published.", "Obtain dated exclusive or MLS, OM, rent roll, seller authority, and covenant evidence."],
  ["LA-003", "Watch", "Nabi Apartments, Los Angeles", 72, "Historical CDFI/project evidence requires regulatory clearance.", "Check recorded affordability covenant, title, HCD records, and deed restrictions."],
  ["FL-001", "Watch", "Gables Galiano, Coral Gables / Miami", 71, "Extended marketing weakens current sale-process evidence.", "Obtain current broker mandate, OM, rent roll, restrictions confirmation, and seller authority."],
  ["FL-006", "Watch", "Genesis Clearwater, Clearwater / Tampa", 71, "Foreclosure reporting lacks primary debt and party linkage.", "Obtain Pinellas complaint, mortgage/assignment, debt balance, lender/borrower link, and restrictions."],
  ["FL-007", "Watch", "650 SW 1st St., Miami", 70, "21 apartments plus retail; no explicit total ask.", "Obtain signed mandate with total ask, residential-income split, rent roll, restrictions, and broker."],
  ["PHI-008", "Watch", "220–222 Church, Philadelphia", 70, "Unit count, commercial scope, and mandate are inconsistent.", "Obtain OM, lease/rent roll, 40-versus-45-unit reconciliation, and broker mandate."],
  ["PHI-007", "Watch", "The Maxfield, Philadelphia", 70, "Listing age weakens current availability.", "Obtain current exclusive, T-12, rent roll, and seller-authority confirmation."],
  ["FL-005", "Watch", "The Wave Apartments, Tampa", 69, "Default reporting lacks a primary foreclosure record.", "Obtain Hillsborough complaint, mortgage/assignment, lender/borrower linkage, and restrictions."],
  ["FL-003", "Watch", "California Club, Miami", 69, "Current mandate evidence is insufficiently recent.", "Obtain current listing agreement, units/price confirmation, rent roll, and restrictions check."],
  ["LA-007", "Watch", "The Jeffries, Los Angeles", 69, "Current availability and regulatory status lack corroboration.", "Obtain live broker mandate, RSO/affordability clearance, price, and rent roll."],
  ["NY-001", "Watch", "30-unit portfolio, NYC", 68, "Stabilization status and current sale process are unclear.", "Obtain HPD/DHCR records, current OM, address list, price, and broker authority."],
  ["LA-008", "Watch", "The Cooper, Los Angeles", 68, "Current listing needs RSO determination.", "Verify HCIDLA RSO status, title/covenants, and current broker mandate."],
  ["LA-009", "Watch", "1400 Venice Blvd., Los Angeles", 68, "Ask lacks a dated current listing record.", "Obtain dated exclusive/MLS, seller authority, RSO/covenant status, and rent roll."],
  ["LA-013", "Watch", "Park Terrace Apartments, Los Angeles", 68, "Aged mandate and occupancy/regulatory evidence unresolved.", "Obtain current mandate, CO, RSO determination, title/covenants, and rent roll."],
];
sheet.getRange("A18:F32").values = watch;

sheet.getRange("A34:C34").merge();
sheet.getRange("A34").values = [["Excluded and coverage gaps"]];
sheet.getRange("A34").format = { fill: red, font: { name: "Arial", size: 11, bold: true, color: dark } };
sheet.getRange("A35:C35").values = [["Item", "Classification", "Exclusion reason"]];
const excluded = [
  ["1020 SW 2nd St., Miami", "Excluded", "20 units at $325,000/unit imply about $6.5M, below the $10M gate."],
  ["2629 NW 17th Ave., Miami", "Excluded", "Explicitly marketed as a covered-land/high-density Live Local/workforce-housing development play."],
  ["2328–2344 N. 2nd St., Philadelphia", "Excluded", "Apartments bundled with retail suites and townhome-approved parcels; materially mixed/development-inclusive."],
  ["4200 Ludlow; 4042/4046–48 Chestnut; 3207 Spring Garden, Philadelphia", "Excluded", "Student/rent-by-bed product."],
  ["The Centennial; Metropolitan Building, Los Angeles", "Excluded", "Rent-stabilized/affordable status outside the primary unrestricted queue."],
  ["The Peake; 4186 S. Western; 1350 W. Court, Los Angeles", "Excluded", "Verified restricted-affordable or project-specific affordable requirement."],
  ["Sunshine, 4110 NW 22nd Ave., Miami", "Excluded", "Under-construction/materially mixed-use product."],
  ["Allapattah 23, Miami", "Excluded", "Repriced to $9.5M and classified as multifamily dormitory product."],
];
sheet.getRange("A36:C43").values = excluded;

sheet.getRange("A45:U45").merge();
sheet.getRange("A45").values = [["Coverage limitation: targeted public-source sweep only. NYC, Los Angeles, Chicago, Philadelphia, named Florida MSAs, and named North Carolina MSAs were screened; absence of a lead is not evidence that no opportunity exists. No outreach was drafted, queued, scheduled, implied, or sent."]];
sheet.getRange("A45").format = { fill: lightBlue, font: { name: "Arial", size: 10, italic: true, color: "#555555" }, wrapText: true, verticalAlignment: "center" };
sheet.getRange("A46:U46").merge();
sheet.getRange("A46").values = [["Google Drive/Sheets connector unavailable: established Google Sheet and historical $20M tabs were left untouched. Authenticated Gmail session exists, but no email was sent because sending requires action-time confirmation."]];
sheet.getRange("A46").format = { fill: lightBlue, font: { name: "Arial", size: 10, italic: true, color: "#555555" }, wrapText: true, verticalAlignment: "center" };

sheet.getRange("A9:U9").format = { fill: dark, font: { name: "Arial", size: 9, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
sheet.getRange("A17:F17").format = { fill: dark, font: { name: "Arial", size: 9, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
sheet.getRange("A35:C35").format = { fill: dark, font: { name: "Arial", size: 9, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
sheet.getRange("A10:U14").format.font = font;
sheet.getRange("A18:F32").format.font = font;
sheet.getRange("A36:C43").format.font = font;
sheet.getRange("A10:U14").format.wrapText = true;
sheet.getRange("A18:F32").format.wrapText = true;
sheet.getRange("A36:C43").format.wrapText = true;
sheet.getRange("D10:D14").format.numberFormat = '"$"#,##0';
sheet.getRange("G10:G14").format.numberFormat = "#,##0";
sheet.getRange("L10:R14").format.numberFormat = "0";
sheet.getRange("D18:D32").format.numberFormat = "0";
sheet.getRange("A10:U14").format.verticalAlignment = "top";
sheet.getRange("A18:F32").format.verticalAlignment = "top";
sheet.getRange("A36:C43").format.verticalAlignment = "top";

for (const [col, width] of Object.entries({A: 13, B: 12, C: 20, D: 15, E: 30, F: 14, G: 10, H: 26, I: 40, J: 38, K: 38, L: 11, M: 11, N: 9, O: 12, P: 14, Q: 12, R: 9, S: 48, T: 34, U: 38})) {
  sheet.getRange(`${col}:${col}`).format.columnWidth = width;
}
for (const row of [9, 17, 35]) sheet.getRange(`${row}:${row}`).format.rowHeight = 34;
for (const row of [10, 11, 12, 13, 14]) sheet.getRange(`${row}:${row}`).format.rowHeight = 92;
for (let row = 18; row <= 32; row += 1) sheet.getRange(`${row}:${row}`).format.rowHeight = 44;
for (let row = 36; row <= 43; row += 1) sheet.getRange(`${row}:${row}`).format.rowHeight = 32;
sheet.getRange("45:46").format.rowHeight = 42;
sheet.freezePanes.freezeRows(9);

const actionTable = sheet.tables.add("A9:U14", true, "ActionQueue20260907");
actionTable.style = "TableStyleMedium2";
const watchTable = sheet.tables.add("A17:F32", true, "Watch20260907");
watchTable.style = "TableStyleMedium4";
const exclusionTable = sheet.tables.add("A35:C43", true, "Exclusions20260907");
exclusionTable.style = "TableStyleMedium3";
sheet.getRange("R10:R14").conditionalFormats.add("cellIs", { operator: "greaterThanOrEqual", formula: 75, format: { fill: green, font: { bold: true, color: "#1F1F1F" } } });

workbook.recalculate();
const key = await workbook.inspect({ kind: "table", range: "Run 2026-09-07!A1:U16", include: "values,formulas", tableMaxRows: 16, tableMaxCols: 21 });
console.log(key.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan" });
console.log(errors.ndjson);
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`SAVED ${outputPath}`);
const preview = await workbook.render({ sheetName: "Run 2026-09-07", range: "A1:U16", scale: 1.2, format: "png" });
await fs.writeFile(`${outputDir}/preview.png`, new Uint8Array(await preview.arrayBuffer()));
