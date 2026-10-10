// Browser end-to-end tests: the Foundation "definition of done" journey, through the real UI.
//
//   npm run e2e            (starts nothing if the API on :8040, worker and app on :3010 are already running;
//                           otherwise starts them)
// Locally it drives your installed Google Chrome; in CI it uses Playwright's bundled Chromium.
import { resolve } from "node:path";

import { defineConfig } from "@playwright/test";

const ROOT = resolve(__dirname, "..", "..");
const PY = `"${process.platform === "win32" ? resolve(ROOT, ".venv", "Scripts", "python.exe") : resolve(ROOT, ".venv", "bin", "python")}"`;
const API_DIR = `"${resolve(ROOT, "apps", "api")}"`;

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3010",
    channel: process.env.CI ? undefined : "chrome",
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: process.env.E2E_BASE_URL ? undefined : [
    { command: `${PY} -m uvicorn unboxed_api.main:app --app-dir ${API_DIR} --port 8040`, url: "http://localhost:8040/health",
      reuseExistingServer: true, timeout: 60_000 },
    { command: `${PY} -m workers.worker`, cwd: ROOT, reuseExistingServer: true, timeout: 15_000,
      wait: { stdout: /worker started/ } },
    { command: "npm run dev", url: "http://localhost:3010/login", reuseExistingServer: true, timeout: 120_000 },
  ],
});
