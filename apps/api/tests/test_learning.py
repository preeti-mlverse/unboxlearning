from tests.conftest import build_course, signup


def publish_two_lessons(creator):
    ids = build_course(creator)
    l2 = creator.post(f"/modules/{ids['module']}/lessons", json={"title": "Newton's Third Law"}).json()
    b = creator.get(f"/lessons/{l2['id']}").json()["blocks"][0]
    creator.patch(f"/blocks/{b['id']}", json={"block_type": "text", "config": {"body": "Every action…"}})
    creator.post(f"/courses/{ids['course']}/publish")
    return ids, l2["id"]


def test_catalog_shows_only_published_visible_courses(app, creator, learner):
    draft = creator.post("/courses", json={"title": "Unfinished"}).json()
    ids, _ = publish_two_lessons(creator)
    private = build_course(creator, "Staff handbook")
    creator.patch(f"/courses/{private['course']}", json={"visibility": "organization"})
    creator.post(f"/courses/{private['course']}/publish")
    titles = [c["title"] for c in learner.get("/catalog").json()]
    assert titles == ["Force and Laws of Motion"]
    assert learner.post(f"/courses/{draft['id']}/enroll").json()["error"]["code"] == "NOT_PUBLISHED"
    assert learner.post(f"/courses/{private['course']}/enroll").status_code == 404
    # members of the workspace do see its private courses
    assert "Staff handbook" in [c["title"] for c in creator.get("/catalog").json()]


def test_enroll_learn_complete(creator, learner):
    ids, l2 = publish_two_lessons(creator)
    e = learner.post(f"/courses/{ids['course']}/enroll").json()
    assert e["lessons_total"] == 2 and e["percent"] == 0
    assert learner.post(f"/courses/{ids['course']}/enroll").json()["id"] == e["id"]  # idempotent
    course = learner.get(f"/learn/courses/{ids['course']}").json()
    first = course["modules"][0]["lessons"][0]["id"]
    lesson = learner.get(f"/learn/courses/{ids['course']}/lessons/{first}").json()
    assert lesson["lesson"]["blocks"][0]["config"]["body"] == "F = m × a."
    assert lesson["next_lesson_id"] and lesson["previous_lesson_id"] is None and lesson["position"] == 1
    learner.put(f"/enrollments/{e['id']}/progress/{first}", json={"status": "in_progress"})
    r = learner.put(f"/enrollments/{e['id']}/progress/{first}", json={"status": "completed"}).json()
    assert r["lessons_completed"] == 1 and r["percent"] == 50 and r["next_lesson_id"] == lesson["next_lesson_id"]
    r = learner.put(f"/enrollments/{e['id']}/progress/{lesson['next_lesson_id']}", json={"status": "completed"}).json()
    assert r["status"] == "completed" and r["percent"] == 100 and r["completed_at"]
    assert learner.get("/enrollments").json()[0]["percent"] == 100


def test_progress_is_private_and_version_bound(app, creator, learner):
    ids, _ = publish_two_lessons(creator)
    e = learner.post(f"/courses/{ids['course']}/enroll").json()
    nosy = signup(app, "learner")
    assert nosy.put(f"/enrollments/{e['id']}/progress/{ids['lesson']}", json={"status": "completed"}).status_code == 404
    assert nosy.get(f"/learn/courses/{ids['course']}").json()["error"]["code"] == "NOT_ENROLLED"
    # a lesson from another course can't be marked
    other = build_course(creator, "Other")
    assert learner.put(f"/enrollments/{e['id']}/progress/{other['lesson']}", json={"status": "completed"}).status_code == 404


def test_republish_keeps_learners_on_their_version_until_they_switch(creator, learner):
    ids, l2 = publish_two_lessons(creator)
    e = learner.post(f"/courses/{ids['course']}/enroll").json()
    learner.put(f"/enrollments/{e['id']}/progress/{ids['lesson']}", json={"status": "completed"})
    # creator edits lesson 1's text and adds a third lesson in version 2
    creator.post(f"/courses/{ids['course']}/versions")
    draft = creator.get(f"/courses/{ids['course']}").json()
    lessons = draft["modules"][0]["lessons"]
    b = creator.get(f"/lessons/{lessons[0]['id']}").json()["blocks"][0]
    creator.patch(f"/blocks/{b['id']}", json={"block_type": "text", "config": {"body": "Revised: F = ma"}})
    l3 = creator.post(f"/modules/{draft['modules'][0]['id']}/lessons", json={"title": "Momentum"}).json()
    b3 = creator.get(f"/lessons/{l3['id']}").json()["blocks"][0]
    creator.patch(f"/blocks/{b3['id']}", json={"block_type": "text", "config": {"body": "p = mv"}})
    creator.post(f"/courses/{ids['course']}/publish")

    mine = learner.get("/enrollments").json()[0]
    assert mine["version_number"] == 1 and mine["newer_version_available"] is True and mine["lessons_total"] == 2
    seen = learner.get(f"/learn/courses/{ids['course']}/lessons/{ids['lesson']}").json()
    assert seen["lesson"]["blocks"][0]["config"]["body"] == "F = m × a."  # still the version they enrolled in

    switched = learner.post(f"/enrollments/{e['id']}/switch-to-latest").json()
    assert switched["version_number"] == 2 and switched["lessons_total"] == 3
    assert switched["lessons_completed"] == 1  # finished lesson carried over by lineage
    assert switched["newer_version_available"] is False


def test_leave_and_rejoin(creator, learner):
    ids, _ = publish_two_lessons(creator)
    e = learner.post(f"/courses/{ids['course']}/enroll").json()
    assert learner.delete(f"/enrollments/{e['id']}").status_code == 204
    assert learner.get("/enrollments").json() == []
    assert learner.post(f"/courses/{ids['course']}/enroll").json()["status"] == "active"
