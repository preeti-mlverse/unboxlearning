"""Sign in with Google (OpenID Connect, authorization-code flow with PKCE).

Switched on by setting GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET. Google redirects back to
{OAUTH_REDIRECT_BASE}/auth/google/callback, which must be listed as an authorised redirect URI in Google Cloud.

Accounts are matched by Google's stable user id (stored as users.auth_user_id = "google:<sub>"). The first time,
a verified Google email that matches an existing account is linked to it; otherwise a new account is created,
just like the sign-up form (an educator gets a workspace, a learner doesn't)."""
import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlencode

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import utcnow
from ..errors import AppError
from ..models import Profile, User
from . import orgs

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
STATE_COOKIE = "ub_oauth"
INTENTS = {"learner", "educator", "school", "ngo", "organization"}


def enabled() -> bool:
    s = get_settings()
    return bool(s.google_client_id and s.google_client_secret)


def redirect_uri() -> str:
    return f"{get_settings().oauth_redirect_base.rstrip('/')}/auth/google/callback"


# ---- the short-lived state cookie: CSRF state + PKCE verifier + where to go afterwards, signed with the secret key
def _sign(payload: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    sig = hmac.new(get_settings().secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{sig}"


def _unsign(value: str | None) -> dict | None:
    try:
        body, sig = (value or "").rsplit(".", 1)
        good = hmac.new(get_settings().secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, good):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body.encode()))
        return payload if payload.get("exp", 0) > time.time() else None
    except (ValueError, json.JSONDecodeError):
        return None


def start(role: str | None, next_path: str | None) -> tuple[str, str]:
    """Returns (Google URL to send the browser to, value for the state cookie)."""
    if not enabled():
        raise AppError(404, "GOOGLE_DISABLED", "Google sign-in isn't switched on.")
    state, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    safe_next = next_path if next_path and next_path.startswith("/") and not next_path.startswith("//") else None
    cookie = _sign({"s": state, "v": verifier, "r": role if role in INTENTS else "learner", "n": safe_next,
                    "exp": int(time.time()) + 600})
    url = AUTH_URL + "?" + urlencode({
        "client_id": get_settings().google_client_id, "redirect_uri": redirect_uri(), "response_type": "code",
        "scope": "openid email profile", "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
        "prompt": "select_account"})
    return url, cookie


# ---- calls to Google (kept as small functions so tests can replace them)
def exchange_code(code: str, verifier: str) -> dict:
    s = get_settings()
    r = httpx.post(TOKEN_URL, data={"code": code, "client_id": s.google_client_id, "client_secret": s.google_client_secret,
                                    "redirect_uri": redirect_uri(), "grant_type": "authorization_code",
                                    "code_verifier": verifier}, timeout=10)
    if r.status_code != 200:
        raise AppError(400, "GOOGLE_FAILED", "Google didn't accept the sign-in. Please try again.")
    return r.json()


def fetch_userinfo(access_token: str) -> dict:
    r = httpx.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
    if r.status_code != 200:
        raise AppError(400, "GOOGLE_FAILED", "We couldn't read your Google profile. Please try again.")
    return r.json()


def finish(db: Session, code: str, state: str, cookie: str | None) -> tuple[User, str | None, bool]:
    """Complete the sign-in. Returns (user, next path, created)."""
    saved = _unsign(cookie)
    if not saved or not hmac.compare_digest(saved["s"], state or ""):
        raise AppError(400, "GOOGLE_STATE", "That sign-in took too long or was started elsewhere. Please try again.")
    info = fetch_userinfo(exchange_code(code, saved["v"])["access_token"])
    sub, email = info.get("sub"), (info.get("email") or "").strip().lower()
    if not sub or not email or not info.get("email_verified"):
        raise AppError(400, "GOOGLE_UNVERIFIED", "Your Google account's email isn't verified, so we can't use it here.")
    key = f"google:{sub}"
    user = db.scalar(select(User).where(User.auth_user_id == key))
    created = False
    if user is None:
        user = db.scalar(select(User).where(func.lower(User.email) == email))
        if user is not None and user.auth_user_id and user.auth_user_id != key:
            raise AppError(409, "ACCOUNT_LINKED", "This email is already linked to a different Google account.")
        if user is None:
            name = (info.get("name") or email.split("@")[0])[:120]
            user = User(email=email, password_hash=None, auth_user_id=key, email_verified_at=utcnow())
            user.profile = Profile(display_name=name, avatar_url=info.get("picture"), signup_intent=saved["r"])
            db.add(user)
            db.flush()
            if saved["r"] == "educator":
                orgs.create_workspace(db, user, orgs.default_workspace_name("educator", name, None), orgs.INTENT_TO_ORG["educator"])
            created = True
        else:
            user.auth_user_id = key  # link the existing account
    if user.status != "active":
        raise AppError(403, "ACCOUNT_DISABLED", "This account isn't active.")
    user.email_verified_at = user.email_verified_at or utcnow()  # Google has verified the address
    user.last_login_at = utcnow()
    return user, saved.get("n"), created
