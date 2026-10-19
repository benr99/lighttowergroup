import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const input = await FileBlob.load("C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-08-31/light-tower-multifamily-sale-capital-2026-08-31.xlsx");
const workbook = await SpreadsheetFile.importXlsx(input);
const preview = await workbook.render({ sheetName: "Run 2026-08-31", range: "A1:U38", scale: 1, format: "png" });
await fs.writeFile("C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-08-31/preview.png", new Uint8Array(await preview.arrayBuffer()));
console.log("rendered");
