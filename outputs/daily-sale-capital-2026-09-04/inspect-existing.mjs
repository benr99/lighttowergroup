import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const source = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-03/light-tower-multifamily-sale-capital-2026-09-03.xlsx";
const outputDir = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-04";
const blob = await FileBlob.load(source);
const workbook = await SpreadsheetFile.importXlsx(blob);
const summary = await workbook.inspect({ kind: "workbook,sheet,table", maxChars: 5000, tableMaxRows: 8, tableMaxCols: 12, tableMaxCellChars: 80 });
console.log(summary.ndjson);
const preview = await workbook.render({ sheetName: "Run 2026-09-03", range: "A1:M32", scale: 1, format: "png" });
await fs.writeFile(`${outputDir}/existing-preview.png`, new Uint8Array(await preview.arrayBuffer()));
