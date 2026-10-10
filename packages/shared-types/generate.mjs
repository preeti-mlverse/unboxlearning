// Regenerate the shared API types from the FastAPI schema:  npm --prefix apps/web run types
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const py = [join(root, ".venv", "Scripts", "python.exe"), join(root, ".venv", "bin", "python")].find(existsSync) ?? "python";
execFileSync(py, [join(here, "dump_openapi.py")], { stdio: "inherit" });
const bin = join(root, "apps", "web", "node_modules", "openapi-typescript", "bin", "cli.js");
execFileSync(process.execPath, [bin, join(here, "openapi.json"), "-o", join(here, "src", "api.d.ts")], { stdio: "inherit" });
