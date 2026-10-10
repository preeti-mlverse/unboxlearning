"""Passwords (Argon2id), short-lived access tokens (JWT) and opaque single-use tokens (stored only as hashes)."""
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from .config import get_settings

_hasher = PasswordHasher()
# verified against when the account doesn't exist, so a wrong email takes as long as a wrong password
_DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def new_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_code() -> str:
    """A 6-digit one-time code for people to type in (leading zeros allowed)."""
    return f"{secrets.randbelow(1_000_000):06d}"


def code_digest(user_id: str, code: str) -> str:
    # keyed by the user and the server secret, so a leaked table can't be brute-forced offline
    return hmac.new(get_settings().secret_key.encode(), f"{user_id}:{code}".encode(), hashlib.sha256).hexdigest()


def create_access_token(user_id: str, session_id: str) -> tuple[str, datetime]:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.access_token_minutes)
    token = jwt.encode({"sub": user_id, "sid": session_id, "exp": exp, "typ": "access"}, s.secret_key, algorithm="HS256")
    return token, exp


def decode_access_token(token: str) -> dict | None:
    try:
        claims = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return claims if claims.get("typ") == "access" else None


# ---- signed file URLs: /files/{token} works for a few minutes, for one document, without a session
def sign_file_token(document_id: str, seconds: int | None = None) -> str:
    exp = int(time.time()) + (seconds or get_settings().signed_url_seconds)
    msg = f"{document_id}.{exp}"
    sig = hmac.new(get_settings().secret_key.encode(), msg.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{msg}.{sig}"


def verify_file_token(token: str) -> str | None:
    try:
        document_id, exp, sig = token.rsplit(".", 2)
        msg = f"{document_id}.{exp}"
        good = hmac.new(get_settings().secret_key.encode(), msg.encode(), hashlib.sha256).hexdigest()[:32]
        if hmac.compare_digest(sig, good) and int(exp) >= time.time():
            return document_id
    except ValueError:
        pass
    return None
