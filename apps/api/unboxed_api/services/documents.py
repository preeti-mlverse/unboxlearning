"""Documents: upload into private storage, queue processing, list, rename, soft-delete, and hand out signed URLs."""
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import new_id, utcnow
from ..enums import DocumentPurpose, DocumentStatus
from ..errors import AppError, not_found
from ..models import Course, Document, Job
from ..schemas import DocumentOut
from ..security import sign_file_token
from . import jobs, uploads
from .permissions import P, Principal
from .storage import document_key, get_storage

INSPECT = "document.inspect"


def _org_for_upload(db: Session, principal: Principal, organization_id: str | None, course_id: str | None) -> str:
    if course_id:
        course = db.get(Course, course_id)
        if course is None or course.deleted_at or not principal.is_member(course.organization_id):
            raise not_found("That course")
        return course.organization_id
    if organization_id:
        return organization_id
    options = principal.orgs_with(P.DOCUMENT_UPLOAD)
    if not options:
        raise AppError(403, "NO_WORKSPACE", "Create a workspace before uploading files.")
    return options[0]


async def upload(db: Session, principal: Principal, file: UploadFile, *, organization_id: str | None,
                 course_id: str | None, title: str | None, purpose: str) -> DocumentOut:
    org_id = _org_for_upload(db, principal, organization_id, course_id)
    principal.require(P.DOCUMENT_UPLOAD, org_id)
    checked = await uploads.receive(file, only_images=purpose == DocumentPurpose.ASSET)
    doc_id = new_id("doc")()
    key = document_key(org_id, doc_id, checked.ext, purpose)
    try:
        get_storage().put_file(key, checked.path)
    except OSError:
        raise AppError(500, "DOCUMENT_UPLOAD_FAILED", "We couldn't upload this file. Please try again.")
    finally:
        checked.path.unlink(missing_ok=True)
    doc = Document(id=doc_id, organization_id=org_id, course_id=course_id, uploaded_by=principal.id,
                   title=(title or checked.filename.rsplit(".", 1)[0])[:200], original_filename=checked.filename,
                   mime_type=checked.mime, storage_path=key, file_size=checked.size, checksum=checked.sha256,
                   purpose=purpose, processing_status=DocumentStatus.UPLOADED)
    db.add(doc)
    db.flush()
    job = None
    if purpose == DocumentPurpose.SOURCE:
        job = jobs.enqueue(db, INSPECT, entity_type="document", entity_id=doc.id, payload={"document_id": doc.id},
                           idempotency_key=f"{INSPECT}:{doc.id}", created_by=principal.id)
        doc.processing_status = DocumentStatus.QUEUED
    else:
        doc.processing_status = DocumentStatus.READY  # images are used as they are
    return out(db, doc, job)


def out(db: Session, doc: Document, job: Job | None = None) -> DocumentOut:
    if job is None:
        job = db.scalar(select(Job).where(Job.entity_type == "document", Job.entity_id == doc.id)
                        .order_by(Job.created_at.desc()).limit(1))
    return DocumentOut.model_validate(doc).model_copy(update={"job_id": job.id if job else None})


def get(db: Session, principal: Principal, doc_id: str, permission: str = P.DOCUMENT_VIEW) -> Document:
    doc = db.get(Document, doc_id)
    if doc is None or doc.deleted_at or not principal.is_member(doc.organization_id):
        raise not_found("That document")
    principal.require(permission, doc.organization_id)
    return doc


def list_docs(db: Session, principal: Principal, *, q: str | None, course_id: str | None, purpose: str | None,
              organization_id: str | None, deleted: bool = False) -> list[DocumentOut]:
    orgs = [organization_id] if organization_id else principal.orgs_with(P.DOCUMENT_VIEW)
    orgs = [o for o in orgs if principal.can(P.DOCUMENT_VIEW, o)]
    if not orgs:
        return []
    stmt = select(Document).where(Document.organization_id.in_(orgs),
                                  Document.deleted_at.is_not(None) if deleted else Document.deleted_at.is_(None))
    if q:
        stmt = stmt.where(Document.title.ilike(f"%{q.strip()}%") | Document.original_filename.ilike(f"%{q.strip()}%"))
    if course_id:
        stmt = stmt.where(Document.course_id == course_id)
    if purpose:
        stmt = stmt.where(Document.purpose == purpose)
    return [out(db, d) for d in db.scalars(stmt.order_by(Document.created_at.desc()).limit(200))]


def update(db: Session, principal: Principal, doc_id: str, title: str | None, course_id: str | None,
           fields: set[str]) -> DocumentOut:
    doc = get(db, principal, doc_id, P.DOCUMENT_UPLOAD)
    if title:
        doc.title = title
    if "course_id" in fields:
        if course_id:
            course = db.get(Course, course_id)
            if course is None or course.organization_id != doc.organization_id or course.deleted_at:
                raise not_found("That course")
        doc.course_id = course_id
    return out(db, doc)


def delete(db: Session, principal: Principal, doc_id: str) -> None:
    """Soft delete. The file stays in storage until a cleanup job removes it, so a mistake can be undone."""
    doc = get(db, principal, doc_id, P.DOCUMENT_UPLOAD)
    doc.deleted_at = utcnow()


def signed_path(doc: Document) -> str:
    return f"/files/{sign_file_token(doc.id)}"


def restore(db: Session, principal: Principal, doc_id: str) -> DocumentOut:
    """Undo a delete. Only people who can upload to the workspace can bring a document back."""
    doc = db.get(Document, doc_id)
    if doc is None or doc.deleted_at is None or not principal.is_member(doc.organization_id):
        raise not_found("That deleted document")
    principal.require(P.DOCUMENT_UPLOAD, doc.organization_id)
    doc.deleted_at = None
    return out(db, doc)
