"""SYSTEM: background jobs. The table is the queue: workers claim rows with SELECT … FOR UPDATE SKIP LOCKED,
so a job runs once even with several workers, and a crashed worker's job is picked up again after its lock expires."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, id_column, utcnow
from ..enums import JobStatus
from .common import JSONType, one_of


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (one_of("status", list(JobStatus)), Index("ix_jobs_claim", "status", "run_after"),
                      Index("ix_jobs_entity", "entity_type", "entity_id"))

    id: Mapped[str] = id_column("job")
    job_type: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default=JobStatus.PENDING)
    entity_type: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONType)
    error: Mapped[str | None] = mapped_column(Text)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    progress_message: Mapped[str | None] = mapped_column(String(200))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    # the same key never creates a second job, so a double click or a retried request can't duplicate work
    idempotency_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())
    locked_by: Mapped[str | None] = mapped_column(String(80))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
