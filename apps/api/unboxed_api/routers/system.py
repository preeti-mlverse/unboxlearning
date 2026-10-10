"""/jobs (status polling), /admin (platform admins only) and /health."""
from datetime import timedelta

from fastapi import APIRouter, Query
from sqlalchemy import func, select, text

from ..db import utcnow
from ..deps import DB, Admin, Me
from ..enums import CourseStatus, JobStatus, UserStatus
from ..errors import AppError, bad_request, not_found
from ..models import Course, Document, Enrollment, Job, Membership, Organization, SystemEvent, User
from ..schemas import AdminOrgOut, AdminStats, AdminUserOut, CourseSummary, JobOut, Ok, SystemEventOut
from ..services import events as ev
from ..services import courses as course_svc
from ..services import jobs as job_svc
from ..services.permissions import P

router = APIRouter()


# ---------------------------------------------------------------- jobs
def _job_for(db, me, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise not_found("That job")
    if me.is_admin or job.created_by == me.id:
        return job
    if job.entity_type == "document":
        doc = db.get(Document, job.entity_id)
        if doc and me.can(P.DOCUMENT_VIEW, doc.organization_id):
            return job
    raise not_found("That job")


@router.get("/jobs/{job_id}", response_model=JobOut, tags=["jobs"])
def get_job(job_id: str, me: Me, db: DB):
    return _job_for(db, me, job_id)


@router.post("/jobs/{job_id}/retry", response_model=JobOut, tags=["jobs"])
def retry_job(job_id: str, me: Me, db: DB):
    job = _job_for(db, me, job_id)
    if job.status != JobStatus.FAILED:
        raise bad_request("JOB_NOT_FAILED", "Only failed jobs can be retried.")
    job_svc.retry(db, job)
    if job.entity_type == "document":
        doc = db.get(Document, job.entity_id)
        if doc:
            doc.processing_status, doc.error = "queued", None
    return job


# ---------------------------------------------------------------- admin
admin = APIRouter(prefix="/admin", tags=["admin"])


@admin.get("/stats", response_model=AdminStats)
def stats(_: Admin, db: DB):
    count = lambda stmt: db.scalar(stmt) or 0  # noqa: E731
    return AdminStats(
        users=count(select(func.count(User.id))),
        organizations=count(select(func.count(Organization.id))),
        courses=count(select(func.count(Course.id)).where(Course.deleted_at.is_(None))),
        published_courses=count(select(func.count(Course.id)).where(Course.status == CourseStatus.PUBLISHED,
                                                                    Course.deleted_at.is_(None))),
        enrollments=count(select(func.count(Enrollment.id))),
        documents=count(select(func.count(Document.id)).where(Document.deleted_at.is_(None))),
        jobs_pending=count(select(func.count(Job.id)).where(Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING]))),
        jobs_failed=count(select(func.count(Job.id)).where(Job.status == JobStatus.FAILED)),
        server_errors_24h=count(_since(ev.SERVER_ERROR, 1)), server_errors_7d=count(_since(ev.SERVER_ERROR, 7)),
        uploads_rejected_24h=count(_since(ev.UPLOAD_REJECTED, 1)),
        uploads_failed_24h=count(_since(ev.UPLOAD_FAILED, 1)), uploads_failed_7d=count(_since(ev.UPLOAD_FAILED, 7)),
        documents_failed=count(select(func.count(Document.id)).where(Document.processing_status == "failed",
                                                                     Document.deleted_at.is_(None))))


def _since(kind: str, days: int):
    return select(func.count(SystemEvent.id)).where(SystemEvent.kind == kind,
                                                    SystemEvent.created_at > utcnow() - timedelta(days=days))


@admin.get("/events", response_model=list[SystemEventOut])
def recent_events(_: Admin, db: DB, kind: str | None = Query(None, max_length=30), limit: int = Query(100, le=500)):
    """Recent server errors and upload problems, newest first. The request ID links each one to the logs."""
    stmt = select(SystemEvent)
    if kind:
        stmt = stmt.where(SystemEvent.kind == kind)
    return db.scalars(stmt.order_by(SystemEvent.created_at.desc()).limit(limit)).all()


@admin.get("/users", response_model=list[AdminUserOut])
def users(_: Admin, db: DB, q: str | None = Query(None, max_length=200), limit: int = Query(100, le=500)):
    stmt = select(User)
    if q:
        stmt = stmt.where(User.email.ilike(f"%{q.strip()}%"))
    orgs = dict(db.execute(select(Membership.user_id, func.count(func.distinct(Membership.organization_id)))
                           .group_by(Membership.user_id)).all())
    return [AdminUserOut(id=u.id, email=u.email, display_name=u.profile.display_name, status=u.status,
                         email_verified=u.email_verified_at is not None, is_platform_admin=u.is_platform_admin,
                         organizations=orgs.get(u.id, 0), created_at=u.created_at, last_login_at=u.last_login_at)
            for u in db.scalars(stmt.order_by(User.created_at.desc()).limit(limit)).unique()]


@admin.post("/users/{user_id}/status", response_model=Ok)
def set_user_status(user_id: str, me: Admin, db: DB, status: UserStatus = Query(...)):
    user = db.get(User, user_id)
    if user is None:
        raise not_found("That user")
    if user.id == me.id:
        raise AppError(400, "CANNOT_DISABLE_SELF", "You can't disable your own account.")
    user.status = status
    if status == UserStatus.DISABLED:
        from ..services.accounts import revoke_all
        revoke_all(db, user.id)
    return Ok(message=f"Account is now {status}.")


@admin.get("/organizations", response_model=list[AdminOrgOut])
def organizations(_: Admin, db: DB, q: str | None = Query(None, max_length=200)):
    stmt = select(Organization)
    if q:
        stmt = stmt.where(Organization.name.ilike(f"%{q.strip()}%"))
    members = dict(db.execute(select(Membership.organization_id, func.count(func.distinct(Membership.user_id)))
                              .group_by(Membership.organization_id)).all())
    courses = dict(db.execute(select(Course.organization_id, func.count(Course.id)).where(Course.deleted_at.is_(None))
                              .group_by(Course.organization_id)).all())
    return [AdminOrgOut.model_validate(o).model_copy(update={"members": members.get(o.id, 0), "courses": courses.get(o.id, 0)})
            for o in db.scalars(stmt.order_by(Organization.created_at.desc()).limit(500))]


@admin.get("/courses", response_model=list[CourseSummary])
def all_courses(_: Admin, db: DB, q: str | None = Query(None, max_length=200), include_deleted: bool = False):
    stmt = select(Course)
    if not include_deleted:
        stmt = stmt.where(Course.deleted_at.is_(None))
    if q:
        stmt = stmt.where(Course.title.ilike(f"%{q.strip()}%"))
    return [course_svc.summary(db, c) for c in db.scalars(stmt.order_by(Course.updated_at.desc()).limit(500))]


@admin.post("/courses/{course_id}/restore", response_model=CourseSummary)
def restore_course(course_id: str, _: Admin, db: DB):
    """Undo a soft delete. The course comes back as a draft (or archived, if it had been published)."""
    course = db.get(Course, course_id)
    if course is None:
        raise not_found("That course")
    course.deleted_at = None
    if course.status == CourseStatus.ARCHIVED and not course.current_published_version_id:
        course.status = CourseStatus.DRAFT
    return course_svc.summary(db, course)


@admin.post("/jobs/{job_id}/retry", response_model=JobOut)
def admin_retry_job(job_id: str, _: Admin, db: DB):
    job = db.get(Job, job_id)
    if job is None:
        raise not_found("That job")
    return job_svc.retry(db, job)


@admin.get("/jobs", response_model=list[JobOut])
def all_jobs(_: Admin, db: DB, status: JobStatus | None = None, limit: int = Query(100, le=500)):
    stmt = select(Job)
    if status:
        stmt = stmt.where(Job.status == status)
    return db.scalars(stmt.order_by(Job.created_at.desc()).limit(limit)).all()


# ---------------------------------------------------------------- health
@router.get("/health", tags=["system"])
def health(db: DB):
    """Is the API up, can it reach the database, and is the job queue moving?"""
    db.execute(text("SELECT 1"))
    stuck = db.scalar(select(func.count(Job.id)).where(Job.status == JobStatus.PENDING,
                                                       Job.run_after < utcnow() - timedelta(minutes=10))) or 0
    failed_today = db.scalar(select(func.count(Job.id)).where(Job.status == JobStatus.FAILED,
                                                              Job.completed_at > utcnow() - timedelta(days=1))) or 0
    return {"status": "ok", "database": "ok", "jobs_waiting_over_10_min": stuck, "jobs_failed_last_24h": failed_today}
