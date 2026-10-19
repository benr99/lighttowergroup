import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-01/light-tower-multifamily-sale-capital-2026-09-01.xlsx";
const outputPath = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-02/input-preview.png";
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
console.log((await workbook.inspect({ kind: "workbook,sheet,table", maxChars: 4000, tableMaxRows: 5, tableMaxCols: 8 })).ndjson);
const preview = await workbook.render({ sheetName: "Run 2026-09-01", range: "A1:U39", scale: 1, format: "png" });
await fs.writeFile(outputPath, new Uint8Array(await preview.arrayBuffer()));
console.log(`saved ${outputPath}`);
