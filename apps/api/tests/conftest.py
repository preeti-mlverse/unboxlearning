"""Tests run against a real Postgres database (unboxed_test by default), built by the Alembic migrations, so the
migrations themselves are tested on every run. Each test starts from empty tables."""
import io
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL",
                                            "postgresql+psycopg://unboxed:unboxed_dev@localhost:5432/unboxed_test")
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="unboxed-test-")
os.environ["SMTP_HOST"] = ""
os.environ["REQUIRE_EMAIL_VERIFICATION"] = "false"
sys.path.insert(0, str(ROOT))  # so `workers` imports

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from unboxed_api import db as dbmod  # noqa: E402
from unboxed_api.config import get_settings  # noqa: E402
from unboxed_api.main import create_app  # noqa: E402
from unboxed_api.services import ratelimit  # noqa: E402

PASSWORD = "learn1234"


@pytest.fixture(scope="session", autouse=True)
def schema():
    cfg = Config(str(ROOT / "database" / "alembic.ini"))
    cfg.attributes["database_url"] = os.environ["DATABASE_URL"]
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    dbmod.reset_engine(os.environ["DATABASE_URL"])
    yield


@pytest.fixture(autouse=True)
def clean():
    with dbmod.engine().begin() as conn:
        tables = [r[0] for r in conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version'"))]
        conn.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
    ratelimit.reset()
    yield


@pytest.fixture(scope="session")
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app, base_url="http://testserver")


@pytest.fixture
def db():
    s = dbmod.session_factory()()
    yield s
    s.close()


def signup(app, role="educator", email=None, name="Asha Rao", org=None, phone=None, password=PASSWORD) -> TestClient:
    """A fresh browser (its own cookie jar) that has signed up and is logged in."""
    c = TestClient(app, base_url="http://testserver")
    email = email or f"{role}-{os.urandom(3).hex()}@example.com"
    r = c.post("/auth/signup", json={"name": name, "email": email, "password": password, "role": role,
                                      "org": org, "phone": phone, "agree": True})
    assert r.status_code == 201, r.text
    c.email = email
    c.me = r.json()["user"]
    return c


@pytest.fixture
def creator(app):
    return signup(app, "educator", name="Asha Rao")


@pytest.fixture
def learner(app):
    return signup(app, "learner", name="Ravi Kumar")


def outbox_token(kind: str) -> str:
    """Pull the token out of the newest email of a kind (verify / reset) written to the dev outbox."""
    box = Path(get_settings().storage_dir) / "outbox"
    marker = "verify-email?token=" if kind == "verify" else "reset-password?token="
    files = sorted(box.glob("*.txt"), key=lambda p: p.name, reverse=True)
    for f in files:
        body = f.read_text(encoding="utf-8")
        if marker in body:
            return body.split(marker, 1)[1].split()[0]
    raise AssertionError(f"no {kind} email in outbox")


def tiny_pdf(pages: int = 2) -> bytes:
    from pypdf import PdfWriter
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


def build_course(c: TestClient, title="Force and Laws of Motion") -> dict:
    """Course → module → lesson with real text → returns ids."""
    course = c.post("/courses", json={"title": title, "description": "Seed course"}).json()
    module = c.post(f"/courses/{course['id']}/modules", json={"title": "Newton's Laws"}).json()
    lesson = c.post(f"/modules/{module['id']}/lessons", json={"title": "Newton's Second Law"}).json()
    detail = c.get(f"/lessons/{lesson['id']}").json()
    block = detail["blocks"][0]
    r = c.patch(f"/blocks/{block['id']}", json={"block_type": "text",
                                                "config": {"heading": "Force and acceleration", "body": "F = m × a."}})
    assert r.status_code == 200, r.text
    return {"course": course["id"], "module": module["id"], "lesson": lesson["id"], "block": block["id"]}
