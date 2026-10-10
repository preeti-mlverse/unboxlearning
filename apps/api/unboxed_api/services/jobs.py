"""The background job queue.

The API only *enqueues* (and returns at once); a worker process (workers/worker.py) claims and runs jobs.
Properties built in from day one:
- retry with backoff for temporary failures, up to max_attempts;
- idempotency: the same idempotency_key never creates a second job;
- errors stored on the job (what, when, why);
- progress (0–100 plus a message) the app can poll;
- a crashed worker's job is reclaimed once its lock is older than LOCK_TIMEOUT.
"""
import logging
import traceback
from collections.abc import Callable
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..db import utcnow
from ..enums import JobStatus
from ..models import Job

log = logging.getLogger("unboxed.jobs")
LOCK_TIMEOUT = timedelta(minutes=10)


class RetryableError(Exception):
    """Raise for temporary problems (network, rate limit): the job is tried again later."""


class PermanentError(Exception):
    """Raise when retrying can't help (corrupt file): the job fails at once."""


Handler = Callable[[Session, Job, Callable[[int, str], None]], dict | None]
HANDLERS: dict[str, Handler] = {}


def handler(job_type: str):
    def deco(fn: Handler) -> Handler:
        HANDLERS[job_type] = fn
        return fn
    return deco


def enqueue(db: Session, job_type: str, *, entity_type: str | None = None, entity_id: str | None = None,
            payload: dict | None = None, idempotency_key: str | None = None, created_by: str | None = None,
            max_attempts: int = 3) -> Job:
    if idempotency_key:
        existing = db.scalar(select(Job).where(Job.idempotency_key == idempotency_key))
        if existing:
            return existing
    job = Job(job_type=job_type, entity_type=entity_type, entity_id=entity_id, payload=payload or {},
              idempotency_key=idempotency_key, created_by=created_by, max_attempts=max_attempts)
    db.add(job)
    db.flush()
    log.info("job queued", extra={"job_id": job.id, "job_type": job_type})
    return job


def claim(db: Session, worker_id: str) -> Job | None:
    """Take the next runnable job. FOR UPDATE SKIP LOCKED lets several workers share the table safely."""
    now = utcnow()
    q = (select(Job)
         .where(or_(Job.status == JobStatus.PENDING,
                    (Job.status == JobStatus.RUNNING) & (Job.locked_at < now - LOCK_TIMEOUT)),
                Job.run_after <= now)
         .order_by(Job.run_after, Job.created_at)
         .limit(1))
    if db.bind.dialect.name == "postgresql":
        q = q.with_for_update(skip_locked=True)
    job = db.scalar(q)
    if job is None:
        return None
    job.status, job.locked_by, job.locked_at = JobStatus.RUNNING, worker_id, now
    job.started_at = job.started_at or now
    job.attempt_count += 1
    db.commit()
    return job


def backoff(attempt: int) -> timedelta:
    return timedelta(seconds=min(15 * 2 ** (attempt - 1), 900))


def run(db: Session, job: Job) -> None:
    """Run one claimed job and record the outcome. Never raises."""
    fn = HANDLERS.get(job.job_type)

    def progress(pct: int, message: str = "") -> None:
        job.progress, job.progress_message = max(0, min(100, pct)), message[:200] or None
        db.commit()

    try:
        if fn is None:
            raise PermanentError(f"no handler registered for job type '{job.job_type}'")
        result = fn(db, job, progress)
        job.status, job.result, job.error = JobStatus.COMPLETED, result or {}, None
        job.progress, job.completed_at = 100, utcnow()
        log.info("job completed", extra={"job_id": job.id, "job_type": job.job_type})
    except Exception as exc:  # noqa: BLE001 — every failure is recorded on the job
        db.rollback()
        job = db.get(Job, job.id)
        permanent = isinstance(exc, PermanentError)
        job.error = f"{type(exc).__name__}: {exc}"[:2000]
        if not permanent and job.attempt_count < job.max_attempts:
            job.status, job.run_after = JobStatus.PENDING, utcnow() + backoff(job.attempt_count)
            log.warning("job failed, will retry", extra={"job_id": job.id, "job_type": job.job_type})
        else:
            job.status, job.completed_at = JobStatus.FAILED, utcnow()
            log.error("job failed: %s\n%s", job.error, traceback.format_exc(limit=5),
                      extra={"job_id": job.id, "job_type": job.job_type})
            on_failed = FAILURE_HOOKS.get(job.job_type)
            if on_failed:
                on_failed(db, job)
    finally:
        job.locked_by = job.locked_at = None
        db.commit()


FAILURE_HOOKS: dict[str, Callable[[Session, Job], None]] = {}


def on_failure(job_type: str):
    def deco(fn):
        FAILURE_HOOKS[job_type] = fn
        return fn
    return deco


def retry(db: Session, job: Job) -> Job:
    job.status, job.run_after, job.error = JobStatus.PENDING, utcnow(), None
    job.attempt_count, job.progress, job.progress_message, job.completed_at = 0, 0, None, None
    return job


def cancel(job: Job) -> Job:
    if job.status in (JobStatus.PENDING, JobStatus.FAILED):
        job.status, job.completed_at = JobStatus.CANCELLED, utcnow()
    return job
