/* Runs the JavaScript register layer over a JSON array of strings.
 * Driven by crosscheck.py, which compares the output against neutro.py. */
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const here = path.dirname(url.fileURLToPath(import.meta.url));
// webapp/neutro.js in the working tree; ../../neutro.js in the published repo
const candidates = [
  path.join(here, "..", "webapp", "neutro.js"),
  path.join(here, "..", "..", "neutro.js"),
];
const found = candidates.find(p => fs.existsSync(p));
if (!found) { console.error("neutro.js not found in", candidates); process.exit(1); }
const { toNeutro } = await import(url.pathToFileURL(found).href);
const inputs = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
console.log(JSON.stringify(inputs.map(toNeutro)));
