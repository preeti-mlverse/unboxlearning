from fastapi.testclient import TestClient

from unboxed_api.models import User
from tests.conftest import PASSWORD, build_course, signup


def make_admin(app, db) -> TestClient:
    c = signup(app, "learner", email="admin@example.com", name="Platform Admin")
    user = db.query(User).filter_by(email="admin@example.com").one()
    user.is_platform_admin = True
    db.commit()
    return c


def test_admin_endpoints_are_admin_only(app, db, creator, learner):
    for path in ("/admin/stats", "/admin/users", "/admin/organizations", "/admin/courses", "/admin/jobs"):
        assert learner.get(path).status_code == 403
        assert creator.get(path).status_code == 403
    admin = make_admin(app, db)
    build_course(creator)
    stats = admin.get("/admin/stats").json()
    assert stats["users"] == 3 and stats["courses"] == 1 and stats["organizations"] == 1
    assert len(admin.get("/admin/users?q=example").json()) == 3
    assert admin.get("/admin/organizations").json()[0]["courses"] == 1
    assert admin.get("/admin/jobs?status=failed").json() == []


def test_admin_can_disable_a_user(app, db, learner):
    admin = make_admin(app, db)
    uid = learner.get("/users/me").json()["id"]
    assert admin.post(f"/admin/users/{uid}/status?status=disabled").status_code == 200
    assert learner.get("/users/me").status_code == 401
    r = TestClient(app).post("/auth/login", json={"identifier": learner.email, "password": PASSWORD})
    assert r.status_code == 403 and r.json()["error"]["code"] == "ACCOUNT_DISABLED"


def test_errors_are_structured_and_carry_request_id(client):
    r = client.get("/courses/does-not-exist", headers={"X-Request-ID": "req-123"})
    body = r.json()
    assert r.status_code == 401 and set(body["error"]) >= {"code", "message", "request_id"}
    assert body["error"]["request_id"] == "req-123" and r.headers["X-Request-ID"] == "req-123"
    assert client.get("/no/such/route").json()["error"]["code"] == "NOT_FOUND"


def test_health(client):
    r = client.get("/health").json()
    assert r["status"] == "ok" and r["database"] == "ok"


def test_admin_can_restore_a_deleted_course(app, db, creator):
    from tests.conftest import build_course
    admin = make_admin(app, db)
    ids = build_course(creator)
    creator.delete(f"/courses/{ids['course']}")
    assert creator.get("/courses").json() == []
    deleted = admin.get("/admin/courses?include_deleted=true").json()
    assert deleted[0]["deleted_at"] is not None
    assert admin.post(f"/admin/courses/{ids['course']}/restore").json()["status"] == "draft"
    assert len(creator.get("/courses").json()) == 1


def test_admin_counts_upload_problems_and_errors(app, db, creator):
    from workers.worker import drain
    from tests.test_documents_and_jobs import upload
    admin = make_admin(app, db)
    upload(creator, "fake.pdf", b"not a pdf")              # rejected at upload
    upload(creator, "virus.exe", b"MZ")                    # rejected at upload
    upload(creator, "broken.pdf", b"%PDF-1.7\nbroken")     # accepted, fails processing
    drain("w")
    stats = admin.get("/admin/stats").json()
    assert stats["uploads_rejected_24h"] == 2 and stats["uploads_failed_24h"] == 1 and stats["documents_failed"] == 1
    kinds = sorted(e["kind"] for e in admin.get("/admin/events").json())
    assert kinds == ["upload_failed", "upload_rejected", "upload_rejected"]
    assert creator.get("/admin/events").status_code == 403


def test_server_errors_are_counted(app, db, monkeypatch):
    admin = make_admin(app, db)
    from unboxed_api.services import learning
    monkeypatch.setattr(learning, "catalog", lambda *a, **k: 1 / 0)
    r = TestClient(app, raise_server_exceptions=False, cookies=admin.cookies).get("/catalog")
    assert r.status_code == 500 and r.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "ZeroDivisionError" not in r.text  # details stay in the log
    assert admin.get("/admin/stats").json()["server_errors_24h"] == 1
    assert admin.get("/admin/events?kind=server_error").json()[0]["path"] == "/catalog"
