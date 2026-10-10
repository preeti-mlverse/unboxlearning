"""Catalog, enrollment and lesson progress. Progress always belongs to (learner, course *version*)."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..db import utcnow
from ..enums import CourseStatus, EnrollmentStatus, ProgressStatus, Visibility
from ..errors import AppError, conflict, not_found
from ..models import Course, CourseVersion, Enrollment, Lesson, LessonProgress, Module, Organization
from ..schemas import (CatalogCourse, EnrollmentOut, LearnCourseOut, LearnLessonOut, LessonProgressOut)
from .courses import lesson_detail, module_out
from .permissions import P, Principal


def _visible(principal: Principal):
    member_orgs = list(principal.roles)
    cond = Course.visibility == Visibility.PUBLIC
    if member_orgs:
        cond = or_(cond, Course.organization_id.in_(member_orgs))
    return cond


def _version(db: Session, version_id: str) -> CourseVersion:
    return db.scalar(select(CourseVersion).where(CourseVersion.id == version_id)
                     .options(selectinload(CourseVersion.modules).selectinload(Module.lessons).selectinload(Lesson.blocks)))


def _ordered_lessons(version: CourseVersion) -> list[Lesson]:
    return [l for m in version.modules for l in m.lessons]


# ---------------------------------------------------------------- catalog
def catalog(db: Session, principal: Principal, q: str | None = None) -> list[CatalogCourse]:
    stmt = (select(Course, Organization.name).join(Organization, Organization.id == Course.organization_id)
            .where(Course.status == CourseStatus.PUBLISHED, Course.deleted_at.is_(None),
                   Course.current_published_version_id.is_not(None), _visible(principal)))
    if q:
        stmt = stmt.where(Course.title.ilike(f"%{q.strip()}%"))
    mine = dict(db.execute(select(Enrollment.course_id, Enrollment.id).where(
        Enrollment.user_id == principal.id, Enrollment.status != EnrollmentStatus.CANCELLED)).all())
    out = []
    for course, org_name in db.execute(stmt.order_by(Course.updated_at.desc())).all():
        lessons = db.execute(select(Lesson.estimated_minutes).join(Module, Lesson.module_id == Module.id)
                             .where(Module.course_version_id == course.current_published_version_id)).scalars().all()
        modules = db.scalar(select(func.count(Module.id)).where(Module.course_version_id == course.current_published_version_id))
        out.append(CatalogCourse(id=course.id, title=course.title, description=course.description, organization_name=org_name,
                                 module_count=modules or 0, lesson_count=len(lessons), estimated_minutes=sum(lessons),
                                 enrollment_id=mine.get(course.id)))
    return out


# ---------------------------------------------------------------- enrollment
def enroll(db: Session, principal: Principal, course_id: str) -> Enrollment:
    course = db.get(Course, course_id)
    visible = course and course.deleted_at is None and (course.visibility == Visibility.PUBLIC
                                                        or principal.is_member(course.organization_id))
    if not visible:
        raise not_found("That course")
    principal.require(P.LEARNER_ENROLL, course.organization_id)
    existing = db.scalar(select(Enrollment).where(Enrollment.user_id == principal.id, Enrollment.course_id == course_id))
    if existing and existing.status != EnrollmentStatus.CANCELLED:
        return existing  # enrolling twice is harmless
    if course.status != CourseStatus.PUBLISHED or not course.current_published_version_id:
        raise conflict("NOT_PUBLISHED", "This course isn't open for enrollment.")
    if existing:  # re-joining after leaving: start again on the current version
        existing.status, existing.course_version_id = EnrollmentStatus.ACTIVE, course.current_published_version_id
        existing.enrolled_at, existing.completed_at = utcnow(), None
        return existing
    enrollment = Enrollment(user_id=principal.id, course_id=course.id, course_version_id=course.current_published_version_id)
    db.add(enrollment)
    db.flush()
    return enrollment


def get_enrollment(db: Session, principal: Principal, enrollment_id: str) -> Enrollment:
    e = db.get(Enrollment, enrollment_id)
    if e is None or e.user_id != principal.id:
        raise not_found("That enrollment")
    return e


def enrollment_for_course(db: Session, principal: Principal, course_id: str) -> Enrollment:
    e = db.scalar(select(Enrollment).where(Enrollment.user_id == principal.id, Enrollment.course_id == course_id,
                                           Enrollment.status != EnrollmentStatus.CANCELLED))
    if e is None:
        raise AppError(404, "NOT_ENROLLED", "Join this course to start learning.")
    return e


def leave(db: Session, principal: Principal, enrollment_id: str) -> None:
    get_enrollment(db, principal, enrollment_id).status = EnrollmentStatus.CANCELLED


def _progress_map(db: Session, enrollment_id: str) -> dict[str, LessonProgress]:
    return {p.lesson_id: p for p in db.scalars(select(LessonProgress).where(LessonProgress.enrollment_id == enrollment_id))}


def _p_out(lesson_id: str, p: LessonProgress | None) -> LessonProgressOut:
    if p is None:
        return LessonProgressOut(lesson_id=lesson_id, status=ProgressStatus.NOT_STARTED, started_at=None, completed_at=None)
    return LessonProgressOut(lesson_id=lesson_id, status=p.status, started_at=p.started_at, completed_at=p.completed_at)


def enrollment_out(db: Session, e: Enrollment, version: CourseVersion | None = None) -> EnrollmentOut:
    version = version or _version(db, e.course_version_id)
    course = db.get(Course, e.course_id)
    lessons = _ordered_lessons(version)
    progress = _progress_map(db, e.id)
    done = sum(1 for l in lessons if progress.get(l.id) and progress[l.id].status == ProgressStatus.COMPLETED)
    nxt = next((l.id for l in lessons if not (progress.get(l.id) and progress[l.id].status == ProgressStatus.COMPLETED)), None)
    if e.last_lesson_id and nxt and progress.get(e.last_lesson_id) and progress[e.last_lesson_id].status == ProgressStatus.IN_PROGRESS:
        nxt = e.last_lesson_id  # carry on where they stopped
    newer = bool(course.current_published_version_id and course.current_published_version_id != e.course_version_id
                 and course.status == CourseStatus.PUBLISHED)
    return EnrollmentOut(id=e.id, course_id=course.id, course_title=course.title, course_version_id=version.id,
                         version_number=version.version_number, status=e.status, enrolled_at=e.enrolled_at,
                         completed_at=e.completed_at, lessons_total=len(lessons), lessons_completed=done,
                         percent=round(100 * done / len(lessons)) if lessons else 0, next_lesson_id=nxt,
                         last_activity_at=e.last_activity_at, newer_version_available=newer)


def my_enrollments(db: Session, principal: Principal) -> list[EnrollmentOut]:
    rows = db.scalars(select(Enrollment).where(Enrollment.user_id == principal.id,
                                               Enrollment.status != EnrollmentStatus.CANCELLED)
                      .order_by(func.coalesce(Enrollment.last_activity_at, Enrollment.enrolled_at).desc())).all()
    return [enrollment_out(db, e) for e in rows]


def learn_course(db: Session, principal: Principal, course_id: str) -> LearnCourseOut:
    e = enrollment_for_course(db, principal, course_id)
    version = _version(db, e.course_version_id)
    progress = _progress_map(db, e.id)
    course = db.get(Course, course_id)
    return LearnCourseOut(**enrollment_out(db, e, version).model_dump(), description=course.description,
                          modules=[module_out(m) for m in version.modules],
                          progress=[_p_out(l.id, progress.get(l.id)) for l in _ordered_lessons(version)])


def learn_lesson(db: Session, principal: Principal, course_id: str, lesson_id: str) -> LearnLessonOut:
    e = enrollment_for_course(db, principal, course_id)
    version = _version(db, e.course_version_id)
    lessons = _ordered_lessons(version)
    idx = next((i for i, l in enumerate(lessons) if l.id == lesson_id), None)
    if idx is None:
        raise not_found("That lesson")  # not part of the version this learner is on
    lesson = lessons[idx]
    module = next(m for m in version.modules if m.id == lesson.module_id)
    course = db.get(Course, course_id)
    return LearnLessonOut(lesson=lesson_detail(lesson), module_title=module.title, course_id=course.id,
                          course_title=course.title, enrollment_id=e.id,
                          progress=_p_out(lesson.id, _progress_map(db, e.id).get(lesson.id)),
                          previous_lesson_id=lessons[idx - 1].id if idx > 0 else None,
                          next_lesson_id=lessons[idx + 1].id if idx + 1 < len(lessons) else None,
                          position=idx + 1, total=len(lessons))


def set_progress(db: Session, principal: Principal, enrollment_id: str, lesson_id: str, status: str) -> EnrollmentOut:
    e = get_enrollment(db, principal, enrollment_id)
    if e.status == EnrollmentStatus.CANCELLED:
        raise conflict("NOT_ENROLLED", "Join this course again to keep learning.")
    version = _version(db, e.course_version_id)
    lessons = _ordered_lessons(version)
    if lesson_id not in {l.id for l in lessons}:
        raise not_found("That lesson")
    now = utcnow()
    p = db.scalar(select(LessonProgress).where(LessonProgress.enrollment_id == e.id, LessonProgress.lesson_id == lesson_id))
    if p is None:
        p = LessonProgress(enrollment_id=e.id, lesson_id=lesson_id, status=ProgressStatus.NOT_STARTED)
        db.add(p)
    if status == ProgressStatus.IN_PROGRESS:
        if p.status == ProgressStatus.NOT_STARTED:  # re-opening a finished lesson doesn't undo it
            p.status, p.started_at = ProgressStatus.IN_PROGRESS, now
    elif status == ProgressStatus.COMPLETED and p.status != ProgressStatus.COMPLETED:
        p.status, p.completed_at = ProgressStatus.COMPLETED, now
        p.started_at = p.started_at or now
    e.last_lesson_id, e.last_activity_at = lesson_id, now
    db.flush()
    progress = _progress_map(db, e.id)
    if all(progress.get(l.id) and progress[l.id].status == ProgressStatus.COMPLETED for l in lessons):
        if e.status != EnrollmentStatus.COMPLETED:
            e.status, e.completed_at = EnrollmentStatus.COMPLETED, now
    elif e.status == EnrollmentStatus.COMPLETED:
        e.status, e.completed_at = EnrollmentStatus.ACTIVE, None
    return enrollment_out(db, e, version)


def switch_to_latest(db: Session, principal: Principal, enrollment_id: str) -> EnrollmentOut:
    """Move a learner onto the newest published version, carrying finished lessons across by lineage."""
    e = get_enrollment(db, principal, enrollment_id)
    course = db.get(Course, e.course_id)
    if not course.current_published_version_id or course.current_published_version_id == e.course_version_id:
        return enrollment_out(db, e)
    old = {l.id: l.lineage_id for l in _ordered_lessons(_version(db, e.course_version_id))}
    new_version = _version(db, course.current_published_version_id)
    by_lineage = {l.lineage_id: l.id for l in _ordered_lessons(new_version)}
    for p in list(db.scalars(select(LessonProgress).where(LessonProgress.enrollment_id == e.id))):
        target = by_lineage.get(old.get(p.lesson_id, ""))
        if target:
            p.lesson_id = target
        else:
            db.delete(p)  # that lesson no longer exists
    e.course_version_id = new_version.id
    e.last_lesson_id = by_lineage.get(old.get(e.last_lesson_id or "", ""))
    db.flush()
    lessons = _ordered_lessons(new_version)
    progress = _progress_map(db, e.id)
    complete = lessons and all(progress.get(l.id) and progress[l.id].status == ProgressStatus.COMPLETED for l in lessons)
    e.status = EnrollmentStatus.COMPLETED if complete else EnrollmentStatus.ACTIVE
    e.completed_at = e.completed_at if complete else None
    return enrollment_out(db, e, new_version)
