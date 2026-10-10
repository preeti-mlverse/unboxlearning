"""The Foundation "definition of done" journey from the spec, end to end through the HTTP API:

CREATOR  sign up → create workspace → course → module → lesson → content → upload PDF → save draft → preview → publish
LEARNER  sign up → enroll → open course → open lesson → consume → complete → see progress
SYSTEM   private PDF stored → background job → job status → course version kept → permissions enforced → errors recorded
"""
from fastapi.testclient import TestClient

from workers.worker import drain
from tests.conftest import signup, tiny_pdf


def test_foundation_journey(app):
    # ---- creator
    creator = signup(app, "organization", name="Asha Rao", email="asha@school.example")
    assert creator.me["home"] == "onboarding"
    org = creator.post("/organizations", json={"name": "Green Valley Science", "type": "school"}).json()
    course = creator.post("/courses", json={"title": "Force and Laws of Motion", "description": "Physics basics",
                                            "organization_id": org["id"]}).json()
    module = creator.post(f"/courses/{course['id']}/modules", json={"title": "Newton's Laws"}).json()
    lesson = creator.post(f"/modules/{module['id']}/lessons", json={"title": "Newton's Second Law",
                                                                   "estimated_minutes": 6}).json()
    block = creator.get(f"/lessons/{lesson['id']}").json()["blocks"][0]
    creator.patch(f"/blocks/{block['id']}", json={"block_type": "text", "config": {
        "heading": "Push harder, speed up faster", "body": "Acceleration grows with force: **F = m × a**."}})
    doc = creator.post("/documents", files={"file": ("ncert-ch9.pdf", tiny_pdf(4))},
                       data={"course_id": course["id"]}).json()
    assert doc["processing_status"] == "queued"
    preview = creator.get(f"/lessons/{lesson['id']}").json()  # preview of the draft
    assert preview["blocks"][0]["config"]["heading"] == "Push harder, speed up faster"
    published = creator.post(f"/courses/{course['id']}/publish").json()
    assert published["status"] == "published"

    # ---- system: the PDF is private and processed in the background
    anon = TestClient(app)
    assert anon.get(f"/documents/{doc['id']}").status_code == 401
    drain("journey-worker")
    job = creator.get(f"/jobs/{doc['job_id']}").json()
    assert job["status"] == "completed"
    assert creator.get(f"/documents/{doc['id']}").json()["page_count"] == 4

    # ---- learner
    learner = signup(app, "learner", name="Ravi Kumar", email="ravi@example.com")
    catalog = learner.get("/catalog").json()
    assert [c["title"] for c in catalog] == ["Force and Laws of Motion"] and catalog[0]["estimated_minutes"] == 6
    enrollment = learner.post(f"/courses/{course['id']}/enroll").json()
    opened = learner.get(f"/learn/courses/{course['id']}").json()
    first = opened["modules"][0]["lessons"][0]["id"]
    seen = learner.get(f"/learn/courses/{course['id']}/lessons/{first}").json()
    assert "F = m × a" in seen["lesson"]["blocks"][0]["config"]["body"]
    learner.put(f"/enrollments/{enrollment['id']}/progress/{first}", json={"status": "in_progress"})
    done = learner.put(f"/enrollments/{enrollment['id']}/progress/{first}", json={"status": "completed"}).json()
    assert done["percent"] == 100 and done["status"] == "completed"
    assert learner.get("/enrollments").json()[0]["lessons_completed"] == 1

    # ---- system: versions and permissions hold
    assert learner.patch(f"/courses/{course['id']}", json={"title": "Hacked"}).status_code == 404
    assert learner.get(f"/documents/{doc['id']}").status_code == 404
    creator.post(f"/courses/{course['id']}/versions")
    assert learner.get("/enrollments").json()[0]["version_number"] == 1
