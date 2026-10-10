from datetime import timedelta

from fastapi.testclient import TestClient

from unboxed_api.db import utcnow
from unboxed_api.models import Document, Job
from unboxed_api.services import jobs
from workers.worker import drain
from tests.conftest import PNG, build_course, signup, tiny_pdf


def upload(c, name, data, **form):
    return c.post("/documents", files={"file": (name, data)}, data=form)


def test_upload_queues_job_and_worker_processes_it(creator, db):
    r = upload(creator, "chapter-3.pdf", tiny_pdf(3))
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["processing_status"] == "queued" and doc["job_id"] and doc["title"] == "chapter-3"
    stored = db.get(Document, doc["id"])
    assert stored.storage_path == f"organizations/{doc['organization_id']}/documents/{doc['id']}/original.pdf"
    assert creator.get(f"/jobs/{doc['job_id']}").json()["status"] == "pending"
    assert drain("test-worker") == 1
    job = creator.get(f"/jobs/{doc['job_id']}").json()
    assert job["status"] == "completed" and job["progress"] == 100 and job["result"] == {"page_count": 3}
    after = creator.get(f"/documents/{doc['id']}").json()
    assert after["processing_status"] == "ready" and after["page_count"] == 3


def test_file_validation(creator):
    fake = upload(creator, "notes.pdf", b"this is not a pdf")
    assert fake.status_code == 400 and fake.json()["error"]["code"] == "FILE_CONTENT_MISMATCH"
    assert upload(creator, "virus.exe", b"MZ...").json()["error"]["code"] == "FILE_TYPE_NOT_ALLOWED"
    assert upload(creator, "empty.pdf", b"").json()["error"]["code"] == "FILE_EMPTY"
    assert upload(creator, "notes.md", "# Heading\nनमस्ते".encode()).status_code == 201


def test_size_limit(creator, monkeypatch):
    from unboxed_api.config import get_settings
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    r = upload(creator, "big.pdf", tiny_pdf())
    assert r.status_code == 413 and r.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_corrupt_pdf_fails_job_and_document(creator):
    doc = upload(creator, "broken.pdf", b"%PDF-1.7\nthis is not really a pdf").json()
    drain("w")
    after = creator.get(f"/documents/{doc['id']}").json()
    assert after["processing_status"] == "failed" and after["error"]
    job = creator.get(f"/jobs/{doc['job_id']}").json()
    assert job["status"] == "failed" and job["attempt_count"] == 1  # permanent errors don't retry


def test_private_files_need_permission_and_signed_url(app, creator, learner):
    doc = upload(creator, "policy.pdf", tiny_pdf()).json()
    assert learner.get(f"/documents/{doc['id']}").status_code == 404
    assert learner.post(f"/documents/{doc['id']}/download-url").status_code == 404
    assert signup(app, "educator").post(f"/documents/{doc['id']}/download-url").status_code == 404
    url = creator.post(f"/documents/{doc['id']}/download-url").json()["url"]
    anon = TestClient(app)
    got = anon.get(url)
    assert got.status_code == 200 and got.content.startswith(b"%PDF")
    tampered = url[:-3] + ("aaa" if not url.endswith("aaa") else "bbb")
    assert anon.get(tampered).status_code == 403


def test_image_asset_in_block(creator, learner):
    ids = build_course(creator)
    img = upload(creator, "diagram.png", PNG, purpose="asset").json()
    assert img["processing_status"] == "ready" and img["job_id"] is None
    assert upload(creator, "doc.pdf", tiny_pdf(), purpose="asset").json()["error"]["code"] == "FILE_TYPE_NOT_ALLOWED"
    r = creator.post(f"/lessons/{ids['lesson']}/blocks",
                     json={"block_type": "image", "config": {"document_id": img["id"], "alt": "Two carts"}})
    assert r.status_code == 201 and r.json()["media_path"].startswith("/files/")
    assert creator.get(r.json()["media_path"]).content == PNG


def test_documents_search_rename_delete(creator):
    a = upload(creator, "biology-ch3.pdf", tiny_pdf()).json()
    upload(creator, "sales-deck.pdf", tiny_pdf())
    assert [d["title"] for d in creator.get("/documents?q=bio").json()] == ["biology-ch3"]
    creator.patch(f"/documents/{a['id']}", json={"title": "Biology chapter 3"})
    assert creator.get(f"/documents/{a['id']}").json()["title"] == "Biology chapter 3"
    assert creator.delete(f"/documents/{a['id']}").status_code == 204
    assert len(creator.get("/documents").json()) == 1


def test_idempotent_enqueue_and_retry_with_backoff(db):
    a = jobs.enqueue(db, "test.flaky", idempotency_key="same-key")
    b = jobs.enqueue(db, "test.flaky", idempotency_key="same-key")
    db.commit()
    assert a.id == b.id
    calls = []

    @jobs.handler("test.flaky")
    def flaky(db, job, progress):
        calls.append(1)
        if len(calls) < 2:
            raise ConnectionError("provider timed out")
        return {"ok": True}

    drain("w")
    job = db.get(Job, a.id)
    db.refresh(job)
    assert job.status == "pending" and job.attempt_count == 1 and "timed out" in job.error
    assert job.run_after > utcnow()  # backed off
    job.run_after = utcnow() - timedelta(seconds=1)
    db.commit()
    drain("w")
    db.refresh(job)
    assert job.status == "completed" and job.attempt_count == 2 and job.error is None


def test_stale_running_job_is_reclaimed(db):
    job = jobs.enqueue(db, "test.noop")

    @jobs.handler("test.noop")
    def noop(db, job, progress):
        return {}

    job.status, job.locked_by, job.locked_at = "running", "dead-worker", utcnow() - timedelta(hours=1)
    db.commit()
    assert drain("w") == 1
    db.refresh(job)
    assert job.status == "completed"


def test_failed_job_retry_endpoint(creator):
    doc = upload(creator, "broken.pdf", b"%PDF-1.7\nnope").json()
    drain("w")
    r = creator.post(f"/jobs/{doc['job_id']}/retry")
    assert r.status_code == 200 and r.json()["status"] == "pending"
    assert creator.get(f"/documents/{doc['id']}").json()["processing_status"] == "queued"


def test_deleted_documents_can_be_restored(app, creator):
    doc = upload(creator, "handbook.pdf", tiny_pdf()).json()
    creator.delete(f"/documents/{doc['id']}")
    deleted = creator.get("/documents?deleted=true").json()
    assert [d["id"] for d in deleted] == [doc["id"]] and deleted[0]["deleted_at"]
    outsider = signup(app, "educator")
    assert outsider.post(f"/documents/{doc['id']}/restore").status_code == 404
    assert creator.post(f"/documents/{doc['id']}/restore").json()["deleted_at"] is None
    assert [d["id"] for d in creator.get("/documents").json()] == [doc["id"]]
    assert creator.get("/documents?deleted=true").json() == []
