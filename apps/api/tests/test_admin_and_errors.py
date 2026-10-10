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
