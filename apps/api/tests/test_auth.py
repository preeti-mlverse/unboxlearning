from fastapi.testclient import TestClient

from unboxed_api.config import get_settings
from tests.conftest import PASSWORD, outbox_token, signup


def test_educator_signup_creates_workspace_and_session(app):
    c = signup(app, "educator", name="Asha Rao")
    me = c.get("/users/me").json()
    assert me["home"] == "create"
    assert me["memberships"][0]["organization_name"] == "Asha's workspace"
    assert set(me["memberships"][0]["roles"]) == {"creator", "org_admin"}
    assert me["email_verified"] is False


def test_school_signup_uses_given_name(app):
    me = signup(app, "school", org="Green Valley School").me
    assert me["memberships"][0]["organization_type"] == "school"
    assert me["memberships"][0]["organization_name"] == "Green Valley School"


def test_org_signup_without_name_goes_to_onboarding(app):
    c = signup(app, "organization")
    assert c.me["home"] == "onboarding"
    r = c.post("/organizations", json={"name": "Acme Training", "type": "company"})
    assert r.status_code == 201
    assert c.get("/users/me").json()["home"] == "create"


def test_learner_signup_has_no_workspace(learner):
    me = learner.get("/users/me").json()
    assert me["home"] == "learn" and me["memberships"] == []


def test_signup_validation_and_duplicates(app, client):
    bad = client.post("/auth/signup", json={"name": "A", "email": "nope", "password": "short", "agree": False})
    assert bad.status_code == 422
    fields = bad.json()["error"]["details"]["fields"]
    assert {"name", "email", "password", "agree"} <= set(fields)
    c = signup(app, "learner", email="dup@example.com")
    again = client.post("/auth/signup", json={"name": "Dup", "email": "DUP@example.com", "password": PASSWORD,
                                              "agree": True})
    assert again.status_code == 409 and again.json()["error"]["code"] == "EMAIL_TAKEN"
    assert c.me["email"] == "dup@example.com"


def test_login_with_email_or_mobile(app):
    signup(app, "learner", email="ravi@example.com", phone="9876543210")
    c = TestClient(app)
    assert c.post("/auth/login", json={"identifier": "RAVI@example.com", "password": PASSWORD}).status_code == 200
    c2 = TestClient(app)
    r = c2.post("/auth/login", json={"identifier": "+91 98765 43210", "password": PASSWORD})
    assert r.status_code == 200 and r.json()["redirect_to"].endswith("/learn")
    assert c2.get("/users/me").status_code == 200


def test_wrong_password_and_unknown_user_look_the_same(app, client):
    signup(app, "learner", email="ravi@example.com")
    a = client.post("/auth/login", json={"identifier": "ravi@example.com", "password": "wrong-pass1"})
    b = client.post("/auth/login", json={"identifier": "ghost@example.com", "password": "wrong-pass1"})
    assert a.status_code == b.status_code == 401
    assert a.json()["error"]["code"] == b.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_unauthenticated_and_session_expired(client):
    r = client.get("/users/me")
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHENTICATED"
    r = client.get("/users/me", headers={"Authorization": "Bearer not-a-token"})
    assert r.json()["error"]["code"] == "SESSION_EXPIRED"


def test_refresh_rotates_and_logout_revokes(learner):
    old_refresh = learner.cookies.get("ub_refresh")
    assert learner.post("/auth/refresh").status_code == 200
    assert learner.cookies.get("ub_refresh") != old_refresh
    stale = TestClient(learner.app, cookies={"ub_refresh": old_refresh})
    assert stale.post("/auth/refresh").status_code == 401  # a rotated token can't be reused
    access = learner.cookies.get("ub_access")
    assert learner.post("/auth/logout").status_code == 200
    # the old access token stops working at once, because its session is revoked
    assert TestClient(learner.app).get("/users/me", headers={"Authorization": f"Bearer {access}"}).status_code == 401


def test_email_verification(learner):
    token = outbox_token("verify")
    assert learner.post("/auth/verify-email", json={"token": token}).status_code == 200
    assert learner.get("/users/me").json()["email_verified"] is True
    again = learner.post("/auth/verify-email", json={"token": token})
    assert again.status_code == 400 and again.json()["error"]["code"] == "TOKEN_INVALID"


def test_password_reset_logs_out_everywhere(app, client):
    c = signup(app, "learner", email="ravi@example.com")
    assert client.post("/auth/forgot-password", json={"email": "ravi@example.com"}).status_code == 200
    # unknown addresses get the same answer
    assert client.post("/auth/forgot-password", json={"email": "ghost@example.com"}).status_code == 200
    token = outbox_token("reset")
    assert client.post("/auth/reset-password", json={"token": token, "password": "newpass99"}).status_code == 200
    assert c.get("/users/me").status_code == 401  # old session gone
    assert client.post("/auth/login", json={"identifier": "ravi@example.com", "password": PASSWORD}).status_code == 401
    assert client.post("/auth/login", json={"identifier": "ravi@example.com", "password": "newpass99"}).status_code == 200


def test_login_rate_limit(app, client):
    signup(app, "learner", email="ravi@example.com")
    codes = [client.post("/auth/login", json={"identifier": "ravi@example.com", "password": "bad-guess1"}).status_code
             for _ in range(get_settings().auth_rate_limit + 1)]
    assert codes[-1] == 429


def test_profile_update(learner):
    r = learner.patch("/users/me", json={"display_name": "Ravi K", "preferred_language": "hi"})
    assert r.json()["profile"]["display_name"] == "Ravi K" and r.json()["profile"]["preferred_language"] == "hi"


def test_cors_allows_site_only(client):
    ok = client.options("/auth/login", headers={"Origin": get_settings().site_url, "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == get_settings().site_url
    bad = client.options("/auth/login", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad.headers
