import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const file = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-05/light-tower-multifamily-sale-capital-2026-09-05.xlsx";
const out = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-05";
const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(file));
const check = await wb.inspect({ kind: "table", range: "Run 2026-09-05!A1:S38", include: "values,formulas", tableMaxRows: 40, tableMaxCols: 19, tableMaxCellChars: 70 });
console.log(check.ndjson);
const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan" });
console.log(errors.ndjson);
const preview = await wb.render({ sheetName: "Run 2026-09-05", range: "A1:S38", scale: 1, format: "png" });
await fs.writeFile(`${out}/run-preview.png`, new Uint8Array(await preview.arrayBuffer()));
console.log("RENDERED");
