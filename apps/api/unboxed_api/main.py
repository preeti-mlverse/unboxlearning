"""The UnboxEd API.

Run locally (from the repo root):
    .venv/Scripts/python -m uvicorn unboxed_api.main:app --app-dir apps/api --port 8040 --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import errors, logging_setup
from .config import get_settings
from .routers import auth, courses, documents, learning, system, users


def create_app() -> FastAPI:
    settings = get_settings()
    settings.check_production()
    logging_setup.configure()
    app = FastAPI(title="UnboxEd API", version="0.1.0",
                  description="Foundation (Wave 0): accounts, workspaces, courses, versions, documents, jobs, "
                              "enrollment and progress.",
                  docs_url=None if settings.environment == "production" else "/docs", redoc_url=None)
    errors.install(app)
    app.add_middleware(logging_setup.RequestLogMiddleware)
    # Only our own site and app may call the API from a browser, and only they get cookies.
    app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                       allow_headers=["Content-Type", "Authorization", "X-Request-ID"], expose_headers=["X-Request-ID"],
                       max_age=600)
    for r in (auth.router, users.router, courses.router, learning.router, documents.router, system.router, system.admin):
        app.include_router(r)
    return app


app = create_app()
