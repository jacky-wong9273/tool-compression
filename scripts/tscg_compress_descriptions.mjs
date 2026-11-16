import { readFileSync, writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const [tscgRoot, inPath, outPath] = process.argv.slice(2);
const mod = await import(pathToFileURL(`${tscgRoot}/packages/core/src/index.ts`).href);
const payload = JSON.parse(readFileSync(inPath, "utf8"));
const catalogs = [];
for (const tools of payload.catalogs) {
  try {
    const result = mod.compressDescriptions(tools);
    catalogs.push({
      ok: true,
      tools: result.tools,
      principles: result.appliedPrinciples,
    });
  } catch (error) {
    catalogs.push({
      ok: false,
      error_name: error && error.name ? String(error.name) : "Error",
    });
  }
}
writeFileSync(outPath, JSON.stringify({ catalogs }));
