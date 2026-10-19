import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const file = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-04/light-tower-multifamily-sale-capital-2026-09-04.xlsx";
const out = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-04";
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(file));
const check = await workbook.inspect({ kind: "table", range: "Run 2026-09-04!A1:S35", include: "values,formulas", tableMaxRows: 36, tableMaxCols: 19, tableMaxCellChars: 80 });
console.log(check.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan" });
console.log(errors.ndjson);
const preview = await workbook.render({ sheetName: "Run 2026-09-04", range: "A1:S35", scale: 1, format: "png" });
await fs.writeFile(`${out}/run-preview.png`, new Uint8Array(await preview.arrayBuffer()));
console.log("RENDERED");
