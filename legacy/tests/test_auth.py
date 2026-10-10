"""Accounts and dashboard, run against a throwaway database in a separate process."""
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPT = textwrap.dedent("""
    from fastapi.testclient import TestClient
    from engine.api import app
    from engine import db, pipeline as P

    edu, lrn, other = TestClient(app), TestClient(app), TestClient(app)

    # sign-up validates input and refuses duplicate emails
    assert edu.post("/api/auth/signup", json={"name": "A", "email": "a@x.in", "password": "longenough"}).status_code == 400
    assert edu.post("/api/auth/signup", json={"name": "Asha Rao", "email": "bad", "password": "longenough"}).status_code == 400
    assert edu.post("/api/auth/signup", json={"name": "Asha Rao", "email": "asha@x.in", "password": "short"}).status_code == 400
    r = edu.post("/api/auth/signup", json={"name": "Asha Rao", "email": "Asha@X.in", "password": "longenough",
                                            "role": "educator", "phone": "98765 43210", "org": "Sunrise School"})
    assert r.status_code == 200 and r.json()["user"]["is_educator"], r.text
    assert edu.post("/api/auth/signup", json={"name": "Asha Two", "email": "asha@x.in", "password": "longenough"}).status_code == 409

    # the session cookie identifies the user; passwords are never returned or stored in plain text
    me = edu.get("/api/auth/me").json()["user"]
    assert me["email"] == "asha@x.in" and "pw_hash" not in me
    row = db.conn().execute("SELECT pw_hash FROM users WHERE email='asha@x.in'").fetchone()
    assert row["pw_hash"] != "longenough" and len(row["pw_hash"]) == 64

    # log-in by email or by mobile number; wrong password refused
    assert other.post("/api/auth/login", json={"id": "asha@x.in", "password": "nope-nope"}).status_code == 401
    assert other.post("/api/auth/login", json={"id": "9876543210", "password": "longenough"}).status_code == 200
    other.post("/api/auth/logout")
    assert other.get("/api/auth/me").json()["user"] is None
    assert other.get("/api/dashboard").status_code == 401

    # a course created while logged in belongs to that educator and shows on the dashboard
    c = edu.post("/api/courses", json={"title": "Water cycle", "source_ids": []}).json()
    db.put_doc(c["id"], "micro", {"course_title": "Water cycle", "modules": [{"id": "m1"}, {"id": "m2"}], "status": "ready"})
    P.update_course(c["id"], settings={"published": True})
    d = edu.get("/api/dashboard").json()
    assert [x["id"] for x in d["my_courses"]] == [c["id"]] and d["my_courses"][0]["modules"] == 2

    # a learner sees published courses, then their own progress once they start
    lrn.post("/api/auth/signup", json={"name": "Ravi K", "email": "ravi@x.in", "password": "learner123"})
    d = lrn.get("/api/dashboard").json()
    assert "my_courses" not in d and [x["id"] for x in d["available"]] == [c["id"]]
    lid = lrn.get("/api/auth/me").json()["user"]["id"]
    db.put_doc(c["id"], "micro_state", {"cards": {}, "modules": {"m1": {"completed": True}}, "xp": 40, "days": ["2026-10-04"]}, lid)
    d = lrn.get("/api/dashboard").json()
    assert d["learning"][0]["progress"]["percent"] == 50 and d["learning"][0]["progress"]["xp"] == 40 and not d["available"]

    # learners can't claim or create courses
    assert lrn.post(f"/api/courses/{c['id']}/claim").status_code == 403
    assert lrn.post("/api/courses", json={"title": "Nope", "source_ids": []}).status_code == 403
    print("AUTH OK")
""")


def test_accounts_and_dashboard():
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, DATA_DIR=tmp, LLM_PROVIDER="mock")
        r = subprocess.run([sys.executable, "-c", SCRIPT], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
        assert "AUTH OK" in r.stdout, r.stdout + r.stderr
