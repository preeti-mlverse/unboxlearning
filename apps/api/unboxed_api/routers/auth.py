"""/auth: sign up, log in, log out, refresh, verify email, forgot/reset password.

The marketing site (unboxlearning.in/signup, /login) and the app both call these. Sessions are HttpOnly cookies,
so tokens are never readable by page scripts."""
from fastapi import APIRouter, Request, Response

from ..deps import DB, REFRESH_COOKIE, Me
from ..schemas import AuthOut, ChangePasswordIn, EmailIn, LoginIn, Ok, ResetPasswordIn, SignupIn, TokenIn
from ..services import accounts, ratelimit
from ..services.permissions import load_principal

router = APIRouter(prefix="/auth", tags=["auth"])


def _ip(request: Request) -> str:
    return request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "")


def _auth_out(db, user, message=None) -> AuthOut:
    me = accounts.me(db, load_principal(db, user))
    return AuthOut(user=me, redirect_to=accounts.redirect_for(me), message=message)


@router.post("/signup", response_model=AuthOut, status_code=201)
def signup(data: SignupIn, request: Request, response: Response, db: DB):
    ratelimit.check("signup", _ip(request))
    user = accounts.signup(db, data)
    accounts.start_session(db, user, response, request, remember=True)
    return _auth_out(db, user, "Account created. We've sent a link to confirm your email.")


@router.post("/login", response_model=AuthOut)
def login(data: LoginIn, request: Request, response: Response, db: DB):
    ratelimit.check("login", _ip(request), data.identifier)
    user = accounts.authenticate(db, data.identifier, data.password)
    accounts.start_session(db, user, response, request, remember=data.remember)
    return _auth_out(db, user)


@router.post("/refresh", response_model=AuthOut)
def refresh(request: Request, response: Response, db: DB):
    user = accounts.refresh_session(db, request.cookies.get(REFRESH_COOKIE), response)
    return _auth_out(db, user)


@router.post("/logout", response_model=Ok)
def logout(request: Request, response: Response, db: DB):
    accounts.end_session(db, request.cookies.get(REFRESH_COOKIE), response)
    return Ok(message="You're logged out.")


@router.post("/logout-everywhere", response_model=Ok)
def logout_everywhere(me: Me, response: Response, db: DB):
    accounts.revoke_all(db, me.id)
    accounts.clear_cookies(response)
    return Ok(message="You're logged out on every device.")


@router.post("/verify-email", response_model=Ok)
def verify_email(data: TokenIn, db: DB):
    accounts.verify_email(db, data.token)
    return Ok(message="Your email is confirmed.")


@router.post("/resend-verification", response_model=Ok)
def resend_verification(me: Me, request: Request, db: DB):
    ratelimit.check("resend", _ip(request), me.id)
    accounts.send_verification(db, me.user)
    return Ok(message="We've sent a new confirmation link.")


@router.post("/forgot-password", response_model=Ok)
def forgot_password(data: EmailIn, request: Request, db: DB):
    ratelimit.check("forgot", _ip(request), data.email)
    accounts.forgot_password(db, data.email)
    return Ok(message="If an account uses that email, we've sent a link to reset the password.")


@router.post("/reset-password", response_model=Ok)
def reset_password(data: ResetPasswordIn, request: Request, db: DB):
    ratelimit.check("reset", _ip(request))
    accounts.reset_password(db, data.token, data.password)
    return Ok(message="Your password is changed. Log in with the new one.")


@router.post("/change-password", response_model=Ok)
def change_password(data: ChangePasswordIn, me: Me, db: DB):
    accounts.change_password(db, me.user, data.current_password, data.new_password)
    return Ok(message="Your password is changed.")
