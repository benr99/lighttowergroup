import fs from "node:fs/promises";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const outputDir = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-08-15";
const outFile = `${outputDir}/light-tower-multifamily-sale-capital-2026-08-15.xlsx`;
const navy = "#102A43";
const blue = "#1F5A8A";
const paleBlue = "#E8F1F8";
const paleGreen = "#E8F5E9";
const paleYellow = "#FFF4CC";
const paleRed = "#FDECEC";
const darkGray = "#374151";
const border = { preset: "inside", style: "thin", color: "#D9E2EC" };

const actionRows = [
  ["CHI-001", "Drexel Terraces", "Capital Event", "$31.0M original debt", 85, "Continuing", "4830–4848 1/2 S. Drexel Blvd.", "Chicago MSA", 116, 31000000, "Lowenstein-controlled borrower; Trimont/LNR Partners servicers; Morgan Stanley originator", "May 19 reporting identifies foreclosure, payment default, and receiver motion; June 29 servicing commentary identifies a lender foreclosure/workout strategy.", "Lender-workout path supports note/workout capital, receiver-transition senior financing, or lender-led sale dialogue.", "A cure, modification, or receiver stabilization could defer a disposition; no public sale mandate.", "Lender dialogue / note-workout capital / receiver-transition senior refinance", new Date("2026-06-29"), "Tier 2", "Capital event; not confirmed sale process", "Trimont / LNR Partners publicly named; no individual deal contact", "https://dealcharts.org/capitalmarkets/abs/cmbs/counterparty/specialservicer/midland_loan_services"],
  ["CHI-004", "Washington Plaza", "Active Sale", "$12.0M asking", 78, "Continuing", "5501 W. Washington Blvd.", "Chicago MSA", 172, 12000000, "33 Realty; Brian Mond and George Benitez", "Tier 1 listing remains current; July 22 market date; 172 apartments; 98% occupancy; R-4 zoning.", "Fresh conventional sale process supports buyer financing and acquisition-sale advisory.", "Subsidy contracts, deferred maintenance, seller authority, and rent roll are unverified.", "Buyer financing / acquisition-sale advisory / senior refinance", new Date("2026-07-22"), "Tier 1", "Currently available (reviewed Aug. 15)", "Brian Mond +1 773-615-2626; George Benitez +1 239-443-0768", "https://www.loopnet.com/Listing/5501-W-Washington-Blvd-Chicago-IL/41395207/"],
  ["PHI-006", "2328–2344 N. 2nd St.", "Active Sale", "$12.0M asking", 77, "Continuing", "2328–2344 N. 2nd St.", "Philadelphia MSA", 33, 11999999, "McCann Commercial; Jon O'Shea", "Tier 1 listing remains current; June 22 market date; 33 apartments, 3,750 SF ground-floor commercial, and four adjacent residential parcels; 17 units under master lease through July 2027.", "Sale process and master-lease rollover support buyer financing, lease-transition bridge, or recapitalization analysis.", "Retail, adjacent parcels, master-lease assignability, and campus proximity require underwriting; confirm non-student lease structure.", "Buyer financing / lease-transition bridge / acquisition-sale advisory", new Date("2026-06-22"), "Tier 1", "Currently available (reviewed Aug. 15)", "Jon O'Shea +1 267-780-3419", "https://www.loopnet.com/Listing/2328-2344-N-2nd-St-Philadelphia-PA/41009347/"],
];

const watchRows = [
  ["LA-008", "The Cooper", "Active Sale", 71, "New", "6615 Franklin Ave.", "Los Angeles MSA", 75, 18195000, "July 20, 2026 MLS market date; Marcus & Millichap; Rick Raymundo", "1962 vintage makes RSO status material; no primary clearance reviewed.", "Pull HCIDLA RSO determination and OM rent-regulation disclosure.", "https://www.showcase.com/6615-franklin-ave-los-angeles-ca-90028/41365216/"],
  ["LA-009", "1400 Venice Blvd.", "Active Sale", 72, "New", "1400 Venice Blvd.", "Los Angeles MSA", 31, 12950000, "Broker page says 1988 asset is not subject to LA rent control.", "Listing date is absent; mandatory date-recording gate is unmet.", "Obtain dated exclusive/MLS record, current availability, and OM.", "https://www.kittywallaceteam.com/available-listings"],
  ["FL-003", "California Club Apartments", "Active Sale", 74, "Continuing", "750 NE 195th St.", "Miami MSA", 64, 11000000, "MLS A12016834 active; MSP Group, LLC; annual leases.", "Pricing/marketing data differ across public syndications; no individual broker verified.", "Obtain exclusive mandate, current OM/rent roll, and restriction confirmation.", "https://www.coldwellbankerhomes.com/fl/miami/750-ne-195th-st/pid_71184682/"],
  ["CHI-003", "4520–26 S. Drexel Blvd.", "Capital Event", 74, "Continuing", "4520–26 S. Drexel Blvd.", "Chicago MSA", 68, 19400000, "June 10 reporting cites $19.4M+ alleged payoff and Greystone special servicing.", "Corroborating report is derivative; primary docket/receiver order absent.", "Pull Cook County primary docket and receiver order; confirm servicer, timetable, and regulatory constraints.", "https://therealdeal.com/chicago/2026/06/10/greystone-smacks-lowensteins-with-another-cmbs-foreclosure/"],
  ["NY-001", "30-Unit MF Portfolio Sale", "Active Sale", 73, "Continuing", "Portfolio addresses undisclosed", "NYC MSA", 30, 18050000, "Listing says 100% free-market / occupied; January 5 listing date.", "Listing is stale; component-building regulation is unverified.", "Obtain live mandate, component-building regulatory records, and current price guidance.", "https://www.loopnet.com/Listing/30-Unit-MF-Portfolio-Sale/38971102/"],
  ["FL-001", "Gables Galiano", "Active Sale", 73, "Continuing", "1091 Galiano St.", "Miami MSA", 27, 20000000, "MLS offering carries January 16 list date and extended marketing duration.", "Marketing duration creates mandate and price-freshness risk.", "Confirm current mandate and seller price flexibility with public broker.", "https://bogatovrealty.com/miami/commercial/4950965/"],
  ["LA-003", "Nabi Apartments", "Active Sale", 72, "Continuing", "744 S. Mariposa Ave.", "Los Angeles MSA", 31, 10000000, "Broker-facing records show $10.0M offering.", "Listing date not displayed; affordability-covenant status not cleared.", "Obtain current mandate, listing date, affordability status, and T-12.", "https://www.showcase.com/744-s-mariposa-ave-los-angeles-ca-90005/41176859/"],
  ["LA-007", "The Jeffries", "Active Sale", 71, "Continuing", "117 Winston St.", "Los Angeles MSA", 43, 10600000, "Listing states RSO-exempt but mixed use.", "Residential-income dominance and retail scope are not cleared.", "Obtain OM/broker confirmation of residential income dominance and retail scope.", "https://www.loopnet.com/Listing/117-Winston-St-Los-Angeles-CA/40413204/"],
  ["PHI-008", "220–222 Church St.", "Active Sale", 70, "Continuing", "220–222 Church St.", "Philadelphia MSA", 40, 12000000, "Record has unit-count differences, commercial anchors, and retail/short-term-stay issues.", "Use and unit count remain ambiguous.", "Confirm unit count, apartment-income dominance, and live mandate.", "https://www.loopnet.com/Listing/220-222-Church-St-Philadelphia-PA/39165415/"],
  ["PHI-007", "The Maxfield", "Active Sale", 70, "Continuing", "1533 Parrish St.", "Philadelphia MSA", null, null, "Long-marketed listing uses placeholder pro forma.", "Pricing / actual operating performance cannot be relied upon.", "Obtain current mandate, true T-12, and market-rate confirmation.", "https://www.loopnet.com/Listing/1533-Parrish-St-Philadelphia-PA/35238282/"],
  ["FL-004", "601 NE 22nd St.", "Active Sale", 70, "Continuing", "601 NE 22nd St.", "Miami MSA", null, 11777000, "Listing has Feb. 26, 2025 date and syndication unit-count differences.", "Materially stale; restriction status and current seller intent unknown.", "Obtain written current mandate, seller intent, restriction status, and rent roll.", "https://www.canvasre.com/property/43-A11774630-601-Ne-22nd-St-Miami-FL-33137/"],
];

const exclusionRows = [
  ["CHI-002", "Kenmore East Apartments", "Current availability unverified", "Direct Tier 1 listing now says it is no longer advertised; do not treat as active sale without new exclusive mandate or broker confirmation.", "https://www.loopnet.com/Listing/5417-N-Kenmore-Ave-Chicago-IL/40025034/"],
  ["FL-X01", "Sunshine, 4110 NW 22nd Ave.; 2629 NW 17th Ave.", "Product mismatch", "Under-construction/mixed-use project and high-density redevelopment/workforce-housing play.", ""],
  ["LA-X01", "4186 S. Western Ave.; 1350 W. Court St.; The Peake; 5110 N. Bakman Ave.", "Regulatory restriction", "Restricted-affordable or uncleared TOC/HCA characteristics.", ""],
  ["LA-X02", "The Centennial; Metropolitan Building", "RSO / affordable", "Public evidence identifies affordable or RSO constraints.", ""],
  ["PHI-X01", "3207 Spring Garden; 4210–4216 Chestnut; 4200 Ludlow; 4042/4046–48 Chestnut", "Student housing", "Student-housing / rent-by-bed characteristics.", ""],
  ["PHI-X02", "220–250 S. 5th St.", "Development land", "Land/development opportunity, not an existing conventional-rental acquisition.", ""],
];

const coverageRows = [
  ["Coverage limitation", "Targeted public-source research only; not universal listing coverage and never statewide Florida or North Carolina coverage."],
  ["No new qualified action lead", "NYC; named North Carolina MSAs; Tampa, Orlando, Jacksonville, Fort Myers, Naples, Sarasota, Palm Bay, Lakeland, Daytona Beach; non-screened portions of named MSAs."],
  ["Action threshold", "Only 85+ priority and 75–84 qualified leads are in Action Queue. Scores above 69 need Tier 1 evidence or two independent Tier 2 sources."],
  ["Outreach control", "No outreach drafted, queued, scheduled, implied, or sent. Explicit approval of named IDs is required for this run."],
];

function title(sheet, titleText, subtitle, endCol) {
  sheet.getRange(`A1:${endCol}1`).merge();
  sheet.getRange("A1").values = [[titleText]];
  sheet.getRange(`A1:${endCol}1`).format = { fill: navy, font: { bold: true, color: "#FFFFFF", size: 16 }, horizontalAlignment: "left", verticalAlignment: "center" };
  sheet.getRange(`A2:${endCol}2`).merge();
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${endCol}2`).format = { fill: paleBlue, font: { color: darkGray, italic: true }, horizontalAlignment: "left", verticalAlignment: "center", wrapText: true };
  sheet.getRange(`A1:${endCol}1`).format.rowHeight = 28;
  sheet.getRange(`A2:${endCol}2`).format.rowHeight = 30;
}

function tableStyle(sheet, range, headerRange) {
  sheet.getRange(headerRange).format = { fill: blue, font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true, borders: { preset: "outside", style: "thin", color: "#7B8794" } };
  sheet.getRange(range).format.wrapText = true;
  sheet.getRange(range).format.verticalAlignment = "top";
  sheet.getRange(range).format.borders = border;
}

const wb = Workbook.create();
console.log("checkpoint: workbook");
const summary = wb.worksheets.add("Summary");
const action = wb.worksheets.add("Action Queue");
const watch = wb.worksheets.add("Watch");
const excluded = wb.worksheets.add("Exclusions");
const coverage = wb.worksheets.add("Coverage & Sources");
for (const s of [summary, action, watch, excluded, coverage]) s.showGridLines = false;

title(summary, "Light Tower Group — $10M+ Multifamily Sale & Capital Opportunity Engine", "Run date: August 15, 2026 | Report-only | Targeted public-source sweep", "H");
summary.getRange("A4:B4").values = [["Action Queue", "Count"]];
summary.getRange("A5:B7").values = [["Priority (85+)", null], ["Qualified (75–84)", null], ["Total Action Queue", null]];
summary.getRange("B5").formulas = [["=COUNTIF('Action Queue'!E5:E50,\">=85\")"]];
summary.getRange("B6").formulas = [["=COUNTIFS('Action Queue'!E5:E50,\">=75\",'Action Queue'!E5:E50,\"<85\")"]];
summary.getRange("B7").formulas = [["=SUM(B5:B6)"]];
summary.getRange("D4:E4").values = [["Pipeline", "Count"]];
summary.getRange("D5:E7").values = [["Watch (65–74)", null], ["Excluded", null], ["New Action Leads", null]];
summary.getRange("E5").formulas = [["=COUNT('Watch'!D5:D50)"]];
summary.getRange("E6").formulas = [["=COUNTA('Exclusions'!A5:A50)"]];
summary.getRange("E7").formulas = [["=COUNTIF('Action Queue'!F5:F50,\"New\")"]];
summary.getRange("A9:H9").merge();
summary.getRange("A9").values = [["Action Queue — 85+ priority and 75–84 qualified only"]];
summary.getRange("A10:H10").values = [["Lead ID", "Asset", "Classification", "$10M Gate", "Score", "Run Status", "MSA", "Light Tower Angle"]];
summary.getRange("A11:H13").formulas = [
  ["='Action Queue'!A5", "='Action Queue'!B5", "='Action Queue'!C5", "='Action Queue'!D5", "='Action Queue'!E5", "='Action Queue'!F5", "='Action Queue'!H5", "='Action Queue'!O5"],
  ["='Action Queue'!A6", "='Action Queue'!B6", "='Action Queue'!C6", "='Action Queue'!D6", "='Action Queue'!E6", "='Action Queue'!F6", "='Action Queue'!H6", "='Action Queue'!O6"],
  ["='Action Queue'!A7", "='Action Queue'!B7", "='Action Queue'!C7", "='Action Queue'!D7", "='Action Queue'!E7", "='Action Queue'!F7", "='Action Queue'!H7", "='Action Queue'!O7"],
];
summary.getRange("A15:H15").merge();
summary.getRange("A15").values = [["Run controls & coverage"]];
summary.getRange("A16:H19").merge(true);
summary.getRange("A16").values = [["No prospect outreach was drafted, queued, scheduled, implied, or sent. Outreach requires explicit approval of named lead IDs for this specific run."], ["Coverage is targeted public-source research in specified MSAs only; it is never universal coverage or statewide Florida/North Carolina coverage."], ["Kenmore East moved to Exclusions after its direct listing reported it was no longer advertised; current availability must be reverified before reconsideration."], ["The Cooper and 1400 Venice are new Watch items only: respectively RSO status and a dated listing record remain unverified."]];
tableStyle(summary, "A4:B7", "A4:B4");
tableStyle(summary, "D4:E7", "D4:E4");
tableStyle(summary, "A10:H13", "A10:H10");
summary.getRange("A9:H9").format = { fill: navy, font: { bold: true, color: "#FFFFFF" } };
summary.getRange("A15:H15").format = { fill: navy, font: { bold: true, color: "#FFFFFF" } };
summary.getRange("A16:H19").format = { fill: paleYellow, wrapText: true, verticalAlignment: "top" };
summary.getRange("A4:H19").format.rowHeight = 24;
summary.getRange("A16:H19").format.rowHeight = 36;
summary.getRange("B5:B7").format.numberFormat = "#,##0";
summary.getRange("E5:E7").format.numberFormat = "#,##0";
summary.getRange("E11:E13").format.numberFormat = "#,##0";
summary.getRange("A:A").format.columnWidth = 18;
summary.getRange("B:B").format.columnWidth = 30;
summary.getRange("C:C").format.columnWidth = 18;
summary.getRange("D:D").format.columnWidth = 18;
summary.getRange("E:E").format.columnWidth = 12;
summary.getRange("F:F").format.columnWidth = 14;
summary.getRange("G:G").format.columnWidth = 20;
summary.getRange("H:H").format.columnWidth = 42;
summary.freezePanes.freezeRows(2);
console.log("checkpoint: summary");

title(action, "Action Queue", "Only 85+ priority and 75–84 qualified leads. $10M Gate is recorded for each action item.", "T");
const actionHeaders = ["Lead ID", "Asset", "Classification", "$10M Gate", "Score", "Run Status", "Address", "MSA", "Units", "Asking / Debt ($)", "Owner / Sponsor / Lender / Broker", "Observed Facts", "Inference", "Counterargument", "Light Tower Angle", "Observed / Listing Date", "Source Tier", "Current Availability", "Verified Public Contact", "Source URL"];
action.getRange("A4:T4").values = [actionHeaders];
action.getRange("A5:T7").values = actionRows;
tableStyle(action, "A4:T7", "A4:T4");
action.getRange("E5:E7").format.numberFormat = "#,##0";
action.getRange("I5:I7").format.numberFormat = "#,##0";
action.getRange("J5:J7").format.numberFormat = "\"$\"#,##0;[Red](\"$\"#,##0);-";
action.getRange("P5:P7").format.numberFormat = "yyyy-mm-dd";
action.getRange("A5:T7").format.rowHeight = 64;
const actionWidths = [14, 24, 18, 18, 10, 13, 28, 18, 10, 17, 36, 55, 48, 48, 45, 15, 12, 25, 36, 56];
actionWidths.forEach((w, i) => action.getRangeByIndexes(0, i, 8, 1).format.columnWidth = w);
action.freezePanes.freezeRows(4);
console.log("checkpoint: action");

title(watch, "Watch", "Scores 65–74. Each lead requires the precise verification step shown before promotion.", "M");
const watchHeaders = ["Lead ID", "Asset", "Classification", "Score", "Run Status", "Address", "MSA", "Units", "Asking / Debt ($)", "Observed Status", "Why Watch", "Next Verification Step", "Source URL"];
watch.getRange("A4:M4").values = [watchHeaders];
watch.getRange("A5:M15").values = watchRows;
tableStyle(watch, "A4:M15", "A4:M4");
watch.getRange("D5:D15").format.numberFormat = "#,##0";
watch.getRange("H5:H15").format.numberFormat = "#,##0";
watch.getRange("I5:I15").format.numberFormat = "\"$\"#,##0;[Red](\"$\"#,##0);-";
watch.getRange("A5:M15").format.rowHeight = 54;
const watchWidths = [14, 28, 18, 10, 13, 28, 18, 10, 17, 48, 42, 52, 56];
watchWidths.forEach((w, i) => watch.getRangeByIndexes(0, i, 16, 1).format.columnWidth = w);
watch.freezePanes.freezeRows(4);
console.log("checkpoint: watch");

title(excluded, "Exclusions", "Items retained outside the primary queue because they do not meet active-sale, conventional-multifamily, or regulatory-clearance requirements.", "E");
excluded.getRange("A4:E4").values = [["Lead ID", "Asset / Group", "Exclusion Basis", "Observed Reason", "Source URL"]];
excluded.getRange("A5:E10").values = exclusionRows;
tableStyle(excluded, "A4:E10", "A4:E4");
excluded.getRange("A5:E10").format.rowHeight = 46;
[14, 46, 28, 75, 60].forEach((w, i) => excluded.getRangeByIndexes(0, i, 11, 1).format.columnWidth = w);
excluded.freezePanes.freezeRows(4);
console.log("checkpoint: exclusions");

title(coverage, "Coverage & Sources", "Run constraints, market gaps, and source-tier operating standards.", "D");
coverage.getRange("A4:B4").values = [["Topic", "Detail"]];
coverage.getRange("A5:B8").values = coverageRows;
tableStyle(coverage, "A4:B8", "A4:B4");
coverage.getRange("A10:D10").merge();
coverage.getRange("A10").values = [["Source-tier hierarchy"]];
coverage.getRange("A11:D14").values = [
  ["Tier", "Permitted Source Type", "Use", "Promotion Standard"],
  ["Tier 1", "Direct broker/owner/lender/receiver/servicer/auction listing, OM, dated/price/named-contact MLS, public court/recorder/CMBS/servicer records", "Decision evidence", "Required for top-scoring direct evidence where available"],
  ["Tier 2", "SEC filings, broker announcements, credible CRE trade press, public sponsor/lender communication", "Corroboration", "Two independent sources can support a score above 69"],
  ["Tier 3", "Discovery-only sources", "Lead discovery", "Never sufficient for promotion"],
];
coverage.getRange("A10:D10").format = { fill: navy, font: { bold: true, color: "#FFFFFF" } };
tableStyle(coverage, "A11:D14", "A11:D11");
coverage.getRange("A5:B8").format.rowHeight = 45;
coverage.getRange("A12:D14").format.rowHeight = 52;
[24, 95, 22, 48].forEach((w, i) => coverage.getRangeByIndexes(0, i, 15, 1).format.columnWidth = w);
coverage.freezePanes.freezeRows(4);
console.log("checkpoint: coverage");

// Score-based visual cues for easy daily triage.
action.getRange("E5:E7").format.fill = paleGreen;
watch.getRange("D5:D15").format.fill = paleYellow;
excluded.getRange("C5:C10").format.fill = paleRed;
console.log("checkpoint: format");

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(wb);
await output.save(outFile);

const actionInspect = await wb.inspect({ kind: "table", range: "Action Queue!A4:T7", include: "values,formulas", tableMaxRows: 8, tableMaxCols: 20 });
const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan" });
console.log(actionInspect.ndjson);
console.log(errors.ndjson);
console.log(JSON.stringify({ outFile }));
