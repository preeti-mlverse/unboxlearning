# Foundation (Wave 0): status

Checked against "UNBOXED: FOUNDATION PHASE" (generic platform - content to learning.docx). Updated 2026-10-10. Swapped and deferred items are tracked in [TRACKER.md](TRACKER.md).

| Step | What | Status |
|---|---|---|
| 0A | Repository, environments, coding standards | ✅ monorepo layout, `.env.example`, `CLAUDE.md`, CI workflow, local/staging/production settings with a production safety check |
| 0B | Postgres, migrations, base schema | ✅ 13 domain tables + auth sessions/tokens, Alembic baseline `0001`, CHECK constraints for every status |
| 0C | Authentication, users, profiles | ✅ sign up, log in (email or mobile), log out, log out everywhere, refresh rotation, forgot/reset password, email confirmation by 6-digit code or link (required in staging/production), Google sign-in (switches on with credentials), session-expired and unauthorized pages, rate limiting |
| 0D | Organizations, roles, permissions | ✅ workspaces by type, memberships with multiple roles, central permission map; workspace settings + member list |
| 0E | Course, version, module, lesson models | ✅ including typed lesson blocks (text, image) with a registry |
| 0F | Storage, document records, upload | ✅ magic-byte validation, 50 MB limit, empty/corrupt checks, private org-scoped paths, signed URLs, soft delete with restore |
| 0G | Job queue and job status | ✅ Postgres-backed queue, worker, retry + backoff, idempotency, progress, stale-lock reclaim, failure hooks, retry endpoint |
| 0H | Creator app shell | ✅ dashboard, courses, documents, settings, workspace switcher |
| 0I | Manual course editor | ✅ modules/lessons (add, rename, reorder, delete), block editor with autosave, image upload with required alt text, preview, publish checks |
| 0J | Learner app shell | ✅ My learning, Find a course, course page, lesson player, progress |
| 0K | Enrollment and progress | ✅ enroll (version-pinned), in-progress/complete, course completion, continue-where-you-left-off, leave/rejoin |
| 0L | Publish and version flow | ✅ draft → publish → "Make changes" (new draft from published), discard draft, old versions archived, learners switch to latest with progress carried over |
| 0M | Admin, error handling, logging | ✅ admin stats/users/workspaces/courses/jobs/failed jobs with disable user, restore course, retry job; counters for server errors and refused/failed uploads, with an Errors & uploads list; structured errors; JSON request logs with request ID and user |
| 0N | End-to-end tests, staging deployment | 🟡 Browser end-to-end test of the whole journey passes (locally, against Docker, and in CI), including the email-code screen. Docker deploy for staging/production is written and tested locally with production settings; **the first deploy to the VPS is waiting on server access and DNS** (TRACKER P1) |

## Definition of done: the journey
Automated twice: at API level (`apps/api/tests/test_foundation_journey.py`) and through a real browser
(`apps/web/e2e/foundation-journey.spec.ts`: sign-up, course, module, lesson, content, PDF upload processed by the
worker, preview, publish, learner sign-up, enroll, complete, progress, permission and version checks).
Both run in CI on every push.

## Before calling Foundation finished
See TRACKER.md, section "Waiting on you": staging deploy (P1), real email (P2), Google credentials (P3).
