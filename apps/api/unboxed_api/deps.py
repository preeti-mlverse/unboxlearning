"""Request dependencies: the database session and the signed-in person.

The access token is read from the `ub_access` cookie (set by /auth/login) or an `Authorization: Bearer`
header. It is always validated here, on the server; nothing the browser claims about roles is trusted."""
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .db import get_db
from .enums import UserStatus
from .errors import AppError
from .models import AuthSession, User
from .security import decode_access_token
from .services.permissions import P, Principal, load_principal

ACCESS_COOKIE = "ub_access"
REFRESH_COOKIE = "ub_refresh"

DB = Annotated[Session, Depends(get_db)]


def _token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get(ACCESS_COOKIE)


def optional_principal(request: Request, db: DB) -> Principal | None:
    token = _token(request)
    if not token:
        return None
    claims = decode_access_token(token)
    if not claims:
        raise AppError(401, "SESSION_EXPIRED", "Your session has expired. Please log in again.")
    session = db.get(AuthSession, claims.get("sid"))
    if session is None or session.revoked_at is not None:
        raise AppError(401, "SESSION_EXPIRED", "Your session has ended. Please log in again.")
    user = db.get(User, claims["sub"])
    if user is None or user.status != UserStatus.ACTIVE:
        raise AppError(401, "ACCOUNT_DISABLED", "This account isn't active. Contact support if you think this is wrong.")
    request.state.user_id = user.id
    return load_principal(db, user)


def current_principal(principal: Annotated[Principal | None, Depends(optional_principal)]) -> Principal:
    if principal is None:
        raise AppError(401, "UNAUTHENTICATED", "Please log in to continue.")
    return principal


def platform_admin(principal: Annotated[Principal, Depends(current_principal)]) -> Principal:
    principal.require(P.ADMIN_VIEW)
    return principal


Me = Annotated[Principal, Depends(current_principal)]
MaybeMe = Annotated[Principal | None, Depends(optional_principal)]
Admin = Annotated[Principal, Depends(platform_admin)]
