# UnboxEd

**Any knowledge in. Real learning out.**

This repo holds the UnboxEd platform: the product app, its API, the background worker and the marketing site
(unboxlearning.in). It is in the **Foundation phase (Wave 0)**. Accounts, workspaces, a manual course editor,
versions, private documents, background jobs, enrollment and progress are in place. These are what the knowledge
engine (ingestion, knowledge graph, learning-experience compiler, tutor) plugs into next.

```
apps/
  api/          FastAPI + SQLAlchemy + Pydantic: the API (auth, courses, documents, jobs, learning, admin)
  web/          Next.js + TypeScript + Tailwind + Zod: the product app (app.unboxlearning.in)
packages/
  shared-types/ TypeScript types generated from the API's OpenAPI schema (never hand-edited)
  ui/, learning-components/   reserved for later waves
ai/             reserved: providers, ingestion, knowledge, compiler, tutor (empty during Foundation)
database/
  migrations/   Alembic migrations: every schema change lives here
  seeds/        development seed data
workers/        background job worker + job handlers
site/           marketing site (static, python build.py) — sign-up and log-in call the API
deploy/         nginx + systemd + release script for the app and API
docs/foundation architecture, deployment, status against the Foundation spec
legacy/         the earlier engine and app, kept for reference while Wave 1+ is rebuilt
```

## Run it locally

You need Python 3.12, Node 22 and PostgreSQL 17. If you have Docker but no Postgres, `docker compose up --build`
runs the whole stack in containers instead.

```bash
# once: database, Python env, web deps
psql -U postgres -h localhost -c "CREATE ROLE unboxed LOGIN PASSWORD 'unboxed_dev' CREATEDB"
psql -U postgres -h localhost -c "CREATE DATABASE unboxed OWNER unboxed" -c "CREATE DATABASE unboxed_test OWNER unboxed"
python -m venv .venv && .venv/Scripts/pip install -r apps/api/requirements-dev.txt     # .venv/bin on macOS/Linux
npm --prefix apps/web install
cp .env.example .env                      # every value has a local default

# schema + demo data
.venv/Scripts/python -m alembic -c database/alembic.ini upgrade head
.venv/Scripts/python database/seeds/seed.py

# run (three terminals)
.venv/Scripts/python -m uvicorn unboxed_api.main:app --app-dir apps/api --port 8040 --reload   # API  → http://localhost:8040/docs
.venv/Scripts/python -m workers.worker                                                          # background jobs
npm --prefix apps/web run dev                                                                    # app  → http://localhost:3010
```

The marketing site: `cd site && python build.py && python -m http.server 5195 --directory public`. Its
/signup/ and /login/ pages create real accounts through the local API and hand you over to the app.

Seed accounts are `creator@unboxed.local`, `learner@unboxed.local` and `admin@unboxed.local`. The password is in
`database/seeds/seed.py`. Without SMTP settings, verification and reset emails are written to `storage/outbox/`.

## Tests

```bash
cd apps/api && ../../.venv/Scripts/python -m pytest      # API, permissions, versions, files, jobs, the full Foundation journey
npm --prefix apps/web run typecheck                      # web app against the generated API types
npm --prefix apps/web run types                          # regenerate types after changing an API schema
```

## More

- [docs/foundation/ARCHITECTURE.md](docs/foundation/ARCHITECTURE.md): how it fits together, and why
- [docs/foundation/STATUS.md](docs/foundation/STATUS.md): the Foundation checklist (0A–0N), what's done and what's next
- [docs/foundation/DEPLOY.md](docs/foundation/DEPLOY.md): staging and production on the VPS
