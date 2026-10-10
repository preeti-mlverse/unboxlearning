# UnboxEd Foundation: architecture

```
 unboxlearning.in (static site)          app.unboxlearning.in
 ┌───────────────────────────┐          ┌──────────────────────────────────────────┐
 │ /signup  /login  (site.js)│──POST───▶│ nginx ── /api/* ──▶ FastAPI (uvicorn)     │
 └───────────────────────────┘ cookies  │       └─ /*     ──▶ Next.js (app UI)      │
                                        └───────────────┬──────────────────────────┘
                                                        │ SQLAlchemy
                              ┌─────────────────────────▼─────────┐   private files
                              │ PostgreSQL: users … jobs (+ queue)│   storage/files/organizations/<org>/…
                              └─────────────────────────▲─────────┘
                                                        │ SELECT … FOR UPDATE SKIP LOCKED
                                                  workers/worker.py (job handlers)
```

## The seven questions the Foundation answers

| Question | Answer in the code |
|---|---|
| Who is using UnboxEd? | `users` (credentials, status) + `profiles` (name, language, timezone). `services/accounts.py` |
| What are they allowed to do? | Roles on `organization_memberships` → permissions in `services/permissions.py`, checked server-side |
| What are they creating or learning? | `courses → course_versions → modules → lessons → lesson_blocks`; `enrollments` + `lesson_progress` |
| Where is the data stored? | PostgreSQL, schema owned by Alembic migrations in `database/migrations` |
| Where are uploaded files stored? | Private storage (`services/storage.py`, local disk today, S3-compatible later), reached only via signed URLs |
| How do long-running tasks run? | `jobs` table as the queue + `workers/worker.py`. Retry with backoff, idempotency keys, progress, stale-lock recovery |
| How do we change content without breaking previous versions? | Only drafts are editable; publishing archives the old version; enrollments pin a `course_version_id` |

## Decisions and why

**Self-hosted auth (not Supabase).** UnboxEd runs on its own VPS beside the site, so accounts live in our
Postgres. Passwords are hashed with Argon2id. Sessions are an HttpOnly access cookie (a 15-minute JWT that names
its session row, so revoking the row ends it at once) plus a rotating refresh cookie (stored only as a SHA-256
hash). Email-verification and reset tokens are single-use and hashed. `users.auth_provider` and `auth_user_id`
leave room to move to an external provider without changing anything else.

**One origin for the app.** The browser calls `/api/*` on the app's own origin (a Next.js rewrite locally, nginx in
production), so cookies are first-party and CSRF exposure is limited to same-site requests (`SameSite=Lax`, JSON
bodies, CORS allow-list). The marketing site calls the API cross-origin with `credentials: "include"`. In
production `COOKIE_DOMAIN=.unboxlearning.in` shares the session, so after logging in on the site the visitor
lands in the app already signed in.

**Postgres as the job queue (no Redis yet).** The doc suggests Redis + worker. With one database already in place,
a `jobs` table claimed with `FOR UPDATE SKIP LOCKED` gives the properties that matter (one run per job, retries,
stored errors, progress, idempotency) with nothing extra to operate. The handler interface doesn't change if a
Redis-backed queue replaces the claim loop later.

**Roles on memberships, permissions in one map.** `creator`, `learner` and `org_admin` are per-workspace roles, and
platform admin is a user flag. Routes ask `principal.require(P.COURSE_EDIT, org_id)`, never "is this a teacher".
Anyone signed in may enroll in public courses, so a learner needs no workspace.

**Versioned content with lineage.** Copying a published version into a draft keeps each module, lesson and block's
`lineage_id`. That's how "switch to the new version" carries a learner's finished lessons across, and later how
analytics can follow a lesson through regenerations.

**Typed blocks, not HTML.** A lesson is a list of `{block_type, config}`, validated against a registry (`text`,
`image` today). The engine will emit the same shape (`process_flow`, `mcq`, `simulation`…), and block rows already
have `generated_by / model / prompt_version / pipeline_version` columns for provenance.

**Contracts generated, not duplicated.** Pydantic schemas → OpenAPI → `packages/shared-types/src/api.d.ts`.
CI regenerates the file and fails if it changed, so the web app can't drift from the API.

## Signing up from the site

| Site choice | What gets created | Lands on |
|---|---|---|
| Learner | user + profile | `/learn` |
| Educator | user + "<First name>'s workspace" (independent creator); org admin + creator | `/create` |
| School / NGO / Organization | user + workspace with the given name and type; org admin + creator | `/create` |
| (no organisation name given) | user only | `/onboarding` → create workspace |

## Where Wave 1 plugs in
- `documents` rows already go `uploaded → queued → processing → ready/failed` through the `document.inspect` job.
  Real ingestion becomes another handler (or replaces this one). The upload flow, polling UI and statuses stay as they are.
- New tables (`document_sections`, `source_blocks`, `concepts`, `source_chunks`, embeddings via pgvector) hang off
  `document_id` and `organization_id`.
- Generated lessons are ordinary blocks inside a draft version, so creators review, edit and publish them with
  the same editor.
