"""/documents (private uploads) and /files/{token} (short-lived signed downloads)."""
from fastapi import APIRouter, File, Form, Query, Response, UploadFile
from fastapi.responses import FileResponse

from ..deps import DB, Me
from ..enums import DocumentPurpose
from ..errors import AppError, not_found
from ..models import Document
from ..schemas import DocumentOut, DocumentUpdate, SignedUrlOut
from ..security import verify_file_token
from ..services import documents as svc
from ..config import get_settings
from ..services.storage import get_storage

router = APIRouter(tags=["documents"])


@router.post("/documents", response_model=DocumentOut, status_code=201)
async def upload(me: Me, db: DB, file: UploadFile = File(...), organization_id: str | None = Form(None),
                 course_id: str | None = Form(None), title: str | None = Form(None, max_length=200),
                 purpose: DocumentPurpose = Form(DocumentPurpose.SOURCE)):
    """Upload a PDF, Word, PowerPoint, text or image file. Returns at once; processing runs as a background job."""
    return await svc.upload(db, me, file, organization_id=organization_id, course_id=course_id or None,
                            title=title, purpose=purpose)


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(me: Me, db: DB, q: str | None = Query(None, max_length=200), course_id: str | None = None,
                   purpose: DocumentPurpose | None = None, organization_id: str | None = None):
    return svc.list_docs(db, me, q=q, course_id=course_id, purpose=purpose, organization_id=organization_id)


@router.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str, me: Me, db: DB):
    return svc.out(db, svc.get(db, me, doc_id))


@router.patch("/documents/{doc_id}", response_model=DocumentOut)
def update_document(doc_id: str, data: DocumentUpdate, me: Me, db: DB):
    return svc.update(db, me, doc_id, data.title, data.course_id, data.model_fields_set)


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: str, me: Me, db: DB):
    svc.delete(db, me, doc_id)
    return Response(status_code=204)


@router.post("/documents/{doc_id}/download-url", response_model=SignedUrlOut)
def download_url(doc_id: str, me: Me, db: DB):
    """Permission check first, then a URL that works for a few minutes."""
    doc = svc.get(db, me, doc_id)
    return SignedUrlOut(url=svc.signed_path(doc), expires_in=get_settings().signed_url_seconds)


@router.get("/files/{token}", include_in_schema=False)
def serve_file(token: str, db: DB):
    doc_id = verify_file_token(token)
    if not doc_id:
        raise AppError(403, "LINK_EXPIRED", "This file link has expired. Open the file again from UnboxEd.")
    doc = db.get(Document, doc_id)
    storage = get_storage()
    if doc is None or doc.deleted_at or not storage.exists(doc.storage_path):
        raise not_found("That file")
    inline = doc.mime_type.startswith("image/") or doc.mime_type == "application/pdf"
    return FileResponse(storage.path(doc.storage_path), media_type=doc.mime_type, filename=doc.original_filename,
                        content_disposition_type="inline" if inline else "attachment",
                        headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"})
