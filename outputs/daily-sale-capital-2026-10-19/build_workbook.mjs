import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "file:///C:/Users/Ben/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const root = "C:/Users/Ben/Downloads/Lighttowergroupsite";
const outDir = `${root}/outputs/daily-sale-capital-2026-10-19`;
const prior = `${root}/outputs/daily-sale-capital-2026-10-18/light-tower-multifamily-sale-capital-2026-10-18.xlsx`;
const out = `${outDir}/light-tower-multifamily-sale-capital-2026-10-19.xlsx`;
await fs.mkdir(outDir, { recursive: true });
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(prior));
const ws = wb.worksheets.add("Run 2026-10-19");
ws.showGridLines = false;
const navy = "#17365D", pale = "#EAF3F8", amber = "#FFF2CC", rose = "#FCE4D6";
const body = { name: "Arial", size: 10, color: "#1F1F1F" };
const put = (range, values) => { ws.getRange(range).values = values; };

ws.mergeCells("A1:U1"); put("A1", [["Light Tower Group — $10M+ Multifamily Sale & Capital Opportunity Engine"]]);
ws.getRange("A1").format = { font: { name: "Arial", size: 14, bold: true, color: navy } };
ws.mergeCells("A2:U2"); put("A2", [["Run date: October 19, 2026 | Report-only | Targeted named-MSA public-source coverage; not universal or statewide"]]);
ws.getRange("A2").format = { font: { name: "Arial", size: 10, italic: true, color: "#555555" } };
put("A4:B7", [["Action queue", "6 continuing leads"], ["Priority 85+", "None"], ["Qualified 75–84", "6"], ["New qualified leads", "0"]]);
put("D4:E7", [["Watch 65–74", "18 leads"], ["Excluded", "Retained + new screens"], ["$10M Gate", "Required"], ["Outreach", "Named-lead approval required"]]);
for (const range of ["A4:A7", "D4:D7"]) ws.getRange(range).format = { fill: pale, font: { name: "Arial", size: 10, bold: true, color: navy } };
for (const range of ["B4:B7", "E4:E7"]) ws.getRange(range).format = { fill: "#F9FBFD", font: body };

put("A9:U9", [["Lead ID", "Status", "Classification", "$10M Gate", "Asset / Address", "MSA", "Units", "Owner / Broker", "Observed facts", "Inference", "Counterargument", "Sale process 35", "Capital event 20", "Fit 15", "Execution 10", "Evidence 15", "Contacts 5", "Score", "Sources / dates", "Verified public contact", "Light Tower angle"]]);
const actionRows = [
  ["PHI-011", "Continuing", "Active Sale", 40200000, "1220–1246 N. Broad St. & 1254 N. Carlisle St.", "Philadelphia", 309, "GREA", "Oct. 19 Tier 1 search return from Showcase reports multifamily for sale at $40.2M; LoopNet source record was directly observed active Oct. 18; original listing Aug. 31; 8,130 SF ground-floor commercial.", "Named-broker process supports sale advisory and financing review.", "Verify commercial-income split, five-bedroom leases, restrictions, rent roll, authority, and parcel rights.", 34, 0, 13, 9, 15, 5, null, "Showcase / LoopNet Tier 1 | listed Aug. 31; searched Oct. 19 | https://www.loopnet.com/Listing/1220-N-Broad-St-1254-N-Carlisle-St/41945982/", "Kenneth Wellar, GREA, (215) 454-2879, ken.wellar@grea.com", "Sale advisory; buyer financing; bridge; preferred equity; recapitalization"],
  ["LA-011", "Continuing", "Active Sale", 18000000, "Park.1915, 1915 Park Ave.", "Los Angeles", 36, "Marcus & Millichap", "Tier 1 direct offering observed Oct. 18 identifies the LoopNet multifamily-for-sale listing, OM and 2025 financial attachment; Aug. 17 market date.", "Near-term sale-advisory and acquisition-financing candidate.", "Confirm current exclusive, restrictions, CO, authority, rent roll, and 2025 results.", 34, 0, 15, 10, 15, 5, null, "LoopNet Tier 1 | listed Aug. 17; observed Oct. 18 | https://www.loopnet.com/Listing/1915-Park-Avenue-Los-Angeles-CA/41776924/", "Neema Ahadian, (310) 909-5444; Jeffrey Estrada, (310) 909-5423", "Sale advisory; buyer financing; senior refinance"],
  ["LA-010", "Continuing", "Active Sale", 15950000, "3675 Dunn Dr.", "Los Angeles", 18, "Alex Galuz, KW Commercial", "Tier 1 direct result observed Oct. 18 states the Palms multifamily property is currently available; Aug. 3 market date and $7.65M assumable Chase loan were previously disclosed.", "Availability and loan assumption support financing or recap analysis.", "Confirm current exclusive, authority, covenants, rent roll, debt balance, and transfer terms.", 34, 0, 15, 10, 15, 5, null, "LoopNet Tier 1 | listed Aug. 3; observed Oct. 18 | https://www.loopnet.com/Listing/3675-Dunn-Dr-Los-Angeles-CA/41534752/", "Alex Galuz, KW Commercial, (310) 466-0888", "Sale advisory; buyer financing; senior refinance; recapitalization"],
  ["LA-015", "Continuing", "Active Sale", 11200000, "2912–2924 W. 141st Pl. & 2925 W. Rosecrans Ave.", "Gardena / Los Angeles MSA", 32, "Shield Commercial Real Estate", "Public listing records observed Oct. 18 confirm $11.2M, 32 units, and a 6.61% cap rate; direct Tier 1 record has Aug. 17 date and AB 1482-only disclosure.", "Public marketing supports buyer financing, bridge, or recapitalization.", "Confirm current exclusive, authority, AB 1482 scope, title, rent roll, and renovations.", 34, 0, 15, 10, 15, 5, null, "CityFeet / Showcase; LoopNet Tier 1 | listed Aug. 17; observed Oct. 18 | https://www.loopnet.com/Listing/2912-W-141st-Pl-Gardena-CA/41773238/", "Allen Gholian, Shield Commercial, (310) 593-9868", "Sale advisory; buyer financing; bridge; recapitalization"],
  ["CHI-004", "Continuing", "Active Sale", 12000000, "Washington Plaza, 5501 W. Washington Blvd.", "Chicago", 172, "BAUVISTA", "Oct. 19 Tier 1 LoopNet and CityFeet results show $12M, 172 apartments and investment sale; Crexi also shows an active $12M record with 86 days on market. Prior direct record showed 98% stated occupancy and Jul. 22 market date.", "Buyer financing, bridge, or recapitalization potential.", "Verify subsidy/master-lease exposure, capex, authority, restrictions, and rent roll.", 33, 0, 15, 10, 15, 5, null, "LoopNet / CityFeet Tier 1; Crexi corroboration | listed Jul. 22; searched Oct. 19 | https://www.loopnet.com/Listing/5501-W-Washington-Blvd-Chicago-IL/41395207/", "Brian Mond, (773) 615-2626; George Benitez, (239) 443-0768", "Sale advisory; buyer financing; bridge; recapitalization"],
  ["PHI-009", "Continuing", "Pre-Marketing / Quiet Sale", 141000000, "International City Apartments, 7900 & 8400 Lindbergh Blvd.", "Philadelphia", 1068, "AJH Management; Newmark", "Oct. 19 search returns PBJ, TRD, Bisnow and CRE News reporting AJH is offering the 1,068-unit complex for sale and has hired Newmark; 2019 value was $141M. No public current ask.", "Institutional process supports advisory, financing, preferred equity, recapitalization, or lender dialogue.", "Obtain OM, bid timing, authority, price, restrictions, T-12, and capex plan.", 32, 0, 15, 9, 15, 5, null, "PBJ / TRD / Bisnow / CRE News Tier 2 | Aug. 30–Sep. 4; searched Oct. 19 | https://www.bisnow.com/news/philadelphia/multifamily/largest-apartment-complex-for-sale-international-city", "Carl Fiebig, Newmark, (215) 470-5826, Carl.Fiebig@nmrk.com", "Sale advisory; buyer financing; bridge; preferred equity; recapitalization; lender dialogue"]
];
put("A10:U15", actionRows); ws.getRange("R10").formulas = [["=SUM(L10:Q10)"]]; ws.getRange("R10:R15").fillDown();

ws.mergeCells("A17:F17"); put("A17", [["Watch — 65–74: evidence, process, or product gates still open"]]); ws.getRange("A17").format = { fill: amber, font: { name: "Arial", size: 11, bold: true, color: navy } };
put("A18:F18", [["Lead ID", "Classification", "Asset / MSA", "Score", "Reason held", "Precise next verification step"]]);
const watch = [
  ["NY-002", "Watch", "99 Dumont & 499 Pennsylvania, Brooklyn / NYC", 70, "421-a exemption through 2061; restriction status unresolved.", "Obtain OM, 421-a agreement, unit/rent schedule, restrictions, mandate, and authority."],
  ["FL-010", "Capital Event", "Landmark South, Doral / Miami", 65, "$238M bridge refinance; no sale process or unmet capital need public.", "Confirm maturity, milestones, capital need, authority, and JSB/Torchlight dialogue."],
  ["LA-014", "Watch", "V on Victory, Van Nuys / Los Angeles", 74, "Four of 68 units have unresolved restriction status.", "Obtain OM and recorded covenants; reconcile all units' restrictions."],
  ["CHI-003", "Watch", "4520–26 S. Drexel, Chicago", 74, "Primary foreclosure/receiver evidence absent.", "Obtain Cook County docket, receiver order, complaint, payoff, and current marketing status."],
  ["LA-003", "Watch", "Nabi Apartments, Los Angeles", 72, "CDFI/project history requires covenant and title clearance.", "Check recorded covenant, title, HCD records, and deed restrictions."],
  ["LA-012", "Watch", "The Palms, Torrance / Los Angeles", 72, "Current record is contingent, not active sale.", "Monitor close; verify authority, restrictions, rent roll, and lender catalyst."],
  ["FL-001", "Watch", "Gables Galiano, Coral Gables / Miami", 71, "Extended marketing weakens sale-process evidence.", "Obtain current broker mandate, OM, rent roll, restriction confirmation, and authority."],
  ["FL-006", "Watch", "Genesis Clearwater, Clearwater / Tampa", 71, "Foreclosure reporting lacks primary debt and party linkage.", "Obtain complaint, mortgage/assignment, debt balance, lender/borrower link, and restriction evidence."],
  ["FL-007", "Watch", "650 SW 1st St., Miami", 70, "Ask, product split, and restrictions unresolved.", "Obtain total ask, rent roll, residential-income split, restrictions, and broker."],
  ["PHI-008", "Watch", "220–222 Church, Philadelphia", 70, "Unit count, commercial scope, and mandate inconsistent.", "Obtain OM, lease/rent roll, unit reconciliation, and broker mandate."],
  ["PHI-007", "Watch", "The Maxfield, Philadelphia", 70, "Listing age weakens availability.", "Obtain current exclusive, T-12, rent roll, and seller authority."],
  ["FL-005", "Watch", "The Wave Apartments, Tampa", 69, "Default reporting lacks a primary foreclosure record.", "Obtain complaint, mortgage/assignment, lender/borrower linkage, and restriction evidence."],
  ["FL-003", "Watch", "California Club, Miami", 69, "Current mandate evidence is insufficiently recent.", "Obtain current listing agreement, units/price, rent roll, and restriction check."],
  ["LA-007", "Watch", "The Jeffries, Los Angeles", 69, "Availability and regulatory status lack corroboration.", "Obtain live mandate, RSO/affordability clearance, price, and rent roll."],
  ["NY-001", "Watch", "30-unit portfolio, NYC", 68, "Stabilization status and sale process unclear.", "Obtain HPD/DHCR records, current OM, addresses, price, and broker authority."],
  ["LA-008", "Watch", "The Cooper, Los Angeles", 68, "Listing needs RSO determination.", "Verify HCIDLA RSO status, title/covenants, and current broker mandate."],
  ["LA-009", "Watch", "1400 Venice Blvd., Los Angeles", 68, "Ask lacks dated current listing record.", "Obtain dated exclusive/MLS, authority, RSO/covenant status, and rent roll."],
  ["LA-013", "Watch", "Park Terrace Apartments, Los Angeles", 68, "Aged mandate and regulatory evidence unresolved.", "Obtain current mandate, CO, RSO determination, title/covenants, and rent roll."]
];
put("A19:F36", watch);

ws.mergeCells("A38:C38"); put("A38", [["Excluded and coverage gaps"]]); ws.getRange("A38").format = { fill: rose, font: { name: "Arial", size: 11, bold: true, color: navy } };
put("A39:C39", [["Item", "Classification", "Exclusion / coverage finding"]]);
put("A40:C47", [
  ["Oct. 19 public-source screen", "No promotion", "No fresh targeted result cleared price/debt, conventional product, regulatory, recency, and evidence gates."],
  ["New Florida / North Carolina / NYC results", "Excluded / held", "Discovery results were generic, below gate, closed, or lacked price, product, restriction, and current-process evidence."],
  ["Los Angeles / Chicago / Philadelphia new screens", "Held", "New discovery records lacked a verified $10M ask/debt or clear conventional-rental and regulatory evidence."],
  ["Closed / no-catalyst records", "Excluded", "Completed refinancing, sales, and acquisitions remain out absent a current process or unmet capital need."],
  ["Retained exclusions", "Excluded", "Rent-stabilized/restricted/affordable, student, development, materially mixed-use, hospitality, and scattered-small-residential records remain outside the primary queue."],
  ["Direct-page retrieval", "Evidence limitation", "Live direct-page scrape requests were approval-gated; Oct. 19 source search observations and Oct. 18 direct observations are distinguished above."],
  ["Delivery", "Limited", "No connected Sheets session or authenticated email connector. Historical $20M tabs untouched; no email sent."],
  ["Coverage limitation", "Not universal", "Targeted public-source sweep only across named MSAs; never statewide Florida or North Carolina coverage."]
]);

for (const range of ["A9:U9", "A18:F18", "A39:C39"]) ws.getRange(range).format = { fill: navy, font: { name: "Arial", size: 9, bold: true, color: "#FFFFFF" }, wrapText: true, horizontalAlignment: "center", verticalAlignment: "center" };
for (const range of ["A10:U15", "A19:F36", "A40:C47"]) { ws.getRange(range).format.font = body; ws.getRange(range).format.wrapText = true; ws.getRange(range).format.verticalAlignment = "top"; }
ws.getRange("D10:D15").format.numberFormat = '"$"#,##0'; ws.getRange("G10:G15").format.numberFormat = "#,##0"; ws.getRange("L10:R15").format.numberFormat = "0";
for (const [col, width] of Object.entries({ A: 13, B: 13, C: 20, D: 15, E: 33, F: 18, G: 10, H: 27, I: 44, J: 35, K: 39, L: 11, M: 11, N: 9, O: 12, P: 12, Q: 12, R: 9, S: 46, T: 39, U: 39 })) ws.getRange(`${col}:${col}`).format.columnWidth = width;
for (const row of [9, 18, 39]) ws.getRange(`${row}:${row}`).format.rowHeight = 40;
for (let row = 10; row <= 15; row++) ws.getRange(`${row}:${row}`).format.rowHeight = 122;
for (let row = 19; row <= 36; row++) ws.getRange(`${row}:${row}`).format.rowHeight = 52;
for (let row = 40; row <= 47; row++) ws.getRange(`${row}:${row}`).format.rowHeight = 48;
ws.freezePanes.freezeRows(9);
ws.tables.add("A9:U15", true, "ActionQueue20261019").style = "TableStyleMedium2";
ws.tables.add("A18:F36", true, "Watch20261019").style = "TableStyleMedium4";
ws.tables.add("A39:C47", true, "Exclusions20261019").style = "TableStyleMedium3";

wb.recalculate();
console.log((await wb.inspect({ kind: "table", range: "Run 2026-10-19!A1:U15", include: "values,formulas", tableMaxRows: 16, tableMaxCols: 21 })).ndjson);
console.log((await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 300 }, summary: "formula error scan" })).ndjson);
const xlsx = await SpreadsheetFile.exportXlsx(wb); await xlsx.save(out);
const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(out));
console.log((await reopened.inspect({ kind: "table", range: "Run 2026-10-19!A9:U15", include: "values,formulas", tableMaxRows: 7, tableMaxCols: 21 })).ndjson);
try { const png = await wb.render({ sheetName: "Run 2026-10-19", range: "A1:U15", scale: 1, format: "png" }); await fs.writeFile(`${outDir}/preview.png`, new Uint8Array(await png.arrayBuffer())); console.log("PREVIEW SAVED"); } catch (error) { console.log(`PREVIEW UNAVAILABLE: ${error.message}`); }
