# UnboxEd web app

Next.js (App Router) + TypeScript + Tailwind + Zod. Talks to the API only through `src/lib/api.ts` (`/api/*`, forwarded to FastAPI).

    npm run dev        # http://localhost:3010 (needs the API on :8040)
    npm run types      # regenerate API types from the FastAPI schema
    npm run typecheck
    npm run build      # standalone output for deploy/

See the repo README and docs/foundation/ARCHITECTURE.md.
