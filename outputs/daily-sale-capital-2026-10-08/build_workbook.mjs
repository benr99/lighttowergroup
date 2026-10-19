import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "file:///C:/Users/Ben/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const root = "C:/Users/Ben/Downloads/Lighttowergroupsite";
const outputDir = `${root}/outputs/daily-sale-capital-2026-10-08`;
const outputPath = `${outputDir}/light-tower-multifamily-sale-capital-2026-10-08.xlsx`;
const priorPath = `${root}/outputs/daily-sale-capital-2026-10-07/light-tower-multifamily-sale-capital-2026-10-07.xlsx`;
await fs.mkdir(outputDir, { recursive: true });

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(priorPath));
const sheet = workbook.worksheets.add("Run 2026-10-08");
sheet.showGridLines = false;
const navy = "#17365D", pale = "#EAF3F8", amber = "#FFF2CC", rose = "#FCE4D6";
const bodyFont = { name: "Arial", size: 10, color: "#1F1F1F" };

sheet.mergeCells("A1:U1");
sheet.getRange("A1").values = [["Light Tower Group — $10M+ Multifamily Sale & Capital Opportunity Engine"]];
sheet.getRange("A1").format = { font: { name: "Arial", size: 14, bold: true, color: navy } };
sheet.mergeCells("A2:U2");
sheet.getRange("A2").values = [["Run date: October 8, 2026 | Report-only | Targeted public-source coverage; not universal MSA or statewide coverage"]];
sheet.getRange("A2").format = { font: { name: "Arial", size: 10, italic: true, color: "#555555" } };

sheet.getRange("A4:B7").values = [["Action queue", "6 leads"], ["Priority 85+", "None"], ["Qualified 75–84", "6"], ["New qualified leads", "1"]];
sheet.getRange("D4:E7").values = [["Watch 65–74", "17 leads"], ["Excluded", "11 items/categories"], ["$10M Gate", "Required"], ["Outreach", "Named-lead approval required"]];
for (const range of ["A4:A7", "D4:D7"]) sheet.getRange(range).format = { fill: pale, font: { name: "Arial", size: 10, bold: true, color: navy } };
for (const range of ["B4:B7", "E4:E7"]) sheet.getRange(range).format = { fill: "#F9FBFD", font: bodyFont };

const headers = [["Lead ID", "Status", "Classification", "$10M Gate", "Asset / Address", "MSA", "Units", "Owner / Broker", "Observed facts", "Inference", "Counterargument", "Sale process 35", "Capital event 20", "Fit 15", "Execution 10", "Evidence 15", "Contacts 5", "Score", "Sources / dates", "Verified public contact", "Light Tower angle"]];
sheet.getRange("A9:U9").values = headers;
const actions = [
  ["PHI-011", "New", "Active Sale", 40200000, "Apartments at 1220 and 1254, 1220–1246 N. Broad St. & 1254 N. Carlisle St.", "Philadelphia", 309, "GREA", "Tier 1 active direct offering: $40.2M, 309 apartments, 8,130 SF ground-floor commercial space, 95% / 89% occupancy, listed Aug. 31.", "Current named-broker sale process supports sale advisory, buyer financing, bridge, preferred equity, or recapitalization review.", "Confirm commercial-income split, 5-bedroom lease structure, rent roll, seller authority, restrictions, and adjacent-parcel rights.", 34, 0, 13, 9, 15, 5, null, "LoopNet | listed Aug. 31; observed Oct. 8 | https://www.loopnet.com/Listing/1220-N-Broad-St-1254-N-Carlisle-St/41945982/", "Ken Wellar, GREA, (215) 454-2879, ken.wellar@grea.com", "Sale advisory; buyer financing; bridge; preferred equity; recapitalization"],
  ["LA-011", "Continuing", "Active Sale", 18000000, "Park.1915, 1915 Park Ave.", "Los Angeles", 36, "Marcus & Millichap", "Tier 1 exclusive is live: 2025-built, 36-unit conventional apartment asset at $18.0M.", "Near-term sale-advisory and acquisition-financing opportunity.", "Confirm restrictions, CO, seller authority, rent roll, and 2025 results.", 34, 0, 15, 10, 15, 5, null, "Marcus & Millichap | observed Oct. 8 | https://www.marcusmillichap.com/properties/304677/park1915", "Neema Ahadian (310) 909-5444; Jeffrey Estrada (310) 909-5423; Dan Litman (310) 909-2319", "Sale advisory; buyer financing; senior refinance"],
  ["LA-010", "Continuing", "Active Sale", 15950000, "3675 Dunn Dr.", "Los Angeles", 18, "Alex Galuz, KW Commercial", "Tier 1 listing is currently available; $15.95M ask and Aug. 3 market date.", "Sale process and disclosed loan-assumption feature support financing or recap analysis.", "Confirm seller authority, covenant status, rent roll, loan-transfer terms, and debt.", 34, 0, 15, 10, 15, 5, null, "LoopNet | Aug. 3 market date; observed Oct. 8 | https://www.loopnet.com/Listing/3675-Dunn-Dr-Los-Angeles-CA/41534752/", "Alex Galuz, KW Commercial, (310) 466-0888", "Sale advisory; buyer financing; senior refinance; recapitalization"],
  ["LA-015", "Continuing", "Active Sale", 11200000, "2912–2924 W. 141st Pl. & 2925 W. Rosecrans Ave.", "Los Angeles", 32, "Shield Commercial Real Estate", "Tier 1 listing is currently available; $11.2M, 32 units, 6.44% current cap rate, Aug. 17 market date, AB 1482-only disclosure.", "Dated marketing and operating data support buyer financing or bridge/recap analysis.", "Confirm seller authority, AB 1482 applicability, title, rent roll, and renovations.", 34, 0, 15, 10, 15, 5, null, "LoopNet | Aug. 17 market date; observed Oct. 8 | https://www.loopnet.com/Listing/2912-W-141st-Pl-Gardena-CA/41773238/", "Jonathan Nikfarjam; Allen Gholian, Shield Commercial, (310) 593-9868", "Sale advisory; buyer financing; bridge; recapitalization"],
  ["CHI-004", "Continuing", "Active Sale", 12000000, "Washington Plaza, 5501 W. Washington Blvd.", "Chicago", 172, "33 Realty", "Tier 1 listing is currently available at $12M; 172 units, 98% occupancy, apartment subtype, Jul. 22 market date.", "Buyer financing, bridge, or recapitalization potential.", "Confirm subsidy contracts, deferred maintenance, seller authority, rent roll, and capex plan.", 33, 0, 15, 10, 15, 5, null, "LoopNet | Jul. 22 market date; observed Oct. 8 | https://www.loopnet.com/Listing/5501-W-Washington-Blvd-Chicago-IL/41395207/", "Brian Mond (773) 615-2626; George Benitez (239) 443-0768", "Sale advisory; buyer financing; bridge; recapitalization"],
  ["PHI-009", "Continuing", "Pre-Marketing / Quiet Sale", 141000000, "International City Apartments, 7900 & 8400 Lindbergh Blvd.", "Philadelphia", 1068, "AJH Management; Newmark", "Two independent Tier 2 reports support AJH's sale process and Newmark's marketing of the 44-acre, 64-building value-add asset. Verified 2019 sale value: $141M.", "Institutional process may support sale advisory, financing, preferred equity, recapitalization, or lender dialogue.", "Obtain OM, bid timing, authority, price, restrictions, T-12, and capex plan.", 32, 0, 15, 9, 15, 5, null, "Bisnow Aug. 31; CRE Direct Sep. 1 | observed Oct. 8 | https://www.bisnow.com/news/philadelphia/multifamily/largest-apartment-complex-for-sale-international-city", "Carl Fiebig (215) 470-5826, Carl.Fiebig@nmrk.com; Erin Miller, Newmark", "Sale advisory; buyer financing; bridge; preferred equity; recapitalization; lender dialogue"]
];
sheet.getRange("A10:U15").values = actions;
sheet.getRange("R10").formulas = [["=SUM(L10:Q10)"]];
sheet.getRange("R10:R15").fillDown();

sheet.mergeCells("A17:F17");
sheet.getRange("A17").values = [["Watch — 65–74: evidence or product gates still open"]];
sheet.getRange("A17").format = { fill: amber, font: { name: "Arial", size: 11, bold: true, color: navy } };
sheet.getRange("A18:F18").values = [["Lead ID", "Classification", "Asset / MSA", "Score", "Reason held", "Precise next verification step"]];
const watch = [
  ["FL-010", "Capital Event", "Landmark South, Doral / Miami", 65, "$238M bridge refinance closed Sep. 28; no public sale process or documented unmet capital need.", "Confirm bridge term, extension/maturity, business-plan milestones, capital need, authority, and JSB/Torchlight dialogue."],
  ["LA-014", "Watch", "V on Victory, Van Nuys / Los Angeles", 74, "Four of 68 units have unexplained restriction status.", "Obtain OM and recorded covenants; reconcile all units’ rent-control, income-restriction, and affordability status."],
  ["CHI-003", "Watch", "4520–26 S. Drexel, Chicago", 74, "Current primary foreclosure/receiver evidence is absent.", "Obtain Cook County docket, receiver order, complaint, payoff, and current marketing status."],
  ["LA-003", "Watch", "Nabi Apartments, Los Angeles", 72, "Historical CDFI/project evidence requires covenant and title clearance.", "Check recorded affordability covenant, title, HCD records, and deed restrictions."],
  ["LA-012", "Watch", "The Palms, Torrance / Los Angeles", 72, "Current record shows contingent, not active sale.", "Monitor close status and verify seller authority, restrictions, rent roll, and financing/lender catalyst."],
  ["FL-001", "Watch", "Gables Galiano, Coral Gables / Miami", 71, "Extended marketing weakens current sale-process evidence.", "Obtain current broker mandate, OM, rent roll, restriction confirmation, and seller authority."],
  ["FL-006", "Watch", "Genesis Clearwater, Clearwater / Tampa", 71, "Foreclosure reporting lacks primary debt and party linkage.", "Obtain complaint, mortgage/assignment, debt balance, lender/borrower link, and restriction evidence."],
  ["FL-007", "Watch", "650 SW 1st St., Miami", 70, "Total ask, product split, and restrictions remain unresolved.", "Obtain total ask, rent roll, residential-income split, restrictions, and named broker."],
  ["PHI-008", "Watch", "220–222 Church, Philadelphia", 70, "Unit count, commercial scope, and mandate remain inconsistent.", "Obtain OM, lease/rent roll, 40-versus-45-unit reconciliation, and broker mandate."],
  ["PHI-007", "Watch", "The Maxfield, Philadelphia", 70, "Listing age weakens current availability.", "Obtain current exclusive, T-12, rent roll, and seller-authority confirmation."],
  ["FL-005", "Watch", "The Wave Apartments, Tampa", 69, "Default reporting lacks a primary foreclosure record.", "Obtain complaint, mortgage/assignment, lender/borrower linkage, and restriction evidence."],
  ["FL-003", "Watch", "California Club, Miami", 69, "Current mandate evidence is insufficiently recent.", "Obtain current listing agreement, units/price confirmation, rent roll, and restriction check."],
  ["LA-007", "Watch", "The Jeffries, Los Angeles", 69, "Current availability and regulatory status lack corroboration.", "Obtain live broker mandate, RSO/affordability clearance, price, and rent roll."],
  ["NY-001", "Watch", "30-unit portfolio, NYC", 68, "Stabilization status and current sale process are unclear.", "Obtain HPD/DHCR records, current OM, address list, price, and broker authority."],
  ["LA-008", "Watch", "The Cooper, Los Angeles", 68, "Current listing needs RSO determination.", "Verify HCIDLA RSO status, title/covenants, and current broker mandate."],
  ["LA-009", "Watch", "1400 Venice Blvd., Los Angeles", 68, "Ask lacks a dated current listing record.", "Obtain dated exclusive/MLS, seller authority, RSO/covenant status, and rent roll."],
  ["LA-013", "Watch", "Park Terrace Apartments, Los Angeles", 68, "Aged mandate and occupancy/regulatory evidence remain unresolved.", "Obtain current mandate, CO, RSO determination, title/covenants, and rent roll."]
];
sheet.getRange("A19:F35").values = watch;

sheet.mergeCells("A37:C37");
sheet.getRange("A37").values = [["Excluded and coverage gaps"]];
sheet.getRange("A37").format = { fill: rose, font: { name: "Arial", size: 11, bold: true, color: navy } };
sheet.getRange("A38:C38").values = [["Item", "Classification", "Exclusion reason"]];
const exclusions = [
  ["Reside on Jackson, Chicago", "Excluded", "$24.7M five-year permanent Fannie refinance is closed; no public sale process or unresolved financing catalyst."],
  ["Verso Luxury, Davenport / Orlando MSA", "Excluded", "$57M acquisition and $40.5M loan are closed; no current sale process or capital need verified."],
  ["The Marling at Town Creek, Leland / Wilmington MSA", "Excluded", "$57.7M acquisition closed; no current sale process verified."],
  ["Blue Station, Blue Island / Chicago MSA", "Excluded", "$22M sale closed."],
  ["Belle on Bev, Los Angeles", "Excluded", "Completed recapitalization; materially mixed retail, entertainment, and bar uses."],
  ["836–838 N. Broad, Philadelphia", "Excluded", "PHA-supported income and commercial component require regulatory and residential-income treatment confirmation."],
  ["Avondale Apartments, Philadelphia", "Excluded", "Income-restricted; outside primary queue."],
  ["727 Collins Ave., Miami Beach", "Excluded", "Hospitality master lease plus retail footprint makes it materially mixed."],
  ["1020 SW 2nd St., Miami", "Excluded", "About $6.5M implied price, below $10M gate."],
  ["2629 NW 17th Ave., Miami", "Excluded", "Live Local/workforce-housing development play."],
  ["Prior student, RSO/affordable, TOC/HCA, mixed-use, and dormitory exclusions", "Excluded", "Remain out pending clearing evidence or authorized mandate change."]
];
sheet.getRange("A39:C49").values = exclusions;

for (const range of ["A9:U9", "A18:F18", "A38:C38"]) sheet.getRange(range).format = { fill: navy, font: { name: "Arial", size: 9, bold: true, color: "#FFFFFF" }, wrapText: true, horizontalAlignment: "center", verticalAlignment: "center" };
for (const range of ["A10:U15", "A19:F35", "A39:C49"]) { sheet.getRange(range).format.font = bodyFont; sheet.getRange(range).format.wrapText = true; sheet.getRange(range).format.verticalAlignment = "top"; }
sheet.getRange("D10:D15").format.numberFormat = '"$"#,##0';
sheet.getRange("G10:G15").format.numberFormat = "#,##0";
sheet.getRange("L10:R15").format.numberFormat = "0";
for (const [col, width] of Object.entries({ A: 13, B: 13, C: 20, D: 15, E: 33, F: 14, G: 10, H: 27, I: 42, J: 35, K: 39, L: 11, M: 11, N: 9, O: 12, P: 12, Q: 12, R: 9, S: 46, T: 39, U: 39 })) sheet.getRange(`${col}:${col}`).format.columnWidth = width;
for (const row of [9, 18, 38]) sheet.getRange(`${row}:${row}`).format.rowHeight = 40;
for (let row = 10; row <= 15; row++) sheet.getRange(`${row}:${row}`).format.rowHeight = 100;
for (let row = 19; row <= 35; row++) sheet.getRange(`${row}:${row}`).format.rowHeight = 46;
for (let row = 39; row <= 49; row++) sheet.getRange(`${row}:${row}`).format.rowHeight = 38;
sheet.freezePanes.freezeRows(9);
sheet.tables.add("A9:U15", true, "ActionQueue20261008").style = "TableStyleMedium2";
sheet.tables.add("A18:F35", true, "Watch20261008").style = "TableStyleMedium4";
sheet.tables.add("A38:C49", true, "Exclusions20261008").style = "TableStyleMedium3";

workbook.recalculate();
console.log((await workbook.inspect({ kind: "table", range: "Run 2026-10-08!A1:U15", include: "values,formulas", tableMaxRows: 16, tableMaxCols: 21 })).ndjson);
console.log((await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 300 }, summary: "formula error scan" })).ndjson);
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`SAVED ${outputPath}`);
const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
console.log((await reopened.inspect({ kind: "table", range: "Run 2026-10-08!A9:U15", include: "values,formulas", tableMaxRows: 7, tableMaxCols: 21 })).ndjson);
try {
  const preview = await workbook.render({ sheetName: "Run 2026-10-08", range: "A1:U15", scale: 1, format: "png" });
  await fs.writeFile(`${outputDir}/preview.png`, new Uint8Array(await preview.arrayBuffer()));
  console.log("PREVIEW SAVED");
} catch (error) {
  console.log(`PREVIEW UNAVAILABLE: ${error.message}`);
}
