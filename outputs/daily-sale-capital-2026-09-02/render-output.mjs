import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load("C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-02/light-tower-multifamily-sale-capital-2026-09-02.xlsx"));
const preview = await workbook.render({ sheetName: "Run 2026-09-02", range: "A1:U39", scale: 1, format: "png" });
const bytes = new Uint8Array(await preview.arrayBuffer());
console.log(`rendered ${bytes.byteLength}`);
const path = "C:/Users/Ben/Downloads/Lighttowergroupsite/outputs/daily-sale-capital-2026-09-02/visual-check.png";
await fs.writeFile(path, bytes);
console.log((await fs.stat(path)).size);
