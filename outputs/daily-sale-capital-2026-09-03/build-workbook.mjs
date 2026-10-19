import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-02/light-tower-multifamily-sale-capital-2026-09-02.xlsx";
const outputDir = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-03";
const outputPath = `${outputDir}/light-tower-multifamily-sale-capital-2026-09-03.xlsx`;
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const sheet = workbook.worksheets.add("Run 2026-09-03");
sheet.showGridLines = false;

const navy = "#102A43";
const blue = "#1F4E78";
const lightBlue = "#D9EAF7";
const paleGold = "#FFF2CC";
const paleRed = "#FCE4D6";
const border = "#D9E2F3";
const white = "#FFFFFF";

sheet.mergeCells("A1:U1");
sheet.getRange("A1").values = [["Light Tower Group — Daily $10M+ Multifamily Sale & Capital Opportunity Engine"]];
sheet.getRange("A1:U1").format = { fill: navy, font: { bold: true, color: white, size: 15 }, horizontalAlignment: "left", verticalAlignment: "center" };
sheet.getRange("A1:U1").format.rowHeight = 28;
sheet.mergeCells("A2:U2");
sheet.getRange("A2").values = [["Run date: September 3, 2026 | Report-only | Targeted public-source sweep | No prospect outreach prepared, queued, scheduled, implied, or sent."]];
sheet.getRange("A2:U2").format = { fill: lightBlue, font: { italic: true, color: navy }, verticalAlignment: "center", wrapText: true };
sheet.getRange("A2:U2").format.rowHeight = 30;

sheet.getRange("A4:B7").values = [["Action queue", "Count"], ["Priority (85+)", 0], ["Qualified (75–84)", 2], ["New qualified action leads", 0]];
sheet.getRange("D4:E7").values = [["Pipeline", "Count"], ["Watch (65–74)", 12], ["New Watch items", 0], ["New exclusions", 1]];
for (const range of ["A4:B4", "D4:E4"]) sheet.getRange(range).format = { fill: blue, font: { bold: true, color: white } };
for (const range of ["A4:B7", "D4:E7"]) sheet.getRange(range).format.borders = { preset: "all", style: "thin", color: border };
sheet.getRange("B5:B7").format = { horizontalAlignment: "right", font: { bold: true } };
sheet.getRange("E5:E7").format = { horizontalAlignment: "right", font: { bold: true } };

sheet.mergeCells("A9:U9");
sheet.getRange("A9").values = [["Action Queue — qualified only (75–84); each item clears the $10M gate and has a current Tier 1 source."]];
sheet.getRange("A9:U9").format = { fill: navy, font: { bold: true, color: white } };
sheet.getRange("A10:U10").values = [["Lead ID", "Asset", "Class", "$10M Gate", "Score", "Run Status", "Address", "MSA", "Units", "Asking / Debt ($)", "Owner / Sponsor / Lender / Broker", "Observed Facts", "Inference", "Counterargument", "Light Tower Angle", "Observed / Listing Date", "Source Tier", "Current Availability", "Verified Public Contact", "Source URL", "Score detail"]];
sheet.getRange("A10:U10").format = { fill: blue, font: { bold: true, color: white }, wrapText: true, horizontalAlignment: "center", verticalAlignment: "center" };
sheet.getRange("A10:U10").format.rowHeight = 36;
const actions = [
  ["LA-010", "3675 Dunn Drive", "Active Sale", "$15.95M asking", 79, "Continuing", "3675 Dunn Dr.", "Los Angeles MSA", 18, 15950000, "KW Commercial; Alex Galuz", "Tier 1 listing is currently available Sept. 3: 2019 Class A, 18-unit apartment property, stated 100% occupancy and 4.60% cap rate; listed Aug. 3.", "Fresh conventional marketing supports buyer financing, acquisition-sale advisory, or senior refinance/recap.", "Older public sale-history pages and an archived broker sale tile refer to a 2023 sale; require current seller authority, rent roll/cap-rate assumptions, and any affordability covenant before engagement.", "Buyer financing / acquisition-sale advisory / senior refinance", "Listed 2026-08-03; reviewed 2026-09-03", "Tier 1", "Currently available", "Alex Galuz, KW Commercial, +1 310-466-0888", "https://www.loopnet.com/Listing/3675-Dunn-Dr-Los-Angeles-CA/41534752/", "35 sale + 0 capital + 15 fit + 9 execution + 15 evidence + 5 contact = 79"],
  ["CHI-004", "Washington Plaza", "Active Sale", "$12.0M asking", 78, "Continuing", "5501 W. Washington Blvd.", "Chicago MSA", 172, 12000000, "33 Realty; Brian Mond and George Benitez", "Tier 1 listing is currently available Sept. 3: 172 apartments, stated 98% occupancy, R-4 zoning, and a July 22 market date.", "Live marketing supports buyer financing, acquisition-sale advisory, or value-add refinance/recap.", "Subsidy contracts, deferred maintenance, seller authority, and rent-roll quality remain unverified.", "Buyer financing / acquisition-sale advisory / senior refinance", "Listed 2026-07-22; reviewed 2026-09-03", "Tier 1", "Currently available", "Brian Mond, 33 Realty, +1 773-615-2626; George Benitez, 33 Realty, +1 239-443-0768", "https://www.loopnet.com/Listing/5501-W-Washington-Blvd-Chicago-IL/41395207/", "35 sale + 0 capital + 14 fit + 9 execution + 15 evidence + 5 contact = 78"],
];
sheet.getRange("A11:U12").values = actions;
sheet.getRange("A11:U12").format = { wrapText: true, verticalAlignment: "top" };
sheet.getRange("A10:U12").format.borders = { preset: "all", style: "thin", color: border };
sheet.getRange("E11:E12").format = { horizontalAlignment: "right", font: { bold: true } };
sheet.getRange("I11:J12").format = { horizontalAlignment: "right" };
sheet.getRange("J11:J12").format.numberFormat = "$#,##0;[Red]($#,##0);-";
sheet.getRange("A11:U12").format.rowHeight = 94;

sheet.mergeCells("A14:G14");
sheet.getRange("A14").values = [["Watch (65–74) — verification required before promotion"]];
sheet.getRange("A14:G14").format = { fill: paleGold, font: { bold: true, color: navy } };
sheet.getRange("A15:G15").values = [["Lead ID", "Class / Score", "$10M Gate / Asset", "Observed facts", "Inference / counterargument", "Exact next verification step", "Source / date"]];
sheet.getRange("A15:G15").format = { fill: blue, font: { bold: true, color: white }, wrapText: true, horizontalAlignment: "center" };
const watch = [
  ["CHI-001", "Capital Event / 74", "Drexel Terraces, Chicago — $31.0M original CMBS debt; 116 units", "May 19 Tier 2 reporting names payment default, receiver motion, and roughly $35M foreclosure claim. Last process trigger remains stale.", "No current primary docket, receiver, lender, or servicer sale/workout record; cap score below action status.", "Pull current Cook County docket/receiver order; verify servicer, borrower, balance, and sale/workout timetable.", "https://therealdeal.com/chicago/2026/05/19/chicago-cmbs-foreclosure-hits-lowenstein-apartments/ | 2026-05-19"],
  ["CHI-003", "Capital Event / 74", "4520–26 S. Drexel Blvd., Chicago", "Secondary foreclosure reporting remains insufficient as primary process evidence.", "Asset/counterparty linkage and a sale timetable are not verified by Tier 1 evidence.", "Obtain Cook County primary docket and receiver order; verify servicer and sale timetable.", "Prior public reporting; reviewed 2026-09-03"],
  ["FL-003", "Active Sale / 74", "California Club Apartments, Miami — $11.0M / 64 apartments", "Known direct listing; exclusive mandate and restriction confirmation are pending.", "No current OM/rent roll or named broker is in the verified file.", "Obtain exclusive mandate, current OM/rent roll, named broker, and restriction confirmation.", "Prior direct listing; reviewed 2026-09-03"],
  ["FL-001", "Active Sale / 73", "Gables Galiano, Coral Gables — $20.0M / 27 apartments", "Public active status persists.", "Current broker mandate and seller intent are not independently confirmed.", "Obtain current broker mandate, seller intent, and price-flexibility confirmation.", "https://www.compass.com/building/c-gab-douglas-sec-coral-gables-fl/757308186771136541/ | reviewed 2026-09-03"],
  ["NY-001", "Active Sale / 73", "30-unit multifamily portfolio, NYC", "Need component-building regulatory checks and current pricing/mandate.", "Regulatory status and current process cannot be inferred from prior discovery.", "Obtain current mandate, component-building regulatory checks, and current pricing.", "Prior public listing; reviewed 2026-09-03"],
  ["LA-009", "Active Sale / 72", "1400 Venice Blvd., Los Angeles — $12.95M / 31 units", "Current offering still lacks a recorded dated exclusive / MLS entry.", "Mandatory listing-date and availability gate is not cleared.", "Obtain dated exclusive or MLS, current availability, and OM.", "Prior public listing; reviewed 2026-09-03"],
  ["LA-003", "Active Sale / 72", "Nabi Apartments, Los Angeles", "Offering source lacks mandatory listing date and current mandate confirmation.", "Date and current process cannot be inferred.", "Obtain current mandate, dated listing, covenant status, and T-12.", "Prior public listing; reviewed 2026-09-03"],
  ["LA-008", "Active Sale / 71", "The Cooper Hollywood — $18.195M / 75 units", "Current listing found; RSO status remains unverified.", "Regulatory uncertainty prevents primary-queue promotion.", "Obtain HCIDLA RSO determination and OM rent-regulation disclosure.", "Prior direct listing; reviewed 2026-09-03"],
  ["FL-006", "Capital Event / 71", "The Genesis Clearwater — 372 units", "Aug. 11 reporting identifies foreclosure without verified complaint, balance, lender/borrower linkage, or restrictions.", "Tier 2 evidence supports monitoring only.", "Pull Pinellas complaint, mortgage/assignment, balance, lender/borrower linkage, restriction evidence, and current deal contact.", "https://www.bizjournals.com/tampabay/news/2026/08/11/genesis-clearwater-apartment-foreclosure.html | 2026-08-11"],
  ["FL-007", "Active Sale / 70", "650 SW 1st St., Miami — no explicit total ask", "Tier 1 listing is available and states 21 residential units plus one 450-SF retail suite; it publishes $519,048 per residential unit but no total ask.", "Implied value is not an explicit $10M+ asking-price gate; the small retail suite and absence of named sale contact add risk.", "Obtain signed mandate / explicit total ask, rent roll, retail-income share, restriction confirmation, and named broker contact.", "https://www.loopnet.com/Listing/650-SW-1st-St-Miami-FL/41764910/ | listed 2026-08-15; reviewed 2026-09-03"],
  ["FL-005", "Capital Event / 69", "The Wave Apartments, Tampa — $26M mortgage", "Tier 2 July reporting describes a mortgage default; primary foreclosure record is not in file.", "Lender/borrower linkage, balance, and restriction status remain unverified.", "Pull Hillsborough complaint, mortgage/assignment, lender/borrower linkage, and restriction evidence.", "Prior public reporting; reviewed 2026-09-03"],
  ["FL-008", "Active Sale / 68", "300 Majorca Ave., Coral Gables — $12.75M / 17 apartments", "Public broker listing identifies a 17-unit rental building, but visible record has no current market date; originally built as condos.", "Mandatory listing-date and rental/covenant gates remain unresolved.", "Obtain current Marcus & Millichap mandate, listing date, rental-vs-condo status, and rent-regulation/covenant confirmation.", "https://www.showcase.com/300-majorca-ave-coral-gables-fl-33134/31157564/ | reviewed 2026-09-03"],
];
sheet.getRange("A16:G27").values = watch;
sheet.getRange("A15:G27").format.borders = { preset: "all", style: "thin", color: border };
sheet.getRange("A16:G27").format = { wrapText: true, verticalAlignment: "top" };
sheet.getRange("A16:G27").format.rowHeight = 70;

const exclusions = [
  ["1020 SW 2nd St., Miami", "Excluded — below $10M gate", "Current Tier 1 listing identifies 20 apartments and $325,000 per unit (about $6.5M implied); it is below the mandate threshold. https://www.loopnet.com/Listing/1020-SW-2nd-St-Miami-FL/41479349/"],
  ["PHI-006 — 2328–2344 N. 2nd St., Philadelphia", "Excluded — materially mixed asset / adjacent development parcels", "Current direct listing confirms 33 apartments, but expressly includes 3,750 SF of ground-floor retail across two suites plus four adjacent parcels conditionally approved for townhomes. It does not fit the primary conventional-rental-only queue without specific authorization. https://www.loopnet.com/Listing/2328-2344-N-2nd-St-Philadelphia-PA/41009347/"],
  ["2629 NW 17th Ave., Miami", "Excluded — development-first / workforce-housing strategy and stale date", "Current Tier 1 listing says $10.0M / 34 apartments but expressly markets covered-land, high-density, Live Local/workforce-housing potential. https://www.loopnet.com/Listing/2629-NW-17th-Ave-Miami-FL/33827457/"],
  ["The Peake, Centennial, Metropolitan Building — Los Angeles", "Excluded — known or unresolved affordable / RSO restrictions", "Retain outside primary unrestricted queue unless the mandate changes and primary regulatory evidence clears status."],
  ["Sunshine and 2629 NW 17th — Miami", "Excluded — development / materially mixed use", "Not conventional rental-multifamily dominant under the mandate."],
  ["Allapattah 23 — Miami", "Excluded — sub-$10M and product mismatch", "Current record is $9.5M and identifies a Multifamily Dormitory subtype."],
  ["Prior Philadelphia student/rent-by-bed candidates", "Excluded — product mismatch", "Do not promote without a conventional lease-structure confirmation."],
  ["Kenmore East — Chicago", "Excluded — current availability unverified", "Direct listing is no longer advertised; require renewed current marketing evidence."],
  ["Coverage limitation", "Gap", "Targeted public-source sweep only, not universal listing coverage of an MSA, Florida, or North Carolina. No newly verified action lead in NYC; named North Carolina MSAs; Orlando, Jacksonville, Fort Myers, Naples, Sarasota, Palm Bay, Lakeland, or Daytona Beach."],
  ["Delivery / outreach control", "Constraint", "No connected Google Sheets session or authenticated email connector was available. This fallback workbook was produced; historical $20M tabs were not touched. No prospect outreach was sent or implied; named lead IDs require explicit per-run approval."],
];
sheet.mergeCells("A29:U29");
sheet.getRange("A29").values = [["Exclusions, controls, and coverage gaps"]];
sheet.getRange("A29:U29").format = { fill: paleRed, font: { bold: true, color: navy } };
sheet.getRange("A30:B30").values = [["Item", "Classification / reason"]];
sheet.mergeCells("C30:U30");
sheet.getRange("C30").values = [["Evidence and action"]];
sheet.getRange("A30:U30").format = { fill: blue, font: { bold: true, color: white }, horizontalAlignment: "center" };
for (let index = 0; index < exclusions.length; index += 1) {
  const row = 31 + index;
  const [item, reason, evidence] = exclusions[index];
  sheet.getRange(`A${row}:B${row}`).values = [[item, reason]];
  sheet.mergeCells(`C${row}:U${row}`);
  sheet.getRange(`C${row}`).values = [[evidence]];
}
sheet.getRange("A30:U40").format.borders = { preset: "all", style: "thin", color: border };
sheet.getRange("A31:U40").format = { wrapText: true, verticalAlignment: "top" };
sheet.getRange("A31:U40").format.rowHeight = 62;

const widths = { A: 13, B: 23, C: 15, D: 23, E: 8, F: 13, G: 25, H: 18, I: 8, J: 16, K: 31, L: 43, M: 34, N: 34, O: 35, P: 21, Q: 12, R: 20, S: 33, T: 52, U: 28 };
for (const [column, width] of Object.entries(widths)) sheet.getRange(`${column}:${column}`).format.columnWidth = width;
sheet.getRange("A:U").format.verticalAlignment = "top";
sheet.freezePanes.freezeRows(10);
sheet.freezePanes.freezeColumns(2);

const check = await workbook.inspect({ kind: "table", range: "Run 2026-09-03!A1:U40", include: "values,formulas", tableMaxRows: 40, tableMaxCols: 21 });
console.log(check.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan" });
console.log(errors.ndjson);
await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
const preview = await workbook.render({ sheetName: "Run 2026-09-03", range: "A1:U40", scale: 1, format: "png" });
await fs.writeFile(`${outputDir}/preview-2026-09-03.png`, new Uint8Array(await preview.arrayBuffer()));
console.log(`saved ${outputPath}`);
