"""Sign-up, log-in, sessions, email verification and password reset."""
from datetime import timedelta

from fastapi import Request, Response
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import utcnow
from ..deps import ACCESS_COOKIE, REFRESH_COOKIE
from ..enums import MembershipStatus, Role, TokenPurpose, UserStatus
from ..errors import AppError, conflict
from ..models import AuthSession, AuthToken, Membership, Organization, Profile, User
from ..schemas import MembershipOut, MeOut, ProfileOut, SignupIn
from ..security import (create_access_token, hash_password, needs_rehash, new_opaque_token, token_digest,
                        verify_password)
from . import mailer, orgs
from .permissions import Principal

TOKEN_LIFETIME = {TokenPurpose.VERIFY_EMAIL: timedelta(hours=48), TokenPurpose.RESET_PASSWORD: timedelta(hours=1)}


def normalise_email(email: str) -> str:
    return email.strip().lower()


# ---------------------------------------------------------------- sign-up
def signup(db: Session, data: SignupIn) -> User:
    email = normalise_email(data.email)
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise conflict("EMAIL_TAKEN", "An account with this email already exists. Log in, or reset your password.")
    if data.phone and db.scalar(select(User.id).where(User.phone == data.phone)):
        raise conflict("PHONE_TAKEN", "This mobile number is already linked to an account.")
    user = User(email=email, phone=data.phone, password_hash=hash_password(data.password), last_login_at=utcnow())
    user.profile = Profile(display_name=data.name, preferred_language=data.language, signup_intent=data.role)
    db.add(user)
    db.flush()
    if data.role in orgs.INTENT_TO_ORG:
        name = orgs.default_workspace_name(data.role, data.name, data.org)
        if name:
            orgs.create_workspace(db, user, name, orgs.INTENT_TO_ORG[data.role])
    send_verification(db, user)
    return user


def issue_token(db: Session, user: User, purpose: TokenPurpose) -> str:
    # an older unused token of the same kind stops working once a new one is issued
    db.execute(update(AuthToken).where(AuthToken.user_id == user.id, AuthToken.purpose == purpose,
                                       AuthToken.used_at.is_(None)).values(used_at=utcnow()))
    raw = new_opaque_token()
    db.add(AuthToken(user_id=user.id, purpose=purpose, token_hash=token_digest(raw),
                     expires_at=utcnow() + TOKEN_LIFETIME[purpose]))
    db.flush()
    return raw


def consume_token(db: Session, raw: str, purpose: TokenPurpose) -> User:
    tok = db.scalar(select(AuthToken).where(AuthToken.token_hash == token_digest(raw), AuthToken.purpose == purpose))
    if tok is None or tok.used_at is not None or tok.expires_at < utcnow():
        what = "verification" if purpose == TokenPurpose.VERIFY_EMAIL else "reset"
        raise AppError(400, "TOKEN_INVALID", f"This {what} link has expired or was already used. Ask for a new one.")
    tok.used_at = utcnow()
    return db.get(User, tok.user_id)


def send_verification(db: Session, user: User) -> None:
    if user.email_verified_at:
        return
    mailer.verification_email(user.email, user.profile.display_name, issue_token(db, user, TokenPurpose.VERIFY_EMAIL))


def verify_email(db: Session, raw: str) -> User:
    user = consume_token(db, raw, TokenPurpose.VERIFY_EMAIL)
    user.email_verified_at = user.email_verified_at or utcnow()
    return user


def forgot_password(db: Session, email: str) -> None:
    """Always looks the same from outside, whether or not the account exists."""
    user = db.scalar(select(User).where(func.lower(User.email) == normalise_email(email)))
    if user and user.status == UserStatus.ACTIVE:
        mailer.reset_email(user.email, user.profile.display_name, issue_token(db, user, TokenPurpose.RESET_PASSWORD))


def reset_password(db: Session, raw: str, password: str) -> User:
    user = consume_token(db, raw, TokenPurpose.RESET_PASSWORD)
    user.password_hash = hash_password(password)
    user.email_verified_at = user.email_verified_at or utcnow()  # they proved they can read the inbox
    revoke_all(db, user.id)  # a reset logs out every other device
    return user


def change_password(db: Session, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.password_hash):
        raise AppError(400, "WRONG_PASSWORD", "Your current password isn't right.")
    user.password_hash = hash_password(new)


# ---------------------------------------------------------------- log-in and sessions
def authenticate(db: Session, identifier: str, password: str) -> User:
    ident = identifier.strip().lower()
    digits = "".join(ch for ch in ident if ch.isdigit())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    cond = func.lower(User.email) == ident
    if "@" not in ident and len(digits) == 10:
        cond = or_(cond, User.phone == digits)
    user = db.scalar(select(User).where(cond))
    if not verify_password(password, user.password_hash if user else None):
        raise AppError(401, "INVALID_CREDENTIALS", "That email/mobile and password don't match.")
    if user.status != UserStatus.ACTIVE:
        raise AppError(403, "ACCOUNT_DISABLED", "This account isn't active. Contact support if you think this is wrong.")
    if get_settings().require_email_verification and not user.email_verified_at:
        raise AppError(403, "EMAIL_NOT_VERIFIED", "Please confirm your email first. We've sent you a link.")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = utcnow()
    return user


def _refresh_lifetime(remember: bool) -> timedelta:
    s = get_settings()
    return timedelta(days=s.refresh_token_days if remember else s.refresh_token_days_short)


def start_session(db: Session, user: User, response: Response, request: Request, remember: bool = True) -> None:
    raw = new_opaque_token()
    session = AuthSession(user_id=user.id, refresh_hash=token_digest(raw), remember=remember,
                          expires_at=utcnow() + _refresh_lifetime(remember),
                          user_agent=(request.headers.get("user-agent") or "")[:300],
                          ip=request.client.host if request.client else None)
    db.add(session)
    db.flush()
    _set_cookies(response, user.id, session, raw)


def refresh_session(db: Session, raw: str | None, response: Response) -> User:
    session = db.scalar(select(AuthSession).where(AuthSession.refresh_hash == token_digest(raw or "")))
    if session is None or session.revoked_at is not None or session.expires_at < utcnow():
        clear_cookies(response)
        raise AppError(401, "SESSION_EXPIRED", "Your session has expired. Please log in again.")
    user = db.get(User, session.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise AppError(401, "ACCOUNT_DISABLED", "This account isn't active.")
    new_raw = new_opaque_token()  # rotate: the old refresh token stops working
    session.refresh_hash = token_digest(new_raw)
    session.last_used_at = utcnow()
    _set_cookies(response, user.id, session, new_raw)
    return user


def end_session(db: Session, raw: str | None, response: Response) -> None:
    if raw:
        db.execute(update(AuthSession).where(AuthSession.refresh_hash == token_digest(raw))
                   .values(revoked_at=utcnow()))
    clear_cookies(response)


def revoke_all(db: Session, user_id: str) -> None:
    db.execute(update(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
               .values(revoked_at=utcnow()))


def _cookie_args() -> dict:
    s = get_settings()
    args = {"httponly": True, "secure": s.cookie_secure, "samesite": "lax", "path": "/"}
    if s.cookie_domain:
        args["domain"] = s.cookie_domain
    return args


def _set_cookies(response: Response, user_id: str, session: AuthSession, refresh_raw: str) -> None:
    access, _ = create_access_token(user_id, session.id)
    args = _cookie_args()
    response.set_cookie(ACCESS_COOKIE, access, max_age=get_settings().access_token_minutes * 60, **args)
    refresh_age = int(_refresh_lifetime(session.remember).total_seconds()) if session.remember else None
    response.set_cookie(REFRESH_COOKIE, refresh_raw, max_age=refresh_age, **args)
    # a non-secret hint the marketing site can read to show "Go to your dashboard" instead of "Log in"
    response.set_cookie("ub_signed_in", "1", max_age=refresh_age, **{**args, "httponly": False})


def clear_cookies(response: Response) -> None:
    args = _cookie_args()
    response.delete_cookie(ACCESS_COOKIE, **args)
    response.delete_cookie(REFRESH_COOKIE, **args)
    response.delete_cookie("ub_signed_in", **{**args, "httponly": False})


# ---------------------------------------------------------------- "who am I"
def me(db: Session, principal: Principal) -> MeOut:
    user = principal.user
    rows = db.execute(select(Organization, Membership.role).join(Membership, Membership.organization_id == Organization.id)
                      .where(Membership.user_id == user.id, Membership.status == MembershipStatus.ACTIVE)
                      .order_by(Organization.created_at)).all()
    by_org: dict[str, MembershipOut] = {}
    for org, role in rows:
        m = by_org.setdefault(org.id, MembershipOut(organization_id=org.id, organization_name=org.name,
                                                    organization_slug=org.slug, organization_type=org.type, roles=[]))
        m.roles.append(Role(role))
    memberships = list(by_org.values())
    intent = user.profile.signup_intent or "learner"
    if any(Role.CREATOR in m.roles for m in memberships):
        home = "create"
    elif intent in orgs.INTENT_TO_ORG:
        home = "onboarding"  # wants to create but has no workspace yet
    elif user.is_platform_admin and not memberships:
        home = "admin"
    else:
        home = "learn"
    return MeOut(id=user.id, email=user.email, phone=user.phone, email_verified=user.email_verified_at is not None,
                 is_platform_admin=user.is_platform_admin, profile=ProfileOut.model_validate(user.profile),
                 memberships=memberships, home=home)


HOME_PATHS = {"create": "/create", "learn": "/learn", "onboarding": "/onboarding", "admin": "/admin"}


def redirect_for(me_out: MeOut) -> str:
    return get_settings().app_url + HOME_PATHS[me_out.home]
