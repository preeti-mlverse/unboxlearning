"""Count what goes wrong: server errors, rejected uploads and documents that fail processing.

Events are written in their own short transaction, so they're kept even when the request that hit the problem
is rolled back. Recording must never cause a second failure, so any error here is only logged."""
import logging

from ..db import session_factory
from ..models import SystemEvent

log = logging.getLogger("unboxed.events")

SERVER_ERROR = "server_error"
UPLOAD_REJECTED = "upload_rejected"  # refused at upload: wrong type, too big, empty, damaged
UPLOAD_FAILED = "upload_failed"  # accepted, then failed while being processed

UPLOAD_CODES = {"FILE_TYPE_NOT_ALLOWED", "FILE_TOO_LARGE", "FILE_EMPTY", "FILE_CONTENT_MISMATCH", "DOCUMENT_UPLOAD_FAILED"}


def record(kind: str, code: str, message: str | None = None, *, path: str | None = None,
           request_id: str | None = None, user_id: str | None = None) -> None:
    try:
        with session_factory()() as db:
            db.add(SystemEvent(kind=kind, code=code[:60], message=(message or "")[:2000] or None, path=(path or "")[:300] or None,
                               request_id=request_id, user_id=user_id))
            db.commit()
    except Exception:  # noqa: BLE001
        log.exception("could not record system event %s/%s", kind, code)
