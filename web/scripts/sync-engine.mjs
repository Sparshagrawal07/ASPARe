// Copy the ASPARe engine (src/aspare + config) into api/_engine so the Vercel Python functions can import it.
import { cpSync, rmSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const web = join(here, "..");
const repo = join(web, "..");
const dest = join(web, "api", "_engine");
if (!existsSync(join(repo, "src", "aspare"))) {
  console.log("engine sources not found (building outside the monorepo?); keeping committed copy");
  process.exit(0);
}
rmSync(dest, { recursive: true, force: true });
mkdirSync(dest, { recursive: true });
const skip = (p) => p.includes("__pycache__") || p.endsWith(".pyc");
cpSync(join(repo, "src", "aspare"), join(dest, "aspare"), { recursive: true, filter: (s) => !skip(s) });
cpSync(join(repo, "config"), join(dest, "config"), { recursive: true });
console.log("engine synced into api/_engine");
