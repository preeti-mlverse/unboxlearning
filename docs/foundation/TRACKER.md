# Foundation tracker: swapped items, deferred items, open decisions

What we built differently from the Foundation spec (🔁), what the spec itself marks for later (⏳), and what is
waiting on a decision or on you (⏸). Update the **Status** column as things move.

Last updated: 2026-10-10.

## 🔁 Built differently from the spec

| # | Spec says | What we did | Why | Decision | Status |
|---|---|---|---|---|---|
| S1 | Supabase Auth | Accounts in our own API: Argon2 passwords, rotating cookie sessions, email codes, Google sign-in | Runs on our own VPS; no extra vendor | ✅ Approved (2026-10-08) | Done |
| S2 | Supabase Storage | Private storage volume on the server, org-scoped paths, signed links | Simplest for a single server | ✅ Approved for now; move to S3/Supabase later (2026-10-10) | Done. Migration later (L5) |
| S3 | Redis + worker | Postgres table as the queue (`FOR UPDATE SKIP LOCKED`) + worker | One less service; same retries, idempotency and progress | ✅ Approved (2026-10-10) | Done |
| S4 | Vercel + managed API | Own VPS: Docker Compose stacks for staging and production behind nginx | Same server as the site; full control | ✅ Approved: own VPS (2026-10-10) | Scripts ready; first deploy pending (P1) |
| S5 | shadcn/ui | Our own small component set (`components/ui.tsx`) | The spec allows it; matches the site's look | — | Done |
| S6 | TanStack Query "if required" | Plain fetch + small hooks | Not needed yet | — | Done |
| S7 | Separate migrations 001/002/003 | Baseline `0001`, then incremental `0002`… | Built in one go; every later change is its own migration | — | Done |
| S8 | `/course-versions`, `/progress` endpoints | `/courses/{id}/versions`, `/enrollments/{id}/progress/{lesson}` | Clearer ownership in the URL | — | Done |
| S9 | Version status REVIEW + "approved" step | REVIEW exists; Publish acts as approval | You want to try the end-user experience first (2026-10-10) | ⏸ Revisit after staging trial | Open (D2) |
| S10 | `tests/` at the repo root | `apps/api/tests` (API) + `apps/web/e2e` (browser) | Tests live next to the code they test | — | Done |

## ⏳ Marked "later" by the spec (not Foundation work)

| # | Item | Belongs to | Status |
|---|---|---|---|
| L1 | pgvector, embeddings, document_sections, source_chunks, concepts | Wave 1 ingestion | Not started |
| L2 | Document `source_type`, `language`, `parser_version` | Wave 1 ingestion | Not started (`page_count` done) |
| L3 | `organizations/<org>/generated/` files | Wave 2 generation | Not started (folder layout ready) |
| L4 | Lesson fields `concept_ids`, `learning_objectives`, `difficulty` | Wave 1–2 | Not started |
| L5 | Move files to S3 / Supabase Storage | When there's more than one server, or large volumes | Not started (storage interface ready) |
| L6 | Malware scanning of uploads | Before opening uploads to the public | Not started |
| L7 | Sentry / PostHog / Grafana | Observability, when traffic justifies it | Not started (admin counters + health done) |
| L8 | AI call logging (model, latency, tokens, cost) | Wave 2 | Not started (block provenance columns ready) |
| L9 | Rate limits on AI endpoints | Wave 2 | Auth endpoints done |
| L10 | Microsoft SSO, SAML, school federation | Enterprise, much later | Not started (spec says don't start) |
| L11 | Everything on the spec's "do not build" list | Waves 1+ | Not started, by design |

## ⏸ Waiting on you, or open decisions

| # | Item | Needs | Status |
|---|---|---|---|
| P1 | First staging deploy, then production | VPS SSH access (user + IP) or you running `server-setup.sh`; DNS A records for `app` and `staging` | Waiting |
| P2 | Real email sending | Resend account, its DNS records, SMTP details in the server env files (see EMAIL_AND_GOOGLE.md) | Waiting |
| P3 | Google sign-in | Google Cloud OAuth client; ID + secret in the server env files (see EMAIL_AND_GOOGLE.md) | Code done; waiting on credentials |
| P4 | Sentry error alerts | A Sentry account + DSN, if wanted | Optional |
| P5 | Terms and Privacy review | Your (or a lawyer's) review, now that real accounts, Google sign-in and an email provider are involved | Optional but advised before public launch |
| D1 | OTP beyond email | Done: 6-digit email code for confirming the address. Open: log in with an emailed code (no password)? Mobile SMS OTP (needs an SMS provider such as MSG91 and DLT registration in India)? | Decide |
| D2 | Separate review/approval before publishing | Decide after trying the creator experience on staging | Decide |
| D3 | Workspace invitations (admins inviting creators/learners) | Not in the spec's Foundation list, but needed for schools and companies | Next up when you say so |

## ✅ Recently completed (2026-10-10)

| Item | Where |
|---|---|
| Pushed to GitHub `main`; CI passing | `.github/workflows/ci.yml` |
| Docker Compose verified locally, plus a production-config stack | `docker-compose.yml`, `docker-compose.prod.yml` |
| Email confirmation required in production, with a 6-digit code (plus link) | `services/accounts.py`, `/verify-email` |
| Sign in with Google (on as soon as credentials are set) | `services/google.py`, app + site buttons |
| Automated browser test of the full journey (local Chrome; Chromium in CI) | `apps/web/e2e/` |
| Admin counters: server errors, uploads refused, uploads failed, failed documents, plus an Errors & uploads list | Admin page |
| Restore deleted documents | Documents → Recently deleted |
| Fixed: the two course→version foreign keys missing since 0001 | migration `0002` |
