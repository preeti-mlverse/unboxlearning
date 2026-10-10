# Foundation (Wave 0): status

Checked against "UNBOXED: FOUNDATION PHASE" (generic platform - content to learning.docx). Updated 2026-10-08.

| Step | What | Status |
|---|---|---|
| 0A | Repository, environments, coding standards | ✅ monorepo layout, `.env.example`, `CLAUDE.md`, CI workflow, local/staging/production settings with a production safety check |
| 0B | Postgres, migrations, base schema | ✅ 13 domain tables + auth sessions/tokens, Alembic baseline `0001`, CHECK constraints for every status |
| 0C | Authentication, users, profiles | ✅ sign up, log in (email or mobile), log out, log out everywhere, refresh rotation, forgot/reset password, email verification, session-expired and unauthorized pages, rate limiting |
| 0D | Organizations, roles, permissions | ✅ workspaces by type, memberships with multiple roles, central permission map; workspace settings + member list |
| 0E | Course, version, module, lesson models | ✅ including typed lesson blocks (text, image) with a registry |
| 0F | Storage, document records, upload | ✅ magic-byte validation, 50 MB limit, empty/corrupt checks, private org-scoped paths, signed URLs, soft delete |
| 0G | Job queue and job status | ✅ Postgres-backed queue, worker, retry + backoff, idempotency, progress, stale-lock reclaim, failure hooks, retry endpoint |
| 0H | Creator app shell | ✅ dashboard, courses, documents, settings, workspace switcher |
| 0I | Manual course editor | ✅ modules/lessons (add, rename, reorder, delete), block editor with autosave, image upload with required alt text, preview, publish checks |
| 0J | Learner app shell | ✅ My learning, Find a course, course page, lesson player, progress |
| 0K | Enrollment and progress | ✅ enroll (version-pinned), in-progress/complete, course completion, continue-where-you-left-off, leave/rejoin |
| 0L | Publish and version flow | ✅ draft → publish → "Make changes" (new draft from published), discard draft, old versions archived, learners switch to latest with progress carried over |
| 0M | Admin, error handling, logging | ✅ admin stats/users/workspaces/courses/jobs/failed jobs with disable user, restore course, retry job; structured errors; JSON request logs with request ID and user |
| 0N | End-to-end tests, staging deployment | 🟡 API-level journey test passes, and the browser journey was walked through by hand. Staging deploy scripts and configs are written but **not yet run** (needs server access and DNS for staging.unboxlearning.in) |

## Definition of done: the journey
Covered by `apps/api/tests/test_foundation_journey.py`. It was also walked through by hand in the browser on
2026-10-08: site sign-up → app → create course → module → lessons → content → upload PDF (processed by the
worker) → preview → publish → learner sign-up → catalog → enroll → lessons → complete → progress.

## Before calling Foundation finished
1. **Staging**: point `staging.unboxlearning.in` at the VPS, create `/etc/unboxed/staging.env`, run `deploy/deploy-app.sh` with `TARGET=staging`.
2. **SMTP**: pick a transactional email provider and set `SMTP_*`. Until then, emails go to `storage/outbox/`.
3. **Browser end-to-end test** in CI (Playwright) for the same journey. Today it runs at API level.
4. **Invitations**: workspace admins can't invite members yet; learners join public courses themselves.
5. Optional: Google sign-in, Sentry, and S3-compatible storage for multi-server deployments.
