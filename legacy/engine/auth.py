"""Accounts, sessions and the role-based dashboard.

Passwords are stored as salted PBKDF2-SHA256 hashes. A log-in sets an HttpOnly session cookie; only a SHA-256
of the session token is kept in the database, so a leaked database can't be used to log in.
Roles: 'educator' (creates and owns courses) and 'learner' (takes them). Schools, NGOs and organisations sign up
as educators with an organisation name.
"""
import hashlib
import hmac
import re
import secrets
import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from . import db

router = APIRouter(prefix="/api")
COOKIE = "ub_session"
SESSION_DAYS = 30
ITERATIONS = 200_000
EDUCATOR_ROLES = {"educator", "school", "ngo", "organization"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id TEXT PRIMARY KEY, email TEXT UNIQUE, name TEXT, phone TEXT, role TEXT, org TEXT, language TEXT,
  pw_hash TEXT, pw_salt TEXT, created_at REAL, last_login REAL);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id TEXT, created_at REAL, expires_at REAL);
CREATE TABLE IF NOT EXISTS course_owners(course_id TEXT PRIMARY KEY, user_id TEXT, created_at REAL);
CREATE INDEX IF NOT EXISTS ix_owner_user ON course_owners(user_id);
"""


def ensure_schema():
    with db.tx() as c:
        c.executescript(SCHEMA)


# ----------------------------------------------------------------------------- helpers

def _hash_pw(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS).hex()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _public(u: dict) -> dict:
    return {"id": u["id"], "email": u["email"], "name": u["name"], "phone": u["phone"], "role": u["role"],
            "org": u["org"], "language": u["language"], "is_educator": u["role"] in EDUCATOR_ROLES}


def current_user(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    row = db.conn().execute(
        "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash=? AND s.expires_at>?",
        (_token_hash(token), time.time())).fetchone()
    return dict(row) if row else None


def require_user(request: Request) -> dict:
    u = current_user(request)
    if not u:
        raise HTTPException(401, "Please log in")
    return u


def is_educator(u: dict) -> bool:
    return u["role"] in EDUCATOR_ROLES


def require_educator(request: Request) -> dict:
    u = require_user(request)
    if not is_educator(u):
        raise HTTPException(403, "This needs an educator account")
    return u


def _start_session(response: Response, request: Request, user_id: str, remember: bool):
    token = secrets.token_urlsafe(32)
    now = time.time()
    with db.tx() as c:
        c.execute("INSERT INTO sessions VALUES(?,?,?,?)", (_token_hash(token), user_id, now, now + SESSION_DAYS * 86400))
        c.execute("UPDATE users SET last_login=? WHERE id=?", (now, user_id))
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", path="/",
                        secure=request.url.scheme == "https", max_age=SESSION_DAYS * 86400 if remember else None)


def set_owner(course_id: str, user_id: str):
    with db.tx() as c:
        c.execute("INSERT OR IGNORE INTO course_owners VALUES(?,?,?)", (course_id, user_id, time.time()))


def owner_of(course_id: str) -> str | None:
    r = db.conn().execute("SELECT user_id FROM course_owners WHERE course_id=?", (course_id,)).fetchone()
    return r["user_id"] if r else None


# ----------------------------------------------------------------------------- endpoints

class SignupIn(BaseModel):
    name: str
    email: str
    password: str
    role: str = "learner"
    phone: str = ""
    org: str = ""
    language: str = "en"


class LoginIn(BaseModel):
    id: str            # email (or mobile number)
    password: str
    remember: bool = True


EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/auth/signup")
def signup(body: SignupIn, request: Request, response: Response):
    email = body.email.strip().lower()
    if len(body.name.strip()) < 2:
        raise HTTPException(400, "Please enter your full name")
    if not EMAIL.match(email):
        raise HTTPException(400, "Please enter a valid email")
    if len(body.password) < 8:
        raise HTTPException(400, "Use a password of at least 8 characters")
    role = body.role if body.role in EDUCATOR_ROLES | {"learner"} else "learner"
    phone = re.sub(r"\D", "", body.phone)[-10:]
    if db.conn().execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
        raise HTTPException(409, "An account with this email already exists. Try logging in.")
    salt = secrets.token_bytes(16)
    uid = db.new_id("usr")
    with db.tx() as c:
        c.execute("INSERT INTO users VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                  (uid, email, body.name.strip(), phone, role, body.org.strip(), body.language,
                   _hash_pw(body.password, salt), salt.hex(), time.time(), None))
        # the learner record lets the existing learning features (attempts, mastery) use the account id
        c.execute("INSERT OR IGNORE INTO learners VALUES(?,?,?)", (uid, body.name.strip(), time.time()))
    _start_session(response, request, uid, True)
    u = dict(db.conn().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone())
    return {"user": _public(u)}


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response):
    ident = body.id.strip().lower()
    digits = re.sub(r"\D", "", ident)[-10:]
    row = db.conn().execute("SELECT * FROM users WHERE email=? OR (phone<>'' AND phone=?)", (ident, digits)).fetchone()
    if not row or not hmac.compare_digest(_hash_pw(body.password, bytes.fromhex(row["pw_salt"])), row["pw_hash"]):
        raise HTTPException(401, "That email or password doesn't match")
    _start_session(response, request, row["id"], body.remember)
    return {"user": _public(dict(row))}


@router.post("/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE)
    if token:
        with db.tx() as c:
            c.execute("DELETE FROM sessions WHERE token_hash=?", (_token_hash(token),))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/auth/me")
def me(request: Request):
    u = current_user(request)
    return {"user": _public(u) if u else None}


class ResetIn(BaseModel):
    email: str


@router.post("/auth/reset")
def reset(body: ResetIn):
    # Sending reset emails needs an email service (not set up yet). Answer the same way whether or not the account
    # exists, so this can't be used to discover who has an account.
    return {"ok": True, "message": "If an account exists, a reset link will be sent once email is set up."}


# ----------------------------------------------------------------------------- dashboard

def _course_card(cid: str) -> dict | None:
    c = db.row(db.conn().execute("SELECT * FROM courses WHERE id=?", (cid,)).fetchone())
    if not c:
        return None
    bp = db.get_doc(cid, "micro") or {}
    mods = db.list_docs(cid, "module")
    learners = db.conn().execute("SELECT count(*) n FROM course_docs WHERE course_id=? AND kind='micro_state'", (cid,)).fetchone()["n"]
    return {"id": cid, "title": bp.get("course_title") or c["title"], "tagline": bp.get("tagline", ""),
            "status": c["status"], "outline": bp.get("status"), "cover": bp.get("cover_media"),
            "modules": len(bp.get("modules", [])), "cards": sum(len(m.get("cards", [])) for m in mods.values()),
            "published": c["data"]["settings"].get("published", False), "learners": learners,
            "updated_at": c["updated_at"]}


def _progress(cid: str, uid: str) -> dict | None:
    st = db.get_doc(cid, "micro_state", uid)
    if not st:
        return None
    bp = db.get_doc(cid, "micro") or {}
    total = len(bp.get("modules", [])) or 1
    done = sum(1 for m in st.get("modules", {}).values() if m.get("completed"))
    return {"modules_done": done, "modules_total": total, "percent": round(100 * done / total), "xp": st.get("xp", 0),
            "last_day": (st.get("days") or [None])[-1]}


@router.get("/dashboard")
def dashboard(request: Request):
    u = require_user(request)
    out = {"user": _public(u)}
    if u["role"] in EDUCATOR_ROLES:
        own = [r["course_id"] for r in db.conn().execute(
            "SELECT course_id FROM course_owners WHERE user_id=? ORDER BY created_at DESC", (u["id"],))]
        out["my_courses"] = [x for x in (_course_card(c) for c in own) if x]
        # courses built before accounts existed: shown so they can be claimed
        unowned = [r["id"] for r in db.conn().execute(
            "SELECT id FROM courses WHERE id NOT IN (SELECT course_id FROM course_owners) ORDER BY updated_at DESC")]
        out["unclaimed"] = [x for x in (_course_card(c) for c in unowned) if x and x["modules"]]
    started = [r["course_id"] for r in db.conn().execute(
        "SELECT course_id FROM course_docs WHERE kind='micro_state' AND key=? ORDER BY updated_at DESC", (u["id"],))]
    out["learning"] = [dict(card, progress=_progress(c, u["id"])) for c in started if (card := _course_card(c))]
    published = [r["id"] for r in db.conn().execute("SELECT id FROM courses ORDER BY updated_at DESC")]
    out["available"] = [x for x in (_course_card(c) for c in published)
                        if x and x["published"] and x["id"] not in started and x["modules"]]
    return out


@router.post("/courses/{cid}/claim")
def claim(cid: str, request: Request):
    u = require_educator(request)
    if owner_of(cid) not in (None, u["id"]):
        raise HTTPException(403, "This course belongs to another educator")
    set_owner(cid, u["id"])
    return {"ok": True}
