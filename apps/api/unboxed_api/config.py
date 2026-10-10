"""Settings come from environment variables (and the repo-root .env in local development).

Nothing secret is hard-coded: the defaults below are only safe for a developer's own machine, and
`Settings.check_production()` refuses to start a staging/production API that still uses them.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
DEV_SECRET = "dev-only-secret-change-me-dev-only-secret"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    environment: str = "local"  # local | test | staging | production
    database_url: str = "postgresql+psycopg://unboxed:unboxed_dev@localhost:5432/unboxed"

    # where the product app, the marketing site and this API live (used for links in emails and CORS)
    app_url: str = "http://localhost:3010"
    site_url: str = "http://localhost:5195"
    api_url: str = "http://localhost:8040"
    cors_origins: str = ""  # extra comma-separated origins

    # sessions
    secret_key: str = DEV_SECRET
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    refresh_token_days_short: int = 1  # when "keep me logged in" is off
    cookie_domain: str = ""  # e.g. ".unboxlearning.in" so the site and the app share the session
    cookie_secure: bool = False
    require_email_verification: bool = False

    # files
    storage_backend: str = "local"  # local (private folder on disk); s3 later
    storage_dir: Path = REPO_ROOT / "storage"
    max_upload_mb: int = 50
    signed_url_seconds: int = 300

    # email: with no SMTP host, messages are written to storage/outbox and the log instead of sent
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "UnboxEd <no-reply@unboxlearning.in>"

    # auth rate limit: attempts per window per IP + identifier
    auth_rate_limit: int = 10
    auth_rate_window_seconds: int = 300

    @field_validator("secret_key")
    @classmethod
    def no_empty_secret(cls, v: str) -> str:
        return v or DEV_SECRET  # an empty "SECRET_KEY=" line; check_production() still refuses it when deployed

    @property
    def allowed_origins(self) -> list[str]:
        extra = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return sorted({self.app_url.rstrip("/"), self.site_url.rstrip("/"), *extra})

    @property
    def is_deployed(self) -> bool:
        return self.environment in ("staging", "production")

    def check_production(self) -> None:
        if not self.is_deployed:
            return
        problems = []
        if self.secret_key == DEV_SECRET or len(self.secret_key) < 32:
            problems.append("SECRET_KEY must be set to a random value of at least 32 characters")
        if not self.cookie_secure:
            problems.append("COOKIE_SECURE must be true")
        if "unboxed_dev" in self.database_url:
            problems.append("DATABASE_URL still uses the local development password")
        if problems:
            raise RuntimeError("Refusing to start: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()
