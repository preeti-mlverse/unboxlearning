from tests.conftest import build_course, signup


def test_create_course_starts_with_draft_v1(creator):
    r = creator.post("/courses", json={"title": "  Force   and Laws of Motion ", "description": "Seed"})
    assert r.status_code == 201
    course = r.json()
    assert course["title"] == "Force and Laws of Motion" and course["status"] == "draft"
    detail = creator.get(f"/courses/{course['id']}").json()
    assert detail["version"]["version_number"] == 1 and detail["version"]["status"] == "draft"
    assert detail["can_edit"] is True


def test_build_modules_lessons_blocks_and_reorder(creator):
    ids = build_course(creator)
    m2 = creator.post(f"/courses/{ids['course']}/modules", json={"title": "Momentum"}).json()
    detail = creator.get(f"/courses/{ids['course']}").json()
    assert [m["title"] for m in detail["modules"]] == ["Newton's Laws", "Momentum"]
    assert creator.put(f"/courses/{ids['course']}/modules/order", json={"ids": [m2["id"], ids["module"]]}).status_code == 200
    detail = creator.get(f"/courses/{ids['course']}").json()
    assert [m["title"] for m in detail["modules"]] == ["Momentum", "Newton's Laws"]
    # blocks: add one before the first, then check order
    b = creator.post(f"/lessons/{ids['lesson']}/blocks?position=1", json={"block_type": "text", "config": {"body": "Intro"}})
    assert b.status_code == 201
    lesson = creator.get(f"/lessons/{ids['lesson']}").json()
    assert [x["config"]["body"] for x in lesson["blocks"]] == ["Intro", "F = m × a."]


def test_block_validation(creator):
    ids = build_course(creator)
    r = creator.post(f"/lessons/{ids['lesson']}/blocks", json={"block_type": "hologram", "config": {}})
    assert r.status_code == 400 and r.json()["error"]["code"] == "UNKNOWN_BLOCK_TYPE"
    r = creator.post(f"/lessons/{ids['lesson']}/blocks", json={"block_type": "image", "config": {"document_id": "doc_x"}})
    assert r.status_code == 400 and "alt" in r.json()["error"]["details"]["fields"]


def test_learner_and_other_workspaces_cannot_touch_course(app, creator, learner):
    ids = build_course(creator)
    other = signup(app, "educator", name="Meera Shah")
    for c in (learner, other):
        assert c.get(f"/courses/{ids['course']}").status_code == 404  # existence isn't revealed
        assert c.patch(f"/courses/{ids['course']}", json={"title": "Hacked"}).status_code == 404
        assert c.patch(f"/blocks/{ids['block']}", json={"block_type": "text", "config": {"body": "x"}}).status_code == 404
    assert learner.post("/courses", json={"title": "Mine"}).json()["error"]["code"] == "NO_WORKSPACE"
    assert other.get("/courses").json() == []


def test_publish_blocked_until_ready(creator):
    course = creator.post("/courses", json={"title": "Empty"}).json()
    r = creator.post(f"/courses/{course['id']}/publish")
    assert r.status_code == 400 and r.json()["error"]["code"] == "PUBLISH_BLOCKED"
    m = creator.post(f"/courses/{course['id']}/modules", json={"title": "M"}).json()
    creator.post(f"/modules/{m['id']}/lessons", json={"title": "L"})
    problems = creator.post(f"/courses/{course['id']}/publish").json()["error"]["details"]["problems"]
    assert problems == ["Lesson 'L' has no content yet."]


def test_publish_then_edit_makes_new_version(creator):
    ids = build_course(creator)
    pub = creator.post(f"/courses/{ids['course']}/publish").json()
    assert pub["status"] == "published" and pub["current_draft_version_id"] is None and pub["can_edit"] is False
    v1 = pub["current_published_version_id"]
    # published content is locked
    r = creator.patch(f"/blocks/{ids['block']}", json={"block_type": "text", "config": {"body": "changed"}})
    assert r.status_code == 409 and r.json()["error"]["code"] == "VERSION_LOCKED"
    # start a draft: deep copy with the same lineage
    v2 = creator.post(f"/courses/{ids['course']}/versions").json()
    assert v2["version_number"] == 2 and v2["status"] == "draft"
    draft = creator.get(f"/courses/{ids['course']}").json()
    assert draft["has_unpublished_changes"] is True
    new_lesson = draft["modules"][0]["lessons"][0]
    assert new_lesson["id"] != ids["lesson"]
    old = creator.get(f"/lessons/{ids['lesson']}").json()
    assert new_lesson["lineage_id"] == old["lineage_id"]
    new_block = creator.get(f"/lessons/{new_lesson['id']}").json()["blocks"][0]
    creator.patch(f"/blocks/{new_block['id']}", json={"block_type": "text", "config": {"body": "F = ma, revised."}})
    assert creator.get(f"/lessons/{ids['lesson']}").json()["blocks"][0]["config"]["body"] == "F = m × a."  # v1 untouched
    pub2 = creator.post(f"/courses/{ids['course']}/publish").json()
    statuses = {v["version_number"]: v["status"] for v in pub2["versions"]}
    assert statuses == {1: "archived", 2: "published"}
    assert pub2["current_published_version_id"] != v1


def test_discard_draft(creator):
    ids = build_course(creator)
    creator.post(f"/courses/{ids['course']}/publish")
    creator.post(f"/courses/{ids['course']}/versions")
    assert creator.delete(f"/courses/{ids['course']}/draft").status_code == 204
    assert creator.get(f"/courses/{ids['course']}").json()["current_draft_version_id"] is None


def test_search_and_soft_delete(creator):
    build_course(creator, "Force and Laws of Motion")
    other = creator.post("/courses", json={"title": "Cell biology"}).json()
    assert [c["title"] for c in creator.get("/courses?q=force").json()] == ["Force and Laws of Motion"]
    assert creator.delete(f"/courses/{other['id']}").status_code == 204
    assert [c["title"] for c in creator.get("/courses").json()] == ["Force and Laws of Motion"]
    assert creator.get(f"/courses/{other['id']}").status_code == 404
