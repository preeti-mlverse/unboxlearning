"""/auth: sign up, log in, log out, refresh, verify email, forgot/reset password.

The marketing site (unboxlearning.in/signup, /login) and the app both call these. Sessions are HttpOnly cookies,
so tokens are never readable by page scripts."""
from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import RedirectResponse

from ..deps import DB, REFRESH_COOKIE, Me
from ..schemas import AuthOut, ChangePasswordIn, CodeIn, EmailIn, LoginIn, Ok, ResetPasswordIn, SignupIn, TokenIn
from ..config import get_settings
from ..errors import AppError
from ..services import accounts, google, ratelimit
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


@router.get("/providers")
def providers():
    """Which extra sign-in options are switched on (the app and site show buttons only for these)."""
    return {"google": google.enabled()}


@router.get("/google/start", include_in_schema=False)
def google_start(request: Request, role: str | None = Query(None, max_length=20), next: str | None = Query(None, max_length=300)):
    ratelimit.check("google", _ip(request))
    url, cookie = google.start(role, next)
    resp = RedirectResponse(url, status_code=302)
    s = get_settings()
    resp.set_cookie(google.STATE_COOKIE, cookie, max_age=600, httponly=True, secure=s.cookie_secure, samesite="lax", path="/")
    return resp


@router.get("/google/callback", include_in_schema=False)
def google_callback(request: Request, db: DB, code: str | None = None, state: str | None = None, error: str | None = None):
    app = get_settings().app_url
    if error or not code:
        return RedirectResponse(f"{app}/login?error=google_cancelled", status_code=302)
    try:
        user, next_path, created = google.finish(db, code, state or "", request.cookies.get(google.STATE_COOKIE))
    except AppError as e:
        return RedirectResponse(f"{app}/login?error={e.code.lower()}", status_code=302)
    resp = RedirectResponse(app, status_code=302)
    accounts.start_session(db, user, resp, request, remember=True)
    me = accounts.me(db, load_principal(db, user))
    target = accounts.redirect_for(me)
    if next_path and not accounts.must_verify(me):
        target = app + next_path
    elif created:
        target += "?welcome=1"
    resp.headers["location"] = target
    resp.delete_cookie(google.STATE_COOKIE, path="/")
    return resp


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


@router.post("/verify-email-code", response_model=Ok)
def verify_email_code(data: CodeIn, me: Me, request: Request, db: DB):
    """Confirm the signed-in person's email with the 6-digit code from their inbox."""
    ratelimit.check("code", _ip(request), me.id)
    accounts.verify_email_code(db, me.user, data.code)
    return Ok(message="Your email is confirmed.")


@router.post("/resend-verification", response_model=Ok)
def resend_verification(me: Me, request: Request, db: DB):
    ratelimit.check("resend", _ip(request), me.id)
    accounts.send_verification(db, me.user)
    return Ok(message="We've sent a new code to your email.")


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
