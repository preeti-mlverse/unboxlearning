"""Job handlers. Each is registered by job type and runs only inside the worker process.

Foundation has one: `document.inspect` opens an uploaded file, confirms it is readable and records its size in
pages/slides. Wave 1 replaces this with real ingestion (parsing, sections, chunks), which plugs in as a new
handler without changing the upload flow, the jobs table or the app's progress UI."""
import zipfile

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from unboxed_api.db import utcnow
from unboxed_api.enums import DocumentStatus
from unboxed_api.models import Document
from unboxed_api.services import events
from unboxed_api.services.jobs import PermanentError, handler, on_failure
from unboxed_api.services.storage import get_storage


def _count_units(path, mime: str) -> int | None:
    if mime == "application/pdf":
        try:
            reader = PdfReader(str(path))
            if reader.is_encrypted:
                raise PermanentError("This PDF is password-protected. Upload a version without a password.")
            return len(reader.pages)
        except PdfReadError as e:
            raise PermanentError(f"This PDF couldn't be read; it may be damaged ({e}).")
    if mime.endswith("presentationml.presentation"):
        with zipfile.ZipFile(path) as z:
            return sum(1 for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
    return None


@handler("document.inspect")
def inspect_document(db, job, progress):
    doc = db.get(Document, job.payload["document_id"])
    if doc is None or doc.deleted_at:
        return {"skipped": "document deleted"}
    if doc.processing_status == DocumentStatus.READY:
        return {"page_count": doc.page_count, "skipped": "already processed"}  # idempotent: safe to run twice
    doc.processing_status = DocumentStatus.PROCESSING
    progress(10, "Opening the file")
    storage = get_storage()
    if not storage.exists(doc.storage_path):
        raise PermanentError("The uploaded file is missing from storage.")
    pages = _count_units(storage.path(doc.storage_path), doc.mime_type)
    progress(80, "Checking the contents")
    doc.page_count = pages
    doc.processing_status, doc.error, doc.updated_at = DocumentStatus.READY, None, utcnow()
    return {"page_count": pages}


@on_failure("document.inspect")
def inspect_failed(db, job):
    doc = db.get(Document, job.payload.get("document_id"))
    if doc:
        doc.processing_status = DocumentStatus.FAILED
        doc.error = (job.error or "").split(": ", 1)[-1][:500]
        events.record(events.UPLOAD_FAILED, "DOCUMENT_PROCESSING_FAILED", f"{doc.original_filename}: {doc.error}",
                      user_id=doc.uploaded_by)
