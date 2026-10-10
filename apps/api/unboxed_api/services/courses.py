"""Courses, versions, modules, lessons and blocks.

Rules:
- Only a DRAFT version can be edited. Editing a published course first makes a new draft
  (a deep copy of the published version) with `start_draft()`.
- Publishing turns the draft into the published version and archives the previous one; learners already
  enrolled keep the version they enrolled in.
- Every lookup goes through a permission check against the course's workspace."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..db import utcnow
from ..enums import CourseStatus, DocumentPurpose, LessonStatus, VersionStatus
from ..errors import AppError, bad_request, conflict, forbidden, not_found
from ..models import Course, CourseVersion, Document, Lesson, LessonBlock, Module
from ..security import sign_file_token
from ..schemas import (BlockOut, CourseCreate, CourseDetail, CourseSummary, CourseUpdate, LessonDetail, LessonOut,
                       ModuleOut, VersionOut)
from . import blocks as block_registry
from .permissions import P, Principal


# ---------------------------------------------------------------- lookups
def get_course(db: Session, principal: Principal, course_id: str, permission: str = P.COURSE_VIEW_DRAFT) -> Course:
    course = db.get(Course, course_id)
    if course is None or course.deleted_at is not None:
        raise not_found("That course")
    if not principal.is_member(course.organization_id):
        raise not_found("That course")  # don't reveal other workspaces' courses exist
    principal.require(permission, course.organization_id)
    return course


def draft_version(db: Session, course: Course) -> CourseVersion:
    if not course.current_draft_version_id:
        raise conflict("NO_DRAFT", "This course has no draft. Choose 'Make changes' to start a new version.")
    return db.get(CourseVersion, course.current_draft_version_id)


def _version_of_module(db: Session, module: Module) -> CourseVersion:
    return db.get(CourseVersion, module.course_version_id)


def _editable(db: Session, principal: Principal, version: CourseVersion) -> Course:
    course = get_course(db, principal, version.course_id, P.COURSE_EDIT)
    if version.status != VersionStatus.DRAFT:
        raise conflict("VERSION_LOCKED", "Published versions can't be changed. Make a new draft to edit this course.")
    return course


def get_module(db: Session, principal: Principal, module_id: str, edit: bool = True) -> tuple[Module, Course]:
    module = db.get(Module, module_id)
    if module is None:
        raise not_found("That module")
    version = _version_of_module(db, module)
    course = _editable(db, principal, version) if edit else get_course(db, principal, version.course_id)
    return module, course


def get_lesson(db: Session, principal: Principal, lesson_id: str, edit: bool = True) -> tuple[Lesson, Course]:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise not_found("That lesson")
    module = db.get(Module, lesson.module_id)
    version = _version_of_module(db, module)
    course = _editable(db, principal, version) if edit else get_course(db, principal, version.course_id)
    return lesson, course


def touch(course: Course, principal: Principal) -> None:
    course.updated_at, course.updated_by = utcnow(), principal.id


# ---------------------------------------------------------------- courses
def list_courses(db: Session, principal: Principal, q: str | None = None, org_id: str | None = None,
                 status: str | None = None) -> list[CourseSummary]:
    orgs = principal.orgs_with(P.COURSE_VIEW_DRAFT)
    if org_id:
        if not principal.can(P.COURSE_VIEW_DRAFT, org_id):
            raise forbidden()
        orgs = [org_id]
    if not orgs:
        return []
    stmt = select(Course).where(Course.organization_id.in_(orgs), Course.deleted_at.is_(None))
    if q:
        stmt = stmt.where(Course.title.ilike(f"%{q.strip()}%"))
    if status:
        stmt = stmt.where(Course.status == status)
    return [summary(db, c) for c in db.scalars(stmt.order_by(Course.updated_at.desc())).all()]


def _counts(db: Session, version_id: str | None) -> tuple[int, int]:
    if not version_id:
        return 0, 0
    modules = db.scalar(select(func.count(Module.id)).where(Module.course_version_id == version_id)) or 0
    lessons = db.scalar(select(func.count(Lesson.id)).join(Module, Lesson.module_id == Module.id)
                        .where(Module.course_version_id == version_id)) or 0
    return modules, lessons


def summary(db: Session, course: Course) -> CourseSummary:
    shown = course.current_draft_version_id or course.current_published_version_id
    modules, lessons = _counts(db, shown)
    pub = db.get(CourseVersion, course.current_published_version_id) if course.current_published_version_id else None
    return CourseSummary.model_validate(course).model_copy(update={
        "module_count": modules, "lesson_count": lessons,
        "published_version_number": pub.version_number if pub else None,
        "has_unpublished_changes": bool(course.current_draft_version_id and pub)})


def create_course(db: Session, principal: Principal, data: CourseCreate) -> Course:
    org_id = data.organization_id
    if not org_id:
        options = principal.orgs_with(P.COURSE_CREATE)
        if not options:
            raise AppError(403, "NO_WORKSPACE", "Create a workspace before making a course.")
        org_id = options[0]
    principal.require(P.COURSE_CREATE, org_id)
    course = Course(organization_id=org_id, created_by=principal.id, updated_by=principal.id, title=data.title,
                    description=data.description, visibility=data.visibility)
    db.add(course)
    db.flush()
    v1 = CourseVersion(course_id=course.id, version_number=1, created_by=principal.id)
    db.add(v1)
    db.flush()
    course.current_draft_version_id = v1.id
    return course


def update_course(db: Session, principal: Principal, course_id: str, data: CourseUpdate) -> Course:
    course = get_course(db, principal, course_id, P.COURSE_EDIT)
    for k, v in data.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(course, k, v)
    touch(course, principal)
    return course


def delete_course(db: Session, principal: Principal, course_id: str) -> None:
    """Soft delete: the course disappears from lists and the catalog, but enrollments and history stay."""
    course = get_course(db, principal, course_id, P.COURSE_EDIT)
    course.deleted_at, course.status = utcnow(), CourseStatus.ARCHIVED
    touch(course, principal)


def detail(db: Session, principal: Principal, course: Course, version_id: str | None = None) -> CourseDetail:
    version_id = version_id or course.current_draft_version_id or course.current_published_version_id
    version = None
    modules: list[ModuleOut] = []
    if version_id:
        version = db.scalar(select(CourseVersion).where(CourseVersion.id == version_id, CourseVersion.course_id == course.id)
                            .options(selectinload(CourseVersion.modules).selectinload(Module.lessons)
                                     .selectinload(Lesson.blocks)))
        if version is None:
            raise not_found("That version")
        modules = [module_out(m) for m in version.modules]
    versions = db.scalars(select(CourseVersion).where(CourseVersion.course_id == course.id)
                          .order_by(CourseVersion.version_number.desc())).all()
    return CourseDetail(**summary(db, course).model_dump(), version=VersionOut.model_validate(version) if version else None,
                        modules=modules, versions=[VersionOut.model_validate(v) for v in versions],
                        can_edit=principal.can(P.COURSE_EDIT, course.organization_id)
                        and bool(version and version.status == VersionStatus.DRAFT))


def module_out(m: Module) -> ModuleOut:
    return ModuleOut(id=m.id, lineage_id=m.lineage_id, title=m.title, description=m.description, position=m.position,
                     lessons=[lesson_out(l) for l in m.lessons])


def lesson_out(l: Lesson) -> LessonOut:
    return LessonOut.model_validate(l).model_copy(update={"block_count": len(l.blocks)})


def block_out(b: LessonBlock) -> BlockOut:
    out = BlockOut.model_validate(b)
    if b.block_type == "image" and b.config.get("document_id"):
        out.media_path = f"/files/{sign_file_token(b.config['document_id'], 3600)}"
    return out


def lesson_detail(l: Lesson) -> LessonDetail:
    return LessonDetail(**lesson_out(l).model_dump(), blocks=[block_out(b) for b in l.blocks])


# ---------------------------------------------------------------- versions
def start_draft(db: Session, principal: Principal, course_id: str) -> CourseVersion:
    """Copy the published version into a new draft (modules, lessons and blocks keep their lineage ids)."""
    course = get_course(db, principal, course_id, P.COURSE_EDIT)
    if course.current_draft_version_id:
        return db.get(CourseVersion, course.current_draft_version_id)
    source = db.scalar(select(CourseVersion).where(CourseVersion.id == course.current_published_version_id)
                       .options(selectinload(CourseVersion.modules).selectinload(Module.lessons)
                                .selectinload(Lesson.blocks)))
    number = (db.scalar(select(func.max(CourseVersion.version_number)).where(CourseVersion.course_id == course.id)) or 0) + 1
    draft = CourseVersion(course_id=course.id, version_number=number, created_by=principal.id,
                          based_on_version_id=source.id if source else None)
    db.add(draft)
    db.flush()
    for m in (source.modules if source else []):
        nm = Module(course_version_id=draft.id, lineage_id=m.lineage_id, title=m.title, description=m.description,
                    position=m.position)
        db.add(nm)
        db.flush()
        for l in m.lessons:
            nl = Lesson(module_id=nm.id, lineage_id=l.lineage_id, title=l.title, description=l.description,
                        position=l.position, estimated_minutes=l.estimated_minutes, status=l.status)
            db.add(nl)
            db.flush()
            for b in l.blocks:
                db.add(LessonBlock(lesson_id=nl.id, lineage_id=b.lineage_id, block_type=b.block_type, position=b.position,
                                   config=dict(b.config), generated_by=b.generated_by, model=b.model,
                                   prompt_version=b.prompt_version, pipeline_version=b.pipeline_version))
    course.current_draft_version_id = draft.id
    touch(course, principal)
    db.flush()
    return draft


def discard_draft(db: Session, principal: Principal, course_id: str) -> None:
    course = get_course(db, principal, course_id, P.COURSE_EDIT)
    if not course.current_published_version_id:
        raise conflict("NOTHING_TO_GO_BACK_TO", "This course has never been published, so there's no earlier version to keep.")
    draft = draft_version(db, course)
    course.current_draft_version_id = None
    db.delete(draft)
    touch(course, principal)


def publish_problems(db: Session, version: CourseVersion) -> list[str]:
    problems = []
    if not version.modules:
        problems.append("Add at least one module.")
    for m in version.modules:
        if not m.lessons:
            problems.append(f"Module '{m.title}' has no lessons.")
        for l in m.lessons:
            if not [b for b in l.blocks if not block_registry.is_empty(b.block_type, b.config)]:
                problems.append(f"Lesson '{l.title}' has no content yet.")
    return problems


def publish(db: Session, principal: Principal, course_id: str) -> Course:
    course = get_course(db, principal, course_id, P.COURSE_PUBLISH)
    draft = db.scalar(select(CourseVersion).where(CourseVersion.id == course.current_draft_version_id)
                      .options(selectinload(CourseVersion.modules).selectinload(Module.lessons)
                               .selectinload(Lesson.blocks))) if course.current_draft_version_id else None
    if draft is None:
        raise conflict("NO_DRAFT", "There are no unpublished changes to publish.")
    problems = publish_problems(db, draft)
    if problems:
        raise bad_request("PUBLISH_BLOCKED", "This course isn't ready to publish yet.", {"problems": problems})
    if course.current_published_version_id:
        old = db.get(CourseVersion, course.current_published_version_id)
        old.status = VersionStatus.ARCHIVED  # kept: enrolled learners may still be on it
    now = utcnow()
    draft.status, draft.published_at, draft.published_by = VersionStatus.PUBLISHED, now, principal.id
    for m in draft.modules:
        for l in m.lessons:
            l.status = LessonStatus.READY
    course.current_published_version_id, course.current_draft_version_id = draft.id, None
    course.status = CourseStatus.PUBLISHED
    touch(course, principal)
    return course


def unpublish(db: Session, principal: Principal, course_id: str) -> Course:
    """Take a course out of the catalog. Enrolled learners keep access; nobody new can enroll."""
    course = get_course(db, principal, course_id, P.COURSE_PUBLISH)
    course.status = CourseStatus.ARCHIVED if course.current_published_version_id else CourseStatus.DRAFT
    touch(course, principal)
    return course


# ---------------------------------------------------------------- modules
def _next_position(db: Session, column, parent_col, parent_id: str) -> int:
    return (db.scalar(select(func.max(column)).where(parent_col == parent_id)) or 0) + 1


def add_module(db: Session, principal: Principal, course_id: str, title: str, description: str) -> Module:
    course = get_course(db, principal, course_id, P.COURSE_EDIT)
    version = draft_version(db, course)
    m = Module(course_version_id=version.id, title=title, description=description,
               position=_next_position(db, Module.position, Module.course_version_id, version.id))
    db.add(m)
    touch(course, principal)
    db.flush()
    return m


def update_module(db: Session, principal: Principal, module_id: str, data: dict) -> Module:
    module, course = get_module(db, principal, module_id)
    for k, v in data.items():
        if v is not None:
            setattr(module, k, v)
    touch(course, principal)
    return module


def delete_module(db: Session, principal: Principal, module_id: str) -> None:
    module, course = get_module(db, principal, module_id)
    db.delete(module)
    touch(course, principal)


def reorder(items: list, ids: list[str]) -> None:
    by_id = {i.id: i for i in items}
    if set(ids) != set(by_id):
        raise bad_request("REORDER_MISMATCH", "The new order must list every item exactly once.")
    for pos, i in enumerate(ids, start=1):
        by_id[i].position = pos


def reorder_modules(db: Session, principal: Principal, course_id: str, ids: list[str]) -> None:
    course = get_course(db, principal, course_id, P.COURSE_EDIT)
    version = draft_version(db, course)
    reorder(db.scalars(select(Module).where(Module.course_version_id == version.id)).all(), ids)
    touch(course, principal)


# ---------------------------------------------------------------- lessons
def add_lesson(db: Session, principal: Principal, module_id: str, title: str, description: str, minutes: int) -> Lesson:
    module, course = get_module(db, principal, module_id)
    lesson = Lesson(module_id=module.id, title=title, description=description, estimated_minutes=minutes,
                    position=_next_position(db, Lesson.position, Lesson.module_id, module.id))
    db.add(lesson)
    db.flush()
    # every new lesson starts with an empty text block, so there's somewhere to type
    db.add(LessonBlock(lesson_id=lesson.id, block_type="text", position=1, config={"heading": None, "body": ""}))
    touch(course, principal)
    db.flush()
    db.refresh(lesson)
    return lesson


def update_lesson(db: Session, principal: Principal, lesson_id: str, data: dict) -> Lesson:
    lesson, course = get_lesson(db, principal, lesson_id)
    for k, v in data.items():
        if v is not None:
            setattr(lesson, k, v)
    touch(course, principal)
    return lesson


def delete_lesson(db: Session, principal: Principal, lesson_id: str) -> None:
    lesson, course = get_lesson(db, principal, lesson_id)
    db.delete(lesson)
    touch(course, principal)


def move_lesson(db: Session, principal: Principal, lesson_id: str, module_id: str) -> Lesson:
    lesson, course = get_lesson(db, principal, lesson_id)
    target, target_course = get_module(db, principal, module_id)
    if target.course_version_id != db.get(Module, lesson.module_id).course_version_id:
        raise bad_request("WRONG_VERSION", "Lessons can only move between modules of the same draft.")
    lesson.module_id = target.id
    lesson.position = _next_position(db, Lesson.position, Lesson.module_id, target.id)
    touch(course, principal)
    return lesson


def reorder_lessons(db: Session, principal: Principal, module_id: str, ids: list[str]) -> None:
    module, course = get_module(db, principal, module_id)
    reorder(db.scalars(select(Lesson).where(Lesson.module_id == module.id)).all(), ids)
    touch(course, principal)


# ---------------------------------------------------------------- blocks
def _check_image(db: Session, course: Course, config: dict) -> None:
    doc = db.get(Document, config["document_id"])
    if doc is None or doc.deleted_at or doc.organization_id != course.organization_id:
        raise bad_request("IMAGE_NOT_FOUND", "That image isn't in this workspace. Upload it first.")
    if doc.purpose != DocumentPurpose.ASSET or not doc.mime_type.startswith("image/"):
        raise bad_request("NOT_AN_IMAGE", "Image blocks need an uploaded image (PNG, JPG or WebP).")


def _validated(db: Session, course: Course, block_type: str, config: dict) -> dict:
    clean = block_registry.validate(block_type, config)
    if block_type == "image":
        _check_image(db, course, clean)
    return clean


def add_block(db: Session, principal: Principal, lesson_id: str, block_type: str, config: dict,
              position: int | None = None) -> LessonBlock:
    lesson, course = get_lesson(db, principal, lesson_id)
    clean = _validated(db, course, block_type, config)
    siblings = sorted(lesson.blocks, key=lambda b: b.position)
    if position is None or position > len(siblings):
        position = len(siblings) + 1
    position = max(1, position)
    for b in siblings:
        if b.position >= position:
            b.position += 1
    block = LessonBlock(lesson_id=lesson.id, block_type=block_type, config=clean, position=position)
    db.add(block)
    touch(course, principal)
    db.flush()
    return block


def get_block(db: Session, principal: Principal, block_id: str) -> tuple[LessonBlock, Course]:
    block = db.get(LessonBlock, block_id)
    if block is None:
        raise not_found("That block")
    _, course = get_lesson(db, principal, block.lesson_id)
    return block, course


def update_block(db: Session, principal: Principal, block_id: str, config: dict) -> LessonBlock:
    block, course = get_block(db, principal, block_id)
    block.config = _validated(db, course, block.block_type, config)
    touch(course, principal)
    return block


def delete_block(db: Session, principal: Principal, block_id: str) -> None:
    block, course = get_block(db, principal, block_id)
    db.delete(block)
    touch(course, principal)


def reorder_blocks(db: Session, principal: Principal, lesson_id: str, ids: list[str]) -> None:
    lesson, course = get_lesson(db, principal, lesson_id)
    reorder(list(lesson.blocks), ids)
    touch(course, principal)
