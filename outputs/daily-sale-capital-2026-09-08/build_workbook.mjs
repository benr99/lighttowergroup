import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = "C:/Users/Ben/Downloads/Lighttowergroupsite";
const prior = `${root}/outputs/daily-sale-capital-2026-09-07/light-tower-multifamily-sale-capital-2026-09-07.xlsx`;
const outputDir = `${root}/outputs/daily-sale-capital-2026-09-08`;
const outputPath = `${outputDir}/light-tower-multifamily-sale-capital-2026-09-08.xlsx`;
await fs.mkdir(outputDir, { recursive: true });

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(prior));
const sheet = workbook.worksheets.add("Run 2026-09-08");
sheet.showGridLines = false;

const navy = "#17365D";
const paleBlue = "#EAF3F8";
const amber = "#FFF2CC";
const rose = "#FCE4D6";
const green = "#E2F0D9";
const text = { name: "Arial", size: 10, color: "#1F1F1F" };

sheet.getRange("A1:U1").merge();
sheet.getRange("A1").values = [["Light Tower Group — $10M+ Multifamily Sale & Capital Opportunity Engine"]];
sheet.getRange("A1").format = { font: { name: "Arial", size: 14, bold: true, color: navy } };
sheet.getRange("A2:U2").merge();
sheet.getRange("A2").values = [["Run date: September 8, 2026 | Report-only | Targeted public-source coverage; not universal MSA or statewide coverage"]];
sheet.getRange("A2").format = { font: { name: "Arial", size: 10, italic: true, color: "#555555" } };
sheet.getRange("A4:B7").values = [["Action queue", "7 leads"], ["Priority 85+", "None"], ["Qualified 75–84", "7"], ["New qualified leads", "2"]];
sheet.getRange("D4:E7").values = [["Watch 65–74", "14 leads"], ["Excluded", "6 categories"], ["$10M Gate", "Required"], ["Outreach", "Named-lead approval required"]];
for (const r of ["A4:A7", "D4:D7"]) sheet.getRange(r).format = { fill: paleBlue, font: { name: "Arial", size: 10, bold: true, color: navy } };
for (const r of ["B4:B7", "E4:E7"]) sheet.getRange(r).format = { fill: "#F9FBFD", font: text };

const actionHeaders = [["Lead ID", "Status", "Classification", "$10M Gate", "Asset / Address", "MSA", "Units", "Owner / Sponsor / Lender / Broker", "Observed facts", "Inference", "Counterargument", "Sale process 35", "Capital event 20", "Fit 15", "Execution 10", "Evidence / recency 15", "Public contacts 5", "Score", "Sources / dates", "Verified public contact", "Light Tower angle"]];
sheet.getRange("A9:U9").values = actionHeaders;
const actions = [
  ["LA-014", "New", "Active Sale", 22900000, "V on Victory, 13724 Victory Blvd.", "Los Angeles", 68, "Marcus & Millichap", "Tier 1 live listing, Sep. 2 market date; 2022 construction, 97% occupancy, 5.50% cap rate, apartments.", "Fresh sale process supports advisory and acquisition financing.", "Confirm seller authority, rent roll, title/covenants, and revenue assumptions.", 34, 0, 15, 10, 15, 5, null, "LoopNet | market date Sep. 2 | current Sep. 8 | https://www.loopnet.com/Listing/13724-Victory-Blvd-Van-Nuys-CA/42019684/", "Glen Scher; Filip Niculete; Tony Dang, Marcus & Millichap; (818) 667-6683", "Sale advisory; buyer financing; senior refinance; recapitalization"],
  ["LA-015", "New", "Active Sale", 11200000, "2912–2924 W. 141st Pl. & 2925 W. Rosecrans Ave.", "Los Angeles", 32, "Shield Commercial Real Estate", "Tier 1 live listing, Aug. 17 market date; 32-unit garden portfolio; 2025 actual NOI $721,330; listing says AB 1482 only.", "Dated marketing and operating data support buyer financing or bridge/recap dialogue.", "Verify seller authority, statutory rent-control applicability, title, rent roll, and renovations.", 34, 0, 15, 10, 15, 5, null, "LoopNet | market date Aug. 17 | current Sep. 8 | https://www.loopnet.com/Listing/2912-W-141st-Pl-Gardena-CA/41773238/", "Jonathan Nikfarjam; Allen Gholian, Shield Commercial; (310) 593-9868", "Sale advisory; buyer financing; bridge; recapitalization"],
  ["LA-011", "Continuing", "Active Sale", 18000000, "Park.1915, 1915 Park Ave.", "Los Angeles", 36, "Marcus & Millichap", "Exclusive broker page remains live for a 2025-built, 36-unit apartment asset.", "Near-term sale advisory and acquisition-financing conversation.", "Confirm restrictions, CO, seller authority, rent roll, and actual 2025 results.", 34, 0, 15, 10, 15, 5, null, "Marcus & Millichap | current Sep. 8 | https://www.marcusmillichap.com/properties/304677/park1915", "Neema Ahadian (310) 909-5444; Jeffrey Estrada (310) 909-5423", "Sale advisory; buyer financing; senior refinance"],
  ["LA-010", "Continuing", "Active Sale", 15950000, "3675 Dunn Dr.", "Los Angeles", 18, "Alex Galuz, KW Commercial", "Tier 1 listing remains live for a 2019-built Class A, 18-unit apartment asset.", "Buyer financing and recapitalization potential.", "Confirm seller authority, affordability covenant, current rent roll, and actual debt.", 34, 0, 15, 10, 15, 5, null, "LoopNet | listed Aug. 3 | current Sep. 8 | https://www.loopnet.com/Listing/3675-Dunn-Dr-Los-Angeles-CA/41534752/", "Alex Galuz (310) 466-0888", "Sale advisory; buyer financing; senior refinance; recapitalization"],
  ["CHI-004", "Continuing", "Active Sale", 12000000, "Washington Plaza, 5501 W. Washington Blvd.", "Chicago", 172, "33 Realty", "Tier 1 listing remains live at $12M; 172 units, 98% occupancy, apartment subtype.", "Buyer financing, bridge, or recapitalization potential.", "Confirm subsidy contracts, deferred maintenance, seller authority, rent roll, and capex plan.", 33, 0, 15, 10, 15, 5, null, "LoopNet | listed Jul. 22 | current Sep. 8 | https://www.loopnet.com/Listing/5501-W-Washington-Blvd-Chicago-IL/41395207/", "Brian Mond (773) 615-2626; George Benitez (239) 443-0768", "Sale advisory; buyer financing; bridge; recapitalization"],
  ["LA-012", "Continuing", "Active Sale", 14950000, "The Palms, 3929 W. 242nd St.", "Los Angeles", 48, "Marcus & Millichap", "Exclusive broker page remains live; MLS data has Aug. 17 list date and Aug. 24 reduction to $14.95M.", "Dated exclusive marketing supports buyer financing and value-add capital planning.", "Verify local rent-control status, seller authority, rent roll, capex plan, and restrictions.", 32, 0, 15, 10, 15, 5, null, "Marcus & Millichap + Redfin | current Sep. 8 | https://www.marcusmillichap.com/properties/308515/the-palms", "Tyler Leeson (714) 713-9086", "Sale advisory; buyer financing; bridge; preferred equity"],
  ["PHI-009", "Continuing", "Pre-Marketing / Quiet Sale", 141000000, "International City Apartments, 7900 & 8400 Lindbergh Blvd.", "Philadelphia", 1068, "AJH Management; Newmark", "Two current Tier 2 reports identify a Newmark-led sale process for a 44-acre, 64-building apartment complex.", "Institutional process may need advisory, buyer financing, preferred equity, recapitalization, or lender dialogue.", "Obtain OM, bid timing, seller authority, current pricing, restrictions, T-12, and capex plan.", 32, 0, 15, 9, 15, 5, null, "Bisnow Aug. 31 + Hoodline Sep. 1 | https://www.bisnow.com/news/philadelphia/multifamily/largest-apartment-complex-for-sale-international-city", "Carl Fiebig (215) 470-5826, Carl.Fiebig@nmrk.com; Erin Miller, Newmark", "Sale advisory; buyer financing; bridge; preferred equity; recapitalization; lender dialogue"],
];
sheet.getRange("A10:U16").values = actions;
sheet.getRange("R10").formulas = [["=SUM(L10:Q10)"]];
sheet.getRange("R10:R16").fillDown();

sheet.getRange("A18:F18").merge();
sheet.getRange("A18").values = [["Watch — 65–74: evidence or product gates still open"]];
sheet.getRange("A18").format = { fill: amber, font: { name: "Arial", size: 11, bold: true, color: navy } };
sheet.getRange("A19:F19").values = [["Lead ID", "Classification", "Asset / MSA", "Score", "Reason held", "Precise next verification step"]];
const watch = [
  ["CHI-003", "Watch", "4520–26 S. Drexel, Chicago", 74, "Secondary foreclosure reporting is not a current primary record.", "Obtain Cook County docket, receiver order, complaint, payoff, and current marketing status."],
  ["LA-003", "Watch", "Nabi Apartments, Los Angeles", 72, "Historical CDFI/project evidence requires regulatory clearance.", "Check recorded affordability covenant, title, HCD records, and deed restrictions."],
  ["FL-001", "Watch", "Gables Galiano, Coral Gables / Miami", 71, "Extended marketing weakens current sale-process evidence.", "Obtain current broker mandate, OM, rent roll, restrictions confirmation, and seller authority."],
  ["FL-006", "Watch", "Genesis Clearwater, Clearwater / Tampa", 71, "Foreclosure reporting lacks primary debt and party linkage.", "Obtain Pinellas complaint, mortgage/assignment, debt balance, lender/borrower link, and restrictions."],
  ["FL-007", "Watch", "650 SW 1st St., Miami", 70, "21 apartments plus retail and no explicit total ask.", "Obtain signed mandate with total ask, residential-income split, rent roll, restrictions, and broker."],
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
sheet.getRange("A20:F33").values = watch;

sheet.getRange("A35:C35").merge();
sheet.getRange("A35").values = [["Excluded and coverage gaps"]];
sheet.getRange("A35").format = { fill: rose, font: { name: "Arial", size: 11, bold: true, color: navy } };
sheet.getRange("A36:C36").values = [["Item", "Classification", "Exclusion reason"]];
sheet.getRange("A37:C42").values = [
  ["Avondale Apartments, Philadelphia", "Excluded", "Current source identifies income restrictions and eligibility requirements; outside primary unrestricted queue."],
  ["727 Collins Ave., Miami Beach", "Excluded", "Hospitality master lease and 4,800-SF retail footprint make it materially mixed hospitality/retail."],
  ["1020 SW 2nd St., Miami", "Excluded", "About $6.5M implied price, below $10M gate."],
  ["2629 NW 17th Ave., Miami", "Excluded", "Covered-land/high-density Live Local/workforce-housing development play."],
  ["2328–2344 N. 2nd St., Philadelphia", "Excluded", "Apartments bundled with retail suites and townhome-approved parcels."],
  ["Prior student, RSO/affordable, TOC/HCA, mixed-use, and dormitory exclusions", "Excluded", "Remain outside primary queue pending clearing evidence or authorized mandate change."],
];

sheet.getRange("A44:U44").merge();
sheet.getRange("A44").values = [["Coverage limitation: targeted public-source sweep only. Named MSAs were screened; absence of a lead is not evidence that no opportunity exists. No outreach was drafted, queued, scheduled, implied, or sent."]];
sheet.getRange("A45:U45").merge();
sheet.getRange("A45").values = [["Google Drive/Sheets connector unavailable: established Google Sheet and historical $20M tabs left untouched. No email was sent; email sending requires action-time confirmation."]];
for (const r of ["A44", "A45"]) sheet.getRange(r).format = { fill: paleBlue, font: { name: "Arial", size: 10, italic: true, color: "#555555" }, wrapText: true, verticalAlignment: "center" };

for (const r of ["A9:U9", "A19:F19", "A36:C36"]) sheet.getRange(r).format = { fill: navy, font: { name: "Arial", size: 9, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
for (const r of ["A10:U16", "A20:F33", "A37:C42"]) { sheet.getRange(r).format.font = text; sheet.getRange(r).format.wrapText = true; sheet.getRange(r).format.verticalAlignment = "top"; }
sheet.getRange("D10:D16").format.numberFormat = '"$"#,##0';
sheet.getRange("G10:G16").format.numberFormat = "#,##0";
sheet.getRange("L10:R16").format.numberFormat = "0";
sheet.getRange("D20:D33").format.numberFormat = "0";
for (const [col, width] of Object.entries({ A: 13, B: 12, C: 20, D: 15, E: 30, F: 14, G: 10, H: 26, I: 39, J: 35, K: 36, L: 11, M: 11, N: 9, O: 12, P: 14, Q: 12, R: 9, S: 45, T: 34, U: 36 })) sheet.getRange(`${col}:${col}`).format.columnWidth = width;
for (const row of [9, 19, 36]) sheet.getRange(`${row}:${row}`).format.rowHeight = 36;
for (let row = 10; row <= 16; row += 1) sheet.getRange(`${row}:${row}`).format.rowHeight = 94;
for (let row = 20; row <= 33; row += 1) sheet.getRange(`${row}:${row}`).format.rowHeight = 44;
for (let row = 37; row <= 42; row += 1) sheet.getRange(`${row}:${row}`).format.rowHeight = 36;
sheet.getRange("44:45").format.rowHeight = 42;
sheet.freezePanes.freezeRows(9);
sheet.tables.add("A9:U16", true, "ActionQueue20260908").style = "TableStyleMedium2";
sheet.tables.add("A19:F33", true, "Watch20260908").style = "TableStyleMedium4";
sheet.tables.add("A36:C42", true, "Exclusions20260908").style = "TableStyleMedium3";
sheet.getRange("R10:R16").conditionalFormats.add("cellIs", { operator: "greaterThanOrEqual", formula: 75, format: { fill: green, font: { bold: true, color: "#1F1F1F" } } });

workbook.recalculate();
const key = await workbook.inspect({ kind: "table", range: "Run 2026-09-08!A1:U16", include: "values,formulas", tableMaxRows: 18, tableMaxCols: 21 });
console.log(key.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan" });
console.log(errors.ndjson);
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`SAVED ${outputPath}`);
const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const savedCheck = await reopened.inspect({ kind: "table", range: "Run 2026-09-08!A9:R16", include: "values,formulas", tableMaxRows: 8, tableMaxCols: 18 });
console.log(savedCheck.ndjson);
try {
  const preview = await workbook.render({ sheetName: "Run 2026-09-08", range: "A1:U16", scale: 1, format: "png" });
  await fs.writeFile(`${outputDir}/preview.png`, new Uint8Array(await preview.arrayBuffer()));
  console.log("PREVIEW SAVED");
} catch (error) {
  console.log(`PREVIEW UNAVAILABLE: ${error.message}`);
}
