// The Foundation "definition of done", through the real UI:
// CREATOR  sign up → workspace → course → module → lesson → content → upload PDF → preview → publish
// LEARNER  sign up → enroll → open course → open lesson → read → complete → see progress
// SYSTEM   PDF stored privately, processed by a background job, version kept, permissions enforced
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Page } from "@playwright/test";

const OUTBOX = join(__dirname, "..", "..", "..", "storage", "outbox");
const run = Date.now().toString(36);
const PASSWORD = `journey${run}9`;

/** If the email must be confirmed first, read the code from the dev outbox and type it in. */
async function confirmEmailIfAsked(page: Page, email: string) {
  await page.waitForURL(/\/(create|learn|onboarding|verify-email)/);
  if (!page.url().includes("/verify-email")) return;
  const files = readdirSync(OUTBOX).map((f) => join(OUTBOX, f)).sort((a, b) => statSync(b).mtimeMs - statSync(a).mtimeMs);
  const mail = files.map((f) => readFileSync(f, "utf8")).find((m) => m.includes(`To: ${email}`) && /code is:/.test(m));
  const code = mail?.match(/code is:\s+(\d{6})/)?.[1];
  expect(code, "confirmation code in the dev outbox").toBeTruthy();
  await page.getByLabel("Digit 1").fill(code!); // pasting the whole code fills every box and submits
  await page.waitForURL(/\/(create|learn|onboarding)/);
}

async function signUp(page: Page, role: "educator" | "learner", name: string, email: string, org?: string) {
  await page.goto(`/signup?role=${role}`);
  await page.getByLabel("Full name").fill(name);
  await page.getByLabel("Email", { exact: true }).fill(email);
  if (org) await page.getByLabel(/Workspace name|Organisation name/).fill(org);
  await page.getByLabel("Create a password").fill(PASSWORD);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Create my account" }).click();
  await confirmEmailIfAsked(page, email);
}

/** A tiny valid 3-page PDF. */
function pdf(): Buffer {
  const objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R 4 0 R 5 0 R] /Count 3 >>",
    ...[0, 1, 2].map(() => "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>")];
  let out = "%PDF-1.4\n";
  const offs: number[] = [];
  objs.forEach((o, i) => { offs.push(out.length); out += `${i + 1} 0 obj\n${o}\nendobj\n`; });
  const xref = out.length;
  out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n${offs.map((o) => `${String(o).padStart(10, "0")} 00000 n \n`).join("")}`;
  out += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(out);
}

test("creator builds and publishes a course; a learner completes it", async ({ browser }) => {
  const courseTitle = `Journey course ${run}`;
  const creatorEmail = `creator-${run}@e2e.example.com`;
  const learnerEmail = `learner-${run}@e2e.example.com`;

  // ---------------- creator
  const creatorCtx = await browser.newContext();
  const page = await creatorCtx.newPage();
  await signUp(page, "educator", "Esha Creator", creatorEmail, `E2E Workspace ${run}`);
  await expect(page.getByRole("heading", { name: /What will you unbox today/ })).toBeVisible();

  await page.getByRole("button", { name: "+ Create course" }).first().click();
  await page.getByRole("dialog").getByLabel("Course title").fill(courseTitle);
  await page.getByRole("dialog").getByRole("button", { name: "Create course" }).click();
  await expect(page.getByRole("heading", { name: courseTitle })).toBeVisible();

  await page.getByLabel("New module title").fill("Basics");
  await page.getByRole("button", { name: "+ Module" }).click();
  await page.getByLabel("New lesson in Basics").fill("First lesson");
  await page.getByRole("button", { name: "+ Lesson" }).click();
  await expect(page.getByRole("link", { name: "First lesson" })).toBeVisible();

  // publishing an empty lesson is blocked with a reason
  await page.getByRole("button", { name: "Publish" }).click();
  await expect(page.getByText("Lesson 'First lesson' has no content yet.")).toBeVisible();

  // source PDF: private upload, processed by the worker
  await page.locator('input[type="file"]').setInputFiles({ name: "chapter.pdf", mimeType: "application/pdf", buffer: pdf() });
  const docRow = page.locator("li", { hasText: "chapter.pdf" });
  await expect(docRow.getByText("Ready")).toBeVisible({ timeout: 30_000 });
  await expect(docRow).toContainText("3 pages");

  // write the lesson (autosaves)
  await page.getByRole("link", { name: "First lesson" }).click();
  await page.getByLabel("Heading (optional)").fill("Hello, cells");
  await page.getByLabel("Text").fill("Every living thing is made of **cells**.");
  await expect(page.getByText("Saved")).toBeVisible();

  // preview shows what learners will see
  await page.getByRole("link", { name: "Preview" }).click();
  await expect(page.getByRole("heading", { name: "Hello, cells" })).toBeVisible();
  await page.getByRole("link", { name: "Back to editing" }).click();
  await page.getByRole("link", { name: "Back to course" }).click();

  await page.getByRole("button", { name: "Publish" }).click();
  await expect(page.getByText("Published. Learners can now find and join this version.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Make changes" })).toBeVisible();

  // ---------------- learner (a separate browser session)
  const learnerCtx = await browser.newContext();
  const lp = await learnerCtx.newPage();
  await signUp(lp, "learner", "Lalit Learner", learnerEmail);
  await expect(lp.getByRole("link", { name: "Create" })).toHaveCount(0); // no creator navigation

  await lp.goto("/learn/catalog");
  const card = lp.locator("div", { has: lp.getByRole("heading", { name: courseTitle }) }).last();
  await card.getByRole("button", { name: "Join course" }).click();
  await expect(lp.getByRole("heading", { name: "First lesson" })).toBeVisible();
  await expect(lp.getByText("Every living thing is made of")).toBeVisible();
  await lp.getByRole("button", { name: /Complete lesson/ }).click();
  await expect(lp.getByText("Course complete!")).toBeVisible();

  await lp.goto("/learn/progress");
  await expect(lp.locator("li", { hasText: courseTitle })).toContainText("100%");

  // ---------------- system: the learner can't edit the course or open the creator's files
  const courseId = new URL(page.url()).pathname.split("/").pop();
  const edit = await lp.request.patch(`/api/courses/${courseId}`, { data: { title: "Hacked" } });
  expect(edit.status()).toBe(404);
  const docs = await lp.request.get(`/api/documents`);
  expect(await docs.json()).toEqual([]);

  // editing again makes version 2; the learner stays on version 1
  await page.getByRole("button", { name: "Make changes" }).click();
  await expect(page.getByText("You're editing a new draft")).toBeVisible();
  const mine = await (await lp.request.get("/api/enrollments")).json();
  expect(mine[0].version_number).toBe(1);

  await creatorCtx.close();
  await learnerCtx.close();
});
