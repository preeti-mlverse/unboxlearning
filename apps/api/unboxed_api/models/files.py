"""FILES: the database keeps the record and the storage path; the bytes live in private object storage."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, Timestamps, id_column
from ..enums import DocumentPurpose, DocumentStatus
from .common import one_of


class Document(Timestamps, Base):
    __tablename__ = "documents"
    __table_args__ = (one_of("processing_status", list(DocumentStatus)), one_of("purpose", list(DocumentPurpose)))

    id: Mapped[str] = id_column("doc")
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), index=True)
    course_id: Mapped[str | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), index=True)
    uploaded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(120))
    storage_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(BigInteger)
    checksum: Mapped[str] = mapped_column(String(64), index=True)  # sha256
    purpose: Mapped[str] = mapped_column(String(20), default=DocumentPurpose.SOURCE)
    processing_status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.UPLOADED)
    page_count: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
