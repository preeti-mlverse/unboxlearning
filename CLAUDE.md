# UnboxEd: working notes for Claude Code

## The product
- One product, one name: **UnboxEd**. Don't name parts or features of it ("Studio", "Learnwise"…). The domain
  unboxlearning.in is only the address.
- It's a generic engine for any content and any audience: schools, universities, companies, NGOs, independent
  creators. No school-board pickers or "Class 6–12" assumptions.

## Phase rules: Foundation (Wave 0)
Build the platform the AI plugs into, not the AI. **Do not add** OpenAI/LLM calls, RAG, a knowledge graph, lesson
generation, a tutor, voice, multilingual AI, mastery or spaced repetition, SCORM, payments, a marketplace, mobile
apps, Neo4j, Kafka or Kubernetes until Foundation is signed off (see docs/foundation/STATUS.md).

## Layout and commands
- `apps/api/unboxed_api`: FastAPI. `models/` (SQLAlchemy, one file per domain), `schemas.py` (Pydantic
  contracts), `services/` (all business logic), `routers/` (thin HTTP layer), `deps.py` (session, current user).
- `database/migrations`: Alembic. **Every schema change is a new migration**
  (`.venv/Scripts/python -m alembic -c database/alembic.ini revision --autogenerate -m "..."`), checked by
  hand, then `upgrade head`. Never edit a database directly.
- `workers/`: `worker.py` claims jobs; `handlers.py` registers job types with `@handler("type")`.
- `apps/web/src`: Next.js App Router. `lib/api.ts` is the only way to call the API, `components/ui.tsx` is the
  design system (status badges defined once), `components/blocks/` renders lesson blocks.
- `packages/shared-types/src/api.d.ts`: generated. After changing a Pydantic schema run `npm --prefix apps/web run types`.
- Tests: `cd apps/api && ../../.venv/Scripts/python -m pytest` (real Postgres `unboxed_test`), plus
  `npm --prefix apps/web run typecheck`.

## Rules that keep it safe
- Authorization goes through `Principal.can()/require()` in `services/permissions.py`. Never write ad-hoc role
  `if`s in routes. Roles come from organization memberships, never from the client.
- Every query for content filters by the caller's workspace. A record from another workspace is a 404, not a 403.
- Only DRAFT versions are editable. Enrollments point at a `course_version_id`.
- Errors leave the API as `{"error": {"code", "message", "request_id"}}`. Use `errors.AppError` helpers.
- Files: validate type by magic bytes, store under `organizations/<org>/...` in private storage, serve only via
  signed `/files/<token>` URLs.
- Long work runs as a job (`services/jobs.enqueue`, with an idempotency key), never inside a request.
- Soft-delete important content (`deleted_at`), don't hard-delete.
- New lesson block type = schema in `services/blocks.py` REGISTRY + renderer in `apps/web/src/components/blocks/BlockView.tsx`.
- Secrets live only in `.env` / server env files. `.env.example` documents every variable.
