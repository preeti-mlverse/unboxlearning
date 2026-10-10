# shared-types

`src/api.d.ts` is generated from the FastAPI schema (Pydantic models in `apps/api/unboxed_api/schemas.py`).
Never edit it by hand. After changing an API contract, regenerate it and let the web app's type check catch
anything that now disagrees:

    npm --prefix apps/web run types
    npm --prefix apps/web run typecheck

`src/index.ts` gives the generated schemas short names for the web app.
