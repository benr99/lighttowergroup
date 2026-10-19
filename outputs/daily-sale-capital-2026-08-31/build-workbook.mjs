import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-08-30/light-tower-multifamily-sale-capital-2026-08-30.xlsx";
const outputDir = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-08-31";
const outputPath = `${outputDir}/light-tower-multifamily-sale-capital-2026-08-31.xlsx`;
const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const sheet = workbook.worksheets.add("Run 2026-08-31");
sheet.showGridLines = false;

const navy = "#102A43";
const blue = "#1F4E78";
const lightBlue = "#D9EAF7";
const paleGold = "#FFF2CC";
const paleRed = "#FCE4D6";
const border = "#D9E2F3";

sheet.mergeCells("A1:U1");
sheet.getRange("A1").values = [["Light Tower Group — Daily $10M+ Multifamily Sale & Capital Opportunity Engine"]];
sheet.getRange("A1:U1").format = { fill: navy, font: { bold: true, color: "#FFFFFF", size: 15 }, horizontalAlignment: "left", verticalAlignment: "center" };
sheet.getRange("A1:U1").format.rowHeight = 28;
sheet.mergeCells("A2:U2");
sheet.getRange("A2").values = [["Run date: August 31, 2026 | Report-only | Targeted public-source sweep | No prospect outreach prepared, queued, scheduled, implied, or sent."]];
sheet.getRange("A2:U2").format = { fill: lightBlue, font: { italic: true, color: navy }, verticalAlignment: "center", wrapText: true };
sheet.getRange("A2:U2").format.rowHeight = 30;

sheet.getRange("A4:B7").values = [["Action queue", "Count"], ["Priority (85+)", 0], ["Qualified (75–84)", 4], ["New qualified action leads", 0]];
sheet.getRange("D4:E7").values = [["Pipeline", "Count"], ["Watch (65–74)", 11], ["New Watch items", 0], ["New exclusions", 0]];
sheet.getRange("A4:B4").format = { fill: blue, font: { bold: true, color: "#FFFFFF" } };
sheet.getRange("D4:E4").format = { fill: blue, font: { bold: true, color: "#FFFFFF" } };
sheet.getRange("A4:B7").format.borders = { preset: "all", style: "thin", color: border };
sheet.getRange("D4:E7").format.borders = { preset: "all", style: "thin", color: border };
sheet.getRange("B5:B7").format = { horizontalAlignment: "right", font: { bold: true } };
sheet.getRange("E5:E7").format = { horizontalAlignment: "right", font: { bold: true } };

sheet.mergeCells("A9:U9");
sheet.getRange("A9").values = [["Action Queue — qualified only (75–84); each item clears the $10M gate and has a current, public source."]];
sheet.getRange("A9:U9").format = { fill: navy, font: { bold: true, color: "#FFFFFF" } };
const headers = [["Lead ID", "Asset", "Class", "$10M Gate", "Score", "Run Status", "Address", "MSA", "Units", "Asking / Debt ($)", "Owner / Sponsor / Lender / Broker", "Observed Facts", "Inference", "Counterargument", "Light Tower Angle", "Observed / Listing Date", "Source Tier", "Current Availability", "Verified Public Contact", "Source URL", "Score detail"]];
sheet.getRange("A10:U10").values = headers;
sheet.getRange("A10:U10").format = { fill: blue, font: { bold: true, color: "#FFFFFF" }, wrapText: true, horizontalAlignment: "center", verticalAlignment: "center" };
sheet.getRange("A10:U10").format.rowHeight = 36;
const actions = [
  ["CHI-001", "Drexel Terraces", "Capital Event", "$31.0M original CMBS debt; ~$34.9M alleged payoff", 79, "Continuing", "4830–4848 1/2 S. Drexel Blvd.", "Chicago MSA", 116, 31000000, "Lowenstein-controlled borrower; Trimont / LNR Partners servicers; Morgan Stanley originator", "May 19 reporting identifies missed payments, receiver motion, and roughly $35M foreclosure claim; independent reporting identifies the special-servicing transfer tied to payment default.", "Workout may support lender/note dialogue, receiver-transition senior financing, or sponsor recapitalization.", "A cure, modification, or receiver stabilization may defer disposition; no verified public sale mandate.", "Lender dialogue / note-workout capital / receiver-transition senior refinance", "Trigger 2026-05-19; reviewed 2026-08-31", "Tier 2 x2", "Capital event; public sale process unverified", "Trimont and LNR Partners publicly identified; no individual deal contact", "https://therealdeal.com/chicago/2026/05/19/chicago-cmbs-foreclosure-hits-lowenstein-apartments/ | https://www.multifamilydive.com/news/multifamily-chicago-la-florida-servicing/816371/", "27+20+13+9+8+2 = 79"],
  ["LA-010", "3675 Dunn Drive", "Active Sale", "$15.95M asking", 79, "Continuing", "3675 Dunn Dr.", "Los Angeles MSA", 18, 15950000, "KW Commercial; Alex Galuz", "Tier 1 listing remains currently available on Aug. 31: 2019 Class A, 18-unit apartment property, stated 100% occupancy and 4.60% cap rate; market date Aug. 3.", "Fresh conventional marketing supports buyer financing, acquisition-sale advisory, or senior refinance/recap.", "Confirm seller authority, rent roll/cap-rate assumptions, and any recorded affordability covenant.", "Buyer financing / acquisition-sale advisory / senior refinance", "Listed 2026-08-03; reviewed 2026-08-31", "Tier 1", "Currently available", "Alex Galuz, KW Commercial, +1 310-466-0888", "https://www.loopnet.com/Listing/3675-Dunn-Dr-Los-Angeles-CA/41534752/", "35+0+15+9+15+5 = 79"],
  ["CHI-004", "Washington Plaza", "Active Sale", "$12.0M asking", 78, "Continuing", "5501 W. Washington Blvd.", "Chicago MSA", 172, 12000000, "33 Realty; Brian Mond and George Benitez", "Tier 1 listing remains currently available on Aug. 31: 172 apartments, 98% stated occupancy, R-4 zoning and July 22 market date.", "Live marketing supports buyer financing, acquisition-sale advisory, or value-add refinance/recap.", "Subsidy contracts, deferred maintenance, seller authority, and rent-roll quality remain unverified.", "Buyer financing / acquisition-sale advisory / senior refinance", "Listed 2026-07-22; reviewed 2026-08-31", "Tier 1", "Currently available", "Brian Mond +1 773-615-2626; George Benitez +1 239-443-0768", "https://www.loopnet.com/Listing/5501-W-Washington-Blvd-Chicago-IL/41395207/", "35+0+14+9+15+5 = 78"],
  ["PHI-006", "2328–2344 N. 2nd St.", "Active Sale", "$11,999,999 asking", 75, "Continuing", "2328–2344 N. 2nd St.", "Philadelphia MSA", 33, 11999999, "McCann Commercial; Jon O'Shea", "Tier 1 listing remains currently available Aug. 31: 33 apartments, 3,750 SF ground-floor commercial, four adjacent residential parcels, 85% stated occupancy, and 17 units under a corporate master lease through July 2027.", "Live marketing and lease rollover support buyer financing, lease-transition bridge, or recapitalization.", "Retail income, parcel inclusion, master-lease assignability, and conventional/non-student leasing require underwriting; listing age reduces recency score.", "Buyer financing / lease-transition bridge / acquisition-sale advisory", "Listed 2026-06-22; reviewed 2026-08-31", "Tier 1", "Currently available", "Jon O'Shea, McCann Commercial, +1 267-780-3419", "https://www.loopnet.com/Listing/2328-2344-N-2nd-St-Philadelphia-PA/41009347/", "35+4+10+8+13+5 = 75"],
];
sheet.getRange("A11:U14").values = actions;
sheet.getRange("A11:U14").format = { wrapText: true, verticalAlignment: "top" };
sheet.getRange("A10:U14").format.borders = { preset: "all", style: "thin", color: border };
sheet.getRange("E11:E14").format = { horizontalAlignment: "right", font: { bold: true } };
sheet.getRange("I11:J14").format = { horizontalAlignment: "right" };
sheet.getRange("J11:J14").format.numberFormat = "$#,##0;[Red]($#,##0);-";
sheet.getRange("A11:U14").format.rowHeight = 88;

sheet.mergeCells("A16:F16");
sheet.getRange("A16").values = [["Watch (65–74) — verification required before promotion"]];
sheet.getRange("A16:F16").format = { fill: paleGold, font: { bold: true, color: navy } };
sheet.getRange("A17:F17").values = [["Lead ID", "Class / Score", "$10M Gate / Asset", "Observed Facts", "Exact next verification step", "Source / Date"]];
sheet.getRange("A17:F17").format = { fill: blue, font: { bold: true, color: "#FFFFFF" }, wrapText: true, horizontalAlignment: "center" };
const watch = [
  ["FL-007", "Active Sale / 72", "650 SW 1st St, Miami — ~$10.90M implied by $519,048/unit × 21 units", "Tier 1 listing is currently available Aug. 31, calls the asset 21-unit multifamily and provides an Aug. 15 market date, but gives price only per unit and no individual sale contact.", "Obtain signed sale mandate / explicit total ask, current rent roll, confirmation of no material retail or restriction, and named broker contact.", "https://www.loopnet.com/Listing/650-SW-1st-St-Miami-FL/41764910/ | listed 2026-08-15; reviewed 2026-08-31"],
  ["FL-008", "Active Sale / 68", "300 Majorca Ave, Coral Gables — $12.75M asking / 17 apartments", "Public broker listing identifies a 17-unit rental building, but visible record has no current market date; originally built as condos.", "Obtain current Marcus & Millichap mandate, listing date, rental-vs-condo status, and rent-regulation/covenant confirmation.", "https://www.showcase.com/300-majorca-ave-coral-gables-fl-33134/31157564/ | reviewed 2026-08-31"],
  ["CHI-003", "Capital Event / 74", "4520–26 S. Drexel Blvd., Chicago", "Secondary foreclosure reporting remains insufficient as primary process evidence.", "Obtain Cook County primary docket and receiver order; verify servicer and sale timetable.", "Prior public reporting; review 2026-08-31"],
  ["FL-006", "Capital Event / 71", "The Genesis Clearwater — 372 units", "Aug. 11 reporting identifies foreclosure, without verified complaint, debt balance, lender/borrower linkage, or restrictions.", "Pull Pinellas complaint, mortgage/assignment, balance, lender/borrower linkage, restriction evidence, and current deal contact.", "https://www.bizjournals.com/tampabay/news/2026/08/11/genesis-clearwater-apartment-foreclosure.html | 2026-08-11"],
  ["FL-005", "Capital Event / 69", "The Wave Apartments, Tampa — $26M mortgage", "Tier 2 July reporting describes a mortgage default; primary foreclosure record is not in file.", "Pull Hillsborough complaint, mortgage/assignment, lender/borrower linkage, and restriction evidence.", "Prior public reporting; review 2026-08-31"],
  ["LA-008", "Active Sale / 71", "The Cooper Hollywood — $18.195M / 75 units", "Current listing found; RSO status remains unverified.", "Obtain HCIDLA RSO determination and OM rent-regulation disclosure.", "Prior direct listing; review 2026-08-31"],
  ["LA-009", "Active Sale / 72", "1400 Venice Blvd. — $12.95M / 31 units", "Current offering still lacks a recorded dated exclusive / MLS entry.", "Obtain dated exclusive or MLS, current availability, and OM.", "Prior public listing; review 2026-08-31"],
  ["LA-003", "Active Sale / 72", "Nabi Apartments, Los Angeles", "Offering source lacks mandatory listing date and current mandate confirmation.", "Obtain current mandate, dated listing, covenant status, and T-12.", "Prior public listing; review 2026-08-31"],
  ["NY-001", "Active Sale / 73", "30-Unit MF Portfolio Sale, NYC", "Need component-building regulatory checks and current pricing/mandate.", "Obtain current mandate, component-building regulatory checks, and current pricing.", "Prior public listing; review 2026-08-31"],
  ["FL-003", "Active Sale / 74", "California Club Apartments, Miami — $11.0M / 64 apartments", "Known direct listing but exclusive mandate and restriction confirmation are pending.", "Obtain exclusive mandate, current OM/rent roll, named broker, and restriction confirmation.", "Prior direct listing; review 2026-08-31"],
  ["FL-001", "Active Sale / 73", "Gables Galiano, Coral Gables — $20.0M / 27 apartments", "Public active status persists, but current broker mandate / seller intent remains unverified.", "Obtain current broker mandate, seller intent, and price-flexibility confirmation.", "https://www.compass.com/building/c-gab-douglas-sec-coral-gables-fl/757308186771136541/ | reviewed 2026-08-31"],
];
sheet.getRange("A18:F28").values = watch;
sheet.getRange("A17:F28").format.borders = { preset: "all", style: "thin", color: border };
sheet.getRange("A18:F28").format = { wrapText: true, verticalAlignment: "top" };
sheet.getRange("A18:F28").format.rowHeight = 58;

const exclusions = [
  ["Allapattah 23 — 2311–2325 NW 22nd Ave, Miami", "Excluded — current price below $10M gate; product record includes Multifamily Dormitory subtype", "Direct current listing shows $9.5M / 23 units. Do not promote without verified $10M+ revised ask and conventional-only product confirmation. https://www.loopnet.com/Listing/2311-2325-NW-22nd-Ave-Miami-FL/41046654/"],
  ["The Peake, Centennial, Metropolitan Building — Los Angeles", "Excluded — known or unresolved affordable / RSO restrictions", "Retain outside primary unrestricted queue unless the mandate changes and primary regulatory evidence clears status."],
  ["Sunshine and 2629 NW 17th — Miami", "Excluded — development / materially mixed-use", "Not conventional rental-multifamily dominant under the mandate."],
  ["Prior Philadelphia student/rent-by-bed candidates", "Excluded — product mismatch", "Do not promote without a conventional lease-structure confirmation."],
  ["Kenmore East — Chicago", "Excluded — current availability unverified", "Direct listing no longer advertised; require renewed current marketing evidence."],
  ["Coverage limitation", "Gap", "Targeted public-source sweep only, not universal listing coverage of an MSA, Florida, or North Carolina. No new qualified lead was verified in NYC, named North Carolina MSAs, Orlando, Jacksonville, Fort Myers, Naples, Sarasota, Palm Bay, Lakeland, or Daytona Beach."],
  ["Delivery / outreach control", "Constraint", "No connected Google Sheets session or authenticated email connector was available. This fallback workbook was produced; historical $20M tabs were not touched. No prospect outreach was sent or implied; named lead IDs require explicit per-run approval."],
];
sheet.mergeCells("A30:U30");
sheet.getRange("A30").values = [["Exclusions, controls, and coverage gaps"]];
sheet.getRange("A30:U30").format = { fill: paleRed, font: { bold: true, color: navy } };
sheet.getRange("A31:B31").values = [["Item", "Classification / reason"]];
sheet.mergeCells("C31:U31");
sheet.getRange("C31").values = [["Evidence and action"]];
sheet.getRange("A31:U31").format = { fill: blue, font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center" };
for (let index = 0; index < exclusions.length; index += 1) {
  const row = 32 + index;
  const [item, reason, evidence] = exclusions[index];
  sheet.getRange(`A${row}:B${row}`).values = [[item, reason]];
  sheet.mergeCells(`C${row}:U${row}`);
  sheet.getRange(`C${row}`).values = [[evidence]];
}
sheet.getRange("A31:U38").format.borders = { preset: "all", style: "thin", color: border };
sheet.getRange("A32:U38").format = { wrapText: true, verticalAlignment: "top" };
sheet.getRange("A32:U38").format.rowHeight = 60;

const widths = { A: 12, B: 22, C: 14, D: 22, E: 8, F: 13, G: 24, H: 18, I: 8, J: 15, K: 30, L: 42, M: 34, N: 34, O: 34, P: 20, Q: 12, R: 20, S: 30, T: 52, U: 25 };
for (const [column, width] of Object.entries(widths)) sheet.getRange(`${column}:${column}`).format.columnWidth = width;
sheet.getRange("A:U").format.verticalAlignment = "top";
sheet.freezePanes.freezeRows(10);
sheet.freezePanes.freezeColumns(2);

const check = await workbook.inspect({ kind: "table", range: "Run 2026-08-31!A1:U38", include: "values,formulas", tableMaxRows: 38, tableMaxCols: 21 });
console.log(check.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan" });
console.log(errors.ndjson);
await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
const preview = await workbook.render({ sheetName: "Run 2026-08-31", range: "A1:U38", scale: 1, format: "png" });
await fs.writeFile(`${outputDir}/preview.png`, new Uint8Array(await preview.arrayBuffer()));
console.log(`saved ${outputPath}`);
