import re
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from unboxed_api.config import get_settings
from unboxed_api.services import google
from tests.conftest import outbox_token, signup


def latest_code() -> str:
    box = sorted((get_settings().storage_dir / "outbox").glob("*.txt"), key=lambda p: p.name, reverse=True)
    for f in box:
        m = re.search(r"confirmation code is:\s+(\d{6})", f.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    raise AssertionError("no code email")


@pytest.fixture
def required(monkeypatch):
    monkeypatch.setattr(get_settings(), "require_email_verification", True)


def test_signup_email_has_code_and_link(learner):
    assert re.fullmatch(r"\d{6}", latest_code())
    assert outbox_token("verify")


def test_unverified_people_can_only_confirm(app, required):
    c = signup(app, "educator")
    assert c.me["verification_required"] is True and c.me["email_verified"] is False
    r = c.get("/courses")
    assert r.status_code == 403 and r.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"
    assert c.get("/users/me").status_code == 200  # still allowed
    # log-in works (so they can enter the code) and sends them to the confirm screen
    again = TestClient(app).post("/auth/login", json={"identifier": c.email, "password": "learn1234"})
    assert again.status_code == 200 and again.json()["redirect_to"].endswith("/verify-email")
    assert c.post("/auth/verify-email-code", json={"code": latest_code()}).status_code == 200
    assert c.get("/courses").status_code == 200
    assert c.get("/users/me").json()["email_verified"] is True


def test_wrong_codes_run_out(app, required):
    c = signup(app, "learner")
    good = latest_code()
    bad = "000000" if good != "000000" else "111111"
    messages = [c.post("/auth/verify-email-code", json={"code": bad}).json()["error"] for _ in range(5)]
    assert messages[0]["code"] == "CODE_WRONG" and "4 tries left" in messages[0]["message"]
    assert messages[-1]["code"] == "CODE_EXPIRED"
    assert c.post("/auth/verify-email-code", json={"code": good}).json()["error"]["code"] == "CODE_EXPIRED"
    assert c.post("/auth/resend-verification").status_code == 200
    assert c.post("/auth/verify-email-code", json={"code": latest_code()}).status_code == 200


def test_code_format_is_checked(learner):
    assert learner.post("/auth/verify-email-code", json={"code": "12ab"}).status_code == 422


# ---------------------------------------------------------------- Google
@pytest.fixture
def google_on(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "google_client_id", "test-client.apps.googleusercontent.com")
    monkeypatch.setattr(s, "google_client_secret", "test-secret")
    profile = {"sub": "1234567890", "email": "asha.g@example.com", "email_verified": True, "name": "Asha G"}
    monkeypatch.setattr(google, "exchange_code", lambda code, verifier: {"access_token": "at-" + code})
    monkeypatch.setattr(google, "fetch_userinfo", lambda token: dict(profile))
    return profile


def google_login(app, role="learner", state_override=None):
    c = TestClient(app, follow_redirects=False)
    start = c.get(f"/auth/google/start?role={role}")
    assert start.status_code == 302
    q = parse_qs(urlparse(start.headers["location"]).query)
    assert q["redirect_uri"] == [get_settings().oauth_redirect_base + "/auth/google/callback"]
    assert q["code_challenge_method"] == ["S256"]
    cb = c.get(f"/auth/google/callback?code=abc&state={state_override or q['state'][0]}")
    return c, cb


def test_google_disabled_by_default(client):
    assert client.get("/auth/providers").json() == {"google": False}
    assert client.get("/auth/google/start", follow_redirects=False).status_code == 404


def test_google_creates_educator_with_workspace(app, google_on):
    assert TestClient(app).get("/auth/providers").json() == {"google": True}
    c, cb = google_login(app, role="educator")
    assert cb.status_code == 302 and cb.headers["location"].endswith("/create?welcome=1")
    me = c.get("/users/me").json()
    assert me["email"] == "asha.g@example.com" and me["email_verified"] is True
    assert me["memberships"][0]["organization_name"] == "Asha's workspace"
    # second time: same account, no new workspace
    c2, cb2 = google_login(app, role="educator")
    assert cb2.headers["location"].endswith("/create")
    assert len(c2.get("/users/me").json()["memberships"]) == 1


def test_google_links_existing_password_account(app, google_on):
    existing = signup(app, "learner", email="asha.g@example.com")
    c, cb = google_login(app)
    assert c.get("/users/me").json()["id"] == existing.me["id"]


def test_google_rejects_bad_state_and_unverified_email(app, google_on, monkeypatch):
    _, cb = google_login(app, state_override="forged")
    assert cb.headers["location"].endswith("/login?error=google_state")
    monkeypatch.setattr(google, "fetch_userinfo", lambda t: {**google_on, "email_verified": False})
    _, cb = google_login(app)
    assert cb.headers["location"].endswith("/login?error=google_unverified")
