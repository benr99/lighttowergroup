import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "file:///C:/Users/Ben/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const root = "C:/Users/Ben/Downloads/Lighttowergroupsite";
const outDir = `${root}/outputs/daily-sale-capital-2026-10-14`;
const outPath = `${outDir}/light-tower-multifamily-sale-capital-2026-10-14.xlsx`;
const prior = `${root}/outputs/daily-sale-capital-2026-10-13/light-tower-multifamily-sale-capital-2026-10-13.xlsx`;
await fs.mkdir(outDir, { recursive: true });
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(prior));
const ws = wb.worksheets.add("Run 2026-10-14");
ws.showGridLines = false;
const navy = "#17365D", pale = "#EAF3F8", amber = "#FFF2CC", rose = "#FCE4D6";
const body = { name: "Arial", size: 10, color: "#1F1F1F" };
const set = (range, values) => ws.getRange(range).values = values;

ws.mergeCells("A1:U1"); set("A1", [["Light Tower Group — $10M+ Multifamily Sale & Capital Opportunity Engine"]]);
ws.getRange("A1").format = { font: { name: "Arial", size: 14, bold: true, color: navy } };
ws.mergeCells("A2:U2"); set("A2", [["Run date: October 14, 2026 | Report-only | Targeted public-source coverage; not universal MSA or statewide coverage"]]);
ws.getRange("A2").format = { font: { name: "Arial", size: 10, italic: true, color: "#555555" } };
set("A4:B7", [["Action queue", "6 continuing leads"], ["Priority 85+", "None"], ["Qualified 75–84", "6"], ["New qualified leads", "0"]]);
set("D4:E7", [["Watch 65–74", "18 leads"], ["Excluded", "Retained + current screens"], ["$10M Gate", "Required"], ["Outreach", "Named-lead approval required"]]);
for (const r of ["A4:A7", "D4:D7"]) ws.getRange(r).format = { fill: pale, font: { name: "Arial", size: 10, bold: true, color: navy } };
for (const r of ["B4:B7", "E4:E7"]) ws.getRange(r).format = { fill: "#F9FBFD", font: body };

const headers = [["Lead ID", "Status", "Classification", "$10M Gate", "Asset / Address", "MSA", "Units", "Owner / Broker", "Observed facts", "Inference", "Counterargument", "Sale process 35", "Capital event 20", "Fit 15", "Execution 10", "Evidence 15", "Contacts 5", "Score", "Sources / dates", "Verified public contact", "Light Tower angle"]];
set("A9:U9", headers);
const actions = [
 ["PHI-011","Continuing","Active Sale",40200000,"Apartments at 1220 and 1254, 1220–1246 N. Broad St. & 1254 N. Carlisle St.","Philadelphia",309,"GREA","Tier 1 offering was Active on Oct. 13: $40.2M, 309 apartments, 8,130 SF ground-floor commercial; listed Aug. 31.","Named-broker sale process supports sale advisory, buyer financing, bridge, preferred equity, or recapitalization review.","Verify commercial-income split, five-bedroom lease structure, rent roll, authority, restrictions, and adjacent-parcel rights.",34,0,13,9,15,5,null,"LoopNet Tier 1 | listed Aug. 31; availability last observed Oct. 13; Oct. 14 live fetch approval-gated | https://www.loopnet.com/Listing/1220-N-Broad-St-1254-N-Carlisle-St/41945982/","Kenneth Wellar, GREA, (215) 454-2879, ken.wellar@grea.com","Sale advisory; buyer financing; bridge; preferred equity; recapitalization"],
 ["LA-011","Continuing","Active Sale",18000000,"Park.1915, 1915 Park Ave.","Los Angeles",36,"Marcus & Millichap","Tier 1 offering last observed available Oct. 13: 2025-built, 36-unit conventional apartment offering at $18.0M; Aug. 17 market date.","Near-term sale-advisory and acquisition-financing opportunity.","Verify restrictions, CO, seller authority, rent roll, and 2025 results.",34,0,15,10,15,5,null,"LoopNet Tier 1 | Aug. 17 market date; availability last observed Oct. 13; Oct. 14 live fetch approval-gated | https://www.loopnet.com/Listing/1915-Park-Avenue-Los-Angeles-CA/41776924/","Neema Ahadian, (310) 909-5444; Jeffrey Estrada, (310) 909-5423","Sale advisory; buyer financing; senior refinance"],
 ["LA-010","Continuing","Active Sale",15950000,"3675 Dunn Dr.","Los Angeles",18,"Alex Galuz, KW Commercial","Tier 1 offering last observed available Oct. 13: $15.95M ask, 18 apartments, Aug. 3 market date; $7.65M assumable Chase loan disclosed.","Sale process and loan-assumption feature support financing or recap analysis.","Verify authority, covenants, rent roll, loan-transfer terms, and debt.",34,0,15,10,15,5,null,"LoopNet Tier 1 | Aug. 3 market date; availability last observed Oct. 13; Oct. 14 live fetch approval-gated | https://www.loopnet.com/Listing/3675-Dunn-Dr-Los-Angeles-CA/41534752/","Alex Galuz, KW Commercial, (310) 466-0888","Sale advisory; buyer financing; senior refinance; recapitalization"],
 ["LA-015","Continuing","Active Sale",11200000,"2912–2924 W. 141st Pl. & 2925 W. Rosecrans Ave.","Los Angeles",32,"Shield Commercial Real Estate","Tier 1 offering last observed available Oct. 13: $11.2M, 32 apartments, 6.44% cap rate, Aug. 17 market date; AB 1482-only disclosure.","Dated marketing supports buyer financing, bridge, or recapitalization analysis.","Verify authority, AB 1482 scope, title, rent roll, and renovations.",34,0,15,10,15,5,null,"LoopNet Tier 1 | Aug. 17 market date; availability last observed Oct. 13; Oct. 14 live fetch approval-gated | https://www.loopnet.com/Listing/2912-2924-W-141st-Plz-Gardena-CA/41773238/","Allen Gholian, Shield Commercial, (310) 593-9868","Sale advisory; buyer financing; bridge; recapitalization"],
 ["CHI-004","Continuing","Active Sale",12000000,"Washington Plaza, 5501 W. Washington Blvd.","Chicago",172,"33 Realty","Tier 1 offering last observed available Oct. 13: $12M, 172 apartments, 98% occupancy, Jul. 22 market date.","Buyer financing, bridge, or recapitalization potential.","Verify no subsidy or university master-lease exposure, capex, authority, and rent roll.",33,0,15,10,15,5,null,"LoopNet Tier 1 | Jul. 22 market date; availability last observed Oct. 13; Oct. 14 live fetch approval-gated | https://www.loopnet.com/Listing/5501-W-Washington-Blvd-Chicago-IL/41395207/","Brian Mond, (773) 615-2626; George Benitez, (239) 443-0768","Sale advisory; buyer financing; bridge; recapitalization"],
 ["PHI-009","Continuing","Pre-Marketing / Quiet Sale",141000000,"International City Apartments, 7900 & 8400 Lindbergh Blvd.","Philadelphia",1068,"AJH Management; Newmark","Two independent Tier 2 reports support AJH's sale process and Newmark marketing. Verified 2019 sale value: $141M.","Institutional process may support sale advisory, financing, preferred equity, recapitalization, or lender dialogue.","Obtain OM, bid timing, authority, price, restrictions, T-12, and capex plan.",32,0,15,9,15,5,null,"Bisnow Aug. 31; CRE Direct Sep. 1; public-search corroboration Oct. 13 | https://www.bisnow.com/news/philadelphia/multifamily/largest-apartment-complex-for-sale-international-city","Carl Fiebig, Newmark, (215) 470-5826, Carl.Fiebig@nmrk.com","Sale advisory; buyer financing; bridge; preferred equity; recapitalization; lender dialogue"]
];
set("A10:U15", actions); ws.getRange("R10").formulas = [["=SUM(L10:Q10)"]]; ws.getRange("R10:R15").fillDown();

ws.mergeCells("A17:F17"); set("A17", [["Watch — 65–74: evidence, process, or product gates still open"]]); ws.getRange("A17").format = { fill: amber, font: { name: "Arial", size: 11, bold: true, color: navy } };
set("A18:F18", [["Lead ID", "Classification", "Asset / MSA", "Score", "Reason held", "Precise next verification step"]]);
const watch = [
 ["NY-002","Watch","99 Dumont Ave. & 499 Pennsylvania Ave., Brooklyn / NYC",70,"Current $10M, 20-unit public listing includes a 421-a exemption through 2061; restriction status unresolved.","Obtain OM, 421-a agreement, unit/rent schedule, restriction expiration, mandate, and seller authority."],
 ["FL-010","Capital Event","Landmark South, Doral / Miami",65,"$238M bridge refinance is verified; no public sale process or unmet capital need.","Confirm term, maturity, milestones, capital need, authority, and JSB/Torchlight dialogue."],
 ["LA-014","Watch","V on Victory, Van Nuys / Los Angeles",74,"Four of 68 units have unexplained restriction status.","Obtain OM and recorded covenants; reconcile all units' rent-control and affordability status."],
 ["CHI-003","Watch","4520–26 S. Drexel, Chicago",74,"Primary foreclosure/receiver evidence absent.","Obtain Cook County docket, receiver order, complaint, payoff, and current marketing status."],
 ["LA-003","Watch","Nabi Apartments, Los Angeles",72,"CDFI/project history requires covenant and title clearance.","Check recorded affordability covenant, title, HCD records, and deed restrictions."],
 ["LA-012","Watch","The Palms, Torrance / Los Angeles",72,"Current record is contingent, not active sale.","Monitor close status and verify seller authority, restrictions, rent roll, and financing/lender catalyst."],
 ["FL-001","Watch","Gables Galiano, Coral Gables / Miami",71,"Extended marketing weakens current sale-process evidence.","Obtain current broker mandate, OM, rent roll, restriction confirmation, and authority."],
 ["FL-006","Watch","Genesis Clearwater, Clearwater / Tampa",71,"Foreclosure reporting lacks primary debt and party linkage.","Obtain complaint, mortgage/assignment, debt balance, lender/borrower link, and restriction evidence."],
 ["FL-007","Watch","650 SW 1st St., Miami",70,"Total ask, product split, and restrictions unresolved.","Obtain total ask, rent roll, residential-income split, restrictions, and named broker."],
 ["PHI-008","Watch","220–222 Church, Philadelphia",70,"Unit count, commercial scope, and mandate inconsistent.","Obtain OM, lease/rent roll, unit reconciliation, and broker mandate."],
 ["PHI-007","Watch","The Maxfield, Philadelphia",70,"Listing age weakens current availability.","Obtain current exclusive, T-12, rent roll, and seller-authority confirmation."],
 ["FL-005","Watch","The Wave Apartments, Tampa",69,"Default reporting lacks a primary foreclosure record.","Obtain complaint, mortgage/assignment, lender/borrower linkage, and restriction evidence."],
 ["FL-003","Watch","California Club, Miami",69,"Current mandate evidence insufficiently recent.","Obtain current listing agreement, units/price confirmation, rent roll, and restriction check."],
 ["LA-007","Watch","The Jeffries, Los Angeles",69,"Availability and regulatory status lack corroboration.","Obtain live mandate, RSO/affordability clearance, price, and rent roll."],
 ["NY-001","Watch","30-unit portfolio, NYC",68,"Stabilization status and current sale process unclear.","Obtain HPD/DHCR records, current OM, address list, price, and broker authority."],
 ["LA-008","Watch","The Cooper, Los Angeles",68,"Listing needs RSO determination.","Verify HCIDLA RSO status, title/covenants, and current broker mandate."],
 ["LA-009","Watch","1400 Venice Blvd., Los Angeles",68,"Ask lacks dated current listing record.","Obtain dated exclusive/MLS, authority, RSO/covenant status, and rent roll."],
 ["LA-013","Watch","Park Terrace Apartments, Los Angeles",68,"Aged mandate and occupancy/regulatory evidence unresolved.","Obtain current mandate, CO, RSO determination, title/covenants, and rent roll."]
];
set("A19:F36", watch);

ws.mergeCells("A38:C38"); set("A38", [["Excluded and coverage gaps"]]); ws.getRange("A38").format = { fill: rose, font: { name: "Arial", size: 11, bold: true, color: navy } };
set("A39:C39", [["Item", "Classification", "Exclusion / coverage finding"]]);
set("A40:C48", [
 ["Oct. 14 public-source screen", "No promotion", "Fresh targeted searches produced no credible new $10M+ conventional multifamily sale or capital-event lead; generic, closed, mixed-use, and incomplete hits were not inferred into the queue."],
 ["Miami / Florida screen", "Coverage gap", "No newly verified qualified lead. Returned public hits were generic and insufficient for price/process/product gating."],
 ["NYC / North Carolina screen", "Coverage gap", "No newly verified qualified lead. One Brooklyn public listing remains Watch pending 421-a restriction evidence."],
 ["Los Angeles screen", "Excluded", "3217 S Central is explicitly TOC affordable; 743–749 Gramercy is uncompleted new construction."],
 ["Chicago screen", "Excluded", "Greater Chatham Portfolio lacks a verified current ask/debt and regulatory clearance."],
 ["430 & 499 E. 8th St., Brooklyn", "Excluded", "Current $15M refinance is expressly rent-stabilized."],
 ["727 Collins Ave., Miami Beach", "Excluded", "Hospitality master lease plus retail footprint makes it materially mixed-use."],
 ["Closed / no-catalyst records", "Excluded", "Completed refinancing, closed acquisitions, and closed sales remain out absent a current sale process or documented unmet capital need."],
 ["Coverage limitation", "Not universal", "Targeted public-source sweep only across named MSAs. It does not imply universal listing coverage in any MSA or statewide coverage in Florida or North Carolina."]
]);

for (const r of ["A9:U9", "A18:F18", "A39:C39"]) ws.getRange(r).format = { fill: navy, font: { name: "Arial", size: 9, bold: true, color: "#FFFFFF" }, wrapText: true, horizontalAlignment: "center", verticalAlignment: "center" };
for (const r of ["A10:U15", "A19:F36", "A40:C48"]) { ws.getRange(r).format.font = body; ws.getRange(r).format.wrapText = true; ws.getRange(r).format.verticalAlignment = "top"; }
ws.getRange("D10:D15").format.numberFormat = '"$"#,##0'; ws.getRange("G10:G15").format.numberFormat = "#,##0"; ws.getRange("L10:R15").format.numberFormat = "0";
for (const [col, width] of Object.entries({A:13,B:13,C:20,D:15,E:33,F:14,G:10,H:27,I:42,J:35,K:39,L:11,M:11,N:9,O:12,P:12,Q:12,R:9,S:46,T:39,U:39})) ws.getRange(`${col}:${col}`).format.columnWidth = width;
for (const row of [9,18,39]) ws.getRange(`${row}:${row}`).format.rowHeight = 40;
for (let r=10;r<=15;r++) ws.getRange(`${r}:${r}`).format.rowHeight = 108;
for (let r=19;r<=36;r++) ws.getRange(`${r}:${r}`).format.rowHeight = 52;
for (let r=40;r<=48;r++) ws.getRange(`${r}:${r}`).format.rowHeight = 48;
ws.freezePanes.freezeRows(9);
ws.tables.add("A9:U15", true, "ActionQueue20261014").style = "TableStyleMedium2";
ws.tables.add("A18:F36", true, "Watch20261014").style = "TableStyleMedium4";
ws.tables.add("A39:C48", true, "Exclusions20261014").style = "TableStyleMedium3";
wb.recalculate();
console.log((await wb.inspect({kind:"table",range:"Run 2026-10-14!A1:U15",include:"values,formulas",tableMaxRows:16,tableMaxCols:21})).ndjson);
console.log((await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",options:{useRegex:true,maxResults:300},summary:"final formula error scan"})).ndjson);
const exported = await SpreadsheetFile.exportXlsx(wb); await exported.save(outPath);
const reopened = await SpreadsheetFile.importXlsx(await FileBlob.load(outPath));
console.log((await reopened.inspect({kind:"table",range:"Run 2026-10-14!A9:U15",include:"values,formulas",tableMaxRows:7,tableMaxCols:21})).ndjson);
try { const png = await wb.render({sheetName:"Run 2026-10-14",range:"A1:U15",scale:1,format:"png"}); await fs.writeFile(`${outDir}/preview.png`, new Uint8Array(await png.arrayBuffer())); console.log("PREVIEW SAVED"); } catch (e) { console.log(`PREVIEW UNAVAILABLE: ${e.message}`); }
