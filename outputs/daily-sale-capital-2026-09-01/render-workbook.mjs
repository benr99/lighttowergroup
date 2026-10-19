import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const input = await FileBlob.load("C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-01/light-tower-multifamily-sale-capital-2026-09-01.xlsx");
const workbook = await SpreadsheetFile.importXlsx(input);
console.log("imported");
const preview = await workbook.render({ sheetName: "Run 2026-09-01", range: "A1:U39", scale: 1, format: "png" });
console.log("rendered-buffer");
await fs.writeFile("C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-01/preview.png", new Uint8Array(await preview.arrayBuffer()));
console.log("rendered");
