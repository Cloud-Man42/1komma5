/**
 * Export user-calibrated cable paths to JSON.
 * Run: node scripts/extract-conduit-paths.mjs
 */
import fs from "node:fs";
import { pathsToGeneratedJson } from "./energy-scene-spec.mjs";

const OUT = "src/lib/energyFlowPaths.generated.json";

const generated = pathsToGeneratedJson();
fs.writeFileSync(OUT, JSON.stringify(generated, null, 2));
for (const [id, p] of Object.entries(generated.paths)) {
  console.log(`${id}: ${p.points.length} pts — ${p.d}`);
}
