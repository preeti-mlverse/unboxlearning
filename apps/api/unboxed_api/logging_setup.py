"""JSON-lines logging plus a request middleware that records request ID, user, endpoint, status and time."""
import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

FIELDS = ("request_id", "user_id", "method", "path", "status", "duration_ms", "job_id", "job_type", "client")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out = {"ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
               "level": record.levelname, "logger": record.name, "msg": record.getMessage()}
        for f in FIELDS:
            v = getattr(record, f, None)
            if v is not None:
                out[f] = v
        if record.exc_info:
            out["error"] = self.formatException(record.exc_info)
        return json.dumps(out, default=str)


def configure(level: str = "INFO") -> None:
    root = logging.getLogger()
    if any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.handlers[:] = [handler]
    root.setLevel(level)
    logging.getLogger("uvicorn.access").disabled = True  # our middleware logs requests instead


access = logging.getLogger("unboxed.request")


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request.state.request_id = rid
        request.state.user_id = None
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            access.info("request", extra={
                "request_id": rid, "user_id": getattr(request.state, "user_id", None), "method": request.method,
                "path": request.url.path, "status": status, "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                "client": request.client.host if request.client else None})
