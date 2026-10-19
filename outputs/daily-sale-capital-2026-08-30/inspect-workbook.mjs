import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-08-15/light-tower-multifamily-sale-capital-2026-08-15.xlsx";
const outputDir = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-08-30";
const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const overview = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 6000,
  tableMaxRows: 8,
  tableMaxCols: 12,
  tableMaxCellChars: 80,
});
console.log(overview.ndjson);
const sheetName = "Summary";
const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(`${outputDir}/existing-summary.png`, new Uint8Array(await preview.arrayBuffer()));
console.log(`preview written: ${outputDir}/existing-summary.png`);
