"""/catalog, /enrollments and progress: everything a learner does."""
from fastapi import APIRouter, Query, Response

from ..deps import DB, Me
from ..schemas import CatalogCourse, EnrollmentOut, LearnCourseOut, LearnLessonOut, ProgressUpdate
from ..services import learning as svc

router = APIRouter(tags=["learning"])


@router.get("/catalog", response_model=list[CatalogCourse])
def catalog(me: Me, db: DB, q: str | None = Query(None, max_length=200)):
    """Published courses this person can join."""
    return svc.catalog(db, me, q)


@router.post("/courses/{course_id}/enroll", response_model=EnrollmentOut, status_code=201)
def enroll(course_id: str, me: Me, db: DB):
    return svc.enrollment_out(db, svc.enroll(db, me, course_id))


@router.get("/enrollments", response_model=list[EnrollmentOut])
def my_enrollments(me: Me, db: DB):
    return svc.my_enrollments(db, me)


@router.get("/learn/courses/{course_id}", response_model=LearnCourseOut)
def learn_course(course_id: str, me: Me, db: DB):
    return svc.learn_course(db, me, course_id)


@router.get("/learn/courses/{course_id}/lessons/{lesson_id}", response_model=LearnLessonOut)
def learn_lesson(course_id: str, lesson_id: str, me: Me, db: DB):
    return svc.learn_lesson(db, me, course_id, lesson_id)


@router.put("/enrollments/{enrollment_id}/progress/{lesson_id}", response_model=EnrollmentOut)
def set_progress(enrollment_id: str, lesson_id: str, data: ProgressUpdate, me: Me, db: DB):
    return svc.set_progress(db, me, enrollment_id, lesson_id, data.status)


@router.post("/enrollments/{enrollment_id}/switch-to-latest", response_model=EnrollmentOut)
def switch_to_latest(enrollment_id: str, me: Me, db: DB):
    return svc.switch_to_latest(db, me, enrollment_id)


@router.delete("/enrollments/{enrollment_id}", status_code=204)
def leave(enrollment_id: str, me: Me, db: DB):
    svc.leave(db, me, enrollment_id)
    return Response(status_code=204)
