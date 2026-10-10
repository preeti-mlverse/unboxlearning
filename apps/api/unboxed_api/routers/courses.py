"""/courses, versions, /modules, /lessons, /blocks: the manual course editor's API."""
from fastapi import APIRouter, Query, Response

from ..deps import DB, Me
from ..schemas import (BlockIn, BlockOut, CourseCreate, CourseDetail, CourseSummary, CourseUpdate, LessonCreate,
                       LessonDetail, LessonOut, LessonUpdate, ModuleCreate, ModuleOut, ModuleUpdate, Ok, ReorderIn,
                       VersionOut)
from ..services import courses as svc

router = APIRouter(tags=["courses"])


@router.get("/courses", response_model=list[CourseSummary])
def list_courses(me: Me, db: DB, q: str | None = Query(None, max_length=200), organization_id: str | None = None,
                 status: str | None = None):
    """Courses the signed-in creator can see in their workspaces (search by title with ?q=)."""
    return svc.list_courses(db, me, q, organization_id, status)


@router.post("/courses", response_model=CourseSummary, status_code=201)
def create_course(data: CourseCreate, me: Me, db: DB):
    return svc.summary(db, svc.create_course(db, me, data))


@router.get("/courses/{course_id}", response_model=CourseDetail)
def get_course(course_id: str, me: Me, db: DB, version_id: str | None = None):
    """The draft (or, if none, the published version) with modules, lessons and every version's status."""
    return svc.detail(db, me, svc.get_course(db, me, course_id), version_id)


@router.patch("/courses/{course_id}", response_model=CourseSummary)
def update_course(course_id: str, data: CourseUpdate, me: Me, db: DB):
    return svc.summary(db, svc.update_course(db, me, course_id, data))


@router.delete("/courses/{course_id}", status_code=204)
def delete_course(course_id: str, me: Me, db: DB):
    svc.delete_course(db, me, course_id)
    return Response(status_code=204)


@router.get("/courses/{course_id}/versions", response_model=list[VersionOut])
def versions(course_id: str, me: Me, db: DB):
    return svc.detail(db, me, svc.get_course(db, me, course_id)).versions


@router.post("/courses/{course_id}/versions", response_model=VersionOut, status_code=201)
def start_draft(course_id: str, me: Me, db: DB):
    """Start editing a published course: copies the published version into a new draft."""
    return svc.start_draft(db, me, course_id)


@router.delete("/courses/{course_id}/draft", status_code=204)
def discard_draft(course_id: str, me: Me, db: DB):
    svc.discard_draft(db, me, course_id)
    return Response(status_code=204)


@router.post("/courses/{course_id}/publish", response_model=CourseDetail)
def publish(course_id: str, me: Me, db: DB):
    course = svc.publish(db, me, course_id)
    db.flush()
    return svc.detail(db, me, course)


@router.post("/courses/{course_id}/unpublish", response_model=CourseSummary)
def unpublish(course_id: str, me: Me, db: DB):
    return svc.summary(db, svc.unpublish(db, me, course_id))


# ---------------------------------------------------------------- modules
@router.post("/courses/{course_id}/modules", response_model=ModuleOut, status_code=201)
def add_module(course_id: str, data: ModuleCreate, me: Me, db: DB):
    return svc.module_out(svc.add_module(db, me, course_id, data.title, data.description))


@router.put("/courses/{course_id}/modules/order", response_model=Ok)
def reorder_modules(course_id: str, data: ReorderIn, me: Me, db: DB):
    svc.reorder_modules(db, me, course_id, data.ids)
    return Ok()


@router.patch("/modules/{module_id}", response_model=ModuleOut)
def update_module(module_id: str, data: ModuleUpdate, me: Me, db: DB):
    return svc.module_out(svc.update_module(db, me, module_id, data.model_dump(exclude_unset=True)))


@router.delete("/modules/{module_id}", status_code=204)
def delete_module(module_id: str, me: Me, db: DB):
    svc.delete_module(db, me, module_id)
    return Response(status_code=204)


# ---------------------------------------------------------------- lessons
@router.post("/modules/{module_id}/lessons", response_model=LessonOut, status_code=201)
def add_lesson(module_id: str, data: LessonCreate, me: Me, db: DB):
    return svc.lesson_out(svc.add_lesson(db, me, module_id, data.title, data.description, data.estimated_minutes))


@router.put("/modules/{module_id}/lessons/order", response_model=Ok)
def reorder_lessons(module_id: str, data: ReorderIn, me: Me, db: DB):
    svc.reorder_lessons(db, me, module_id, data.ids)
    return Ok()


@router.get("/lessons/{lesson_id}", response_model=LessonDetail)
def get_lesson(lesson_id: str, me: Me, db: DB):
    """A lesson with its blocks, for editing or previewing (any version the creator can see)."""
    lesson, _ = svc.get_lesson(db, me, lesson_id, edit=False)
    return svc.lesson_detail(lesson)


@router.patch("/lessons/{lesson_id}", response_model=LessonOut)
def update_lesson(lesson_id: str, data: LessonUpdate, me: Me, db: DB):
    return svc.lesson_out(svc.update_lesson(db, me, lesson_id, data.model_dump(exclude_unset=True)))


@router.post("/lessons/{lesson_id}/move", response_model=LessonOut)
def move_lesson(lesson_id: str, me: Me, db: DB, module_id: str = Query(...)):
    return svc.lesson_out(svc.move_lesson(db, me, lesson_id, module_id))


@router.delete("/lessons/{lesson_id}", status_code=204)
def delete_lesson(lesson_id: str, me: Me, db: DB):
    svc.delete_lesson(db, me, lesson_id)
    return Response(status_code=204)


# ---------------------------------------------------------------- blocks
@router.post("/lessons/{lesson_id}/blocks", response_model=BlockOut, status_code=201)
def add_block(lesson_id: str, data: BlockIn, me: Me, db: DB, position: int | None = Query(None, ge=1)):
    return svc.block_out(svc.add_block(db, me, lesson_id, data.block_type, data.config, position))


@router.put("/lessons/{lesson_id}/blocks/order", response_model=Ok)
def reorder_blocks(lesson_id: str, data: ReorderIn, me: Me, db: DB):
    svc.reorder_blocks(db, me, lesson_id, data.ids)
    return Ok()


@router.patch("/blocks/{block_id}", response_model=BlockOut)
def update_block(block_id: str, data: BlockIn, me: Me, db: DB):
    return svc.block_out(svc.update_block(db, me, block_id, data.config))


@router.delete("/blocks/{block_id}", status_code=204)
def delete_block(block_id: str, me: Me, db: DB):
    svc.delete_block(db, me, block_id)
    return Response(status_code=204)
