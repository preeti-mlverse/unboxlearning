"""Structured errors. Learners and creators only ever see a code and a plain message;
the detail (stack trace, SQL error) stays in the server log, linked by the request ID."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("unboxed.errors")


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details


def not_found(what: str = "That item") -> AppError:
    return AppError(404, "NOT_FOUND", f"{what} doesn't exist, or you don't have access to it.")


def forbidden(message: str = "You don't have permission to do that.") -> AppError:
    return AppError(403, "FORBIDDEN", message)


def bad_request(code: str, message: str, details: dict | None = None) -> AppError:
    return AppError(400, code, message, details)


def conflict(code: str, message: str) -> AppError:
    return AppError(409, code, message)


def _body(request: Request, code: str, message: str, details=None) -> dict:
    err = {"code": code, "message": message, "request_id": getattr(request.state, "request_id", None)}
    if details:
        err["details"] = details
    return {"error": err}


HTTP_CODES = {401: ("UNAUTHENTICATED", "Please log in to continue."), 403: ("FORBIDDEN", "You don't have permission to do that."),
              404: ("NOT_FOUND", "We couldn't find that."), 405: ("METHOD_NOT_ALLOWED", "That action isn't supported here."),
              413: ("FILE_TOO_LARGE", "That file is too large."), 429: ("RATE_LIMITED", "Too many attempts. Please wait a few minutes and try again.")}


def install(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        return JSONResponse(_body(request, exc.code, exc.message, exc.details), status_code=exc.status)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        code, message = HTTP_CODES.get(exc.status_code, ("ERROR", "Something went wrong."))
        if isinstance(exc.detail, str) and exc.status_code not in (404, 405):
            message = exc.detail
        return JSONResponse(_body(request, code, message), status_code=exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        fields = {}
        for e in exc.errors():
            loc = [str(p) for p in e.get("loc", []) if p not in ("body", "query", "path")]
            msg = e.get("msg", "Invalid value").removeprefix("Value error, ")
            if msg.startswith("value is not a valid email address"):
                msg = "Enter a valid email address."
            fields[".".join(loc) or "request"] = msg
        return JSONResponse(_body(request, "VALIDATION_FAILED", "Some fields need attention.", {"fields": fields}), status_code=422)

    @app.exception_handler(IntegrityError)
    async def integrity_error(request: Request, exc: IntegrityError):
        log.warning("integrity error: %s", exc.orig, extra={"request_id": getattr(request.state, "request_id", None)})
        return JSONResponse(_body(request, "CONFLICT", "That conflicts with something that already exists."), status_code=409)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        log.exception("unhandled error", extra={"request_id": getattr(request.state, "request_id", None)})
        return JSONResponse(_body(request, "INTERNAL_ERROR", "Something went wrong on our side. Please try again."), status_code=500)
