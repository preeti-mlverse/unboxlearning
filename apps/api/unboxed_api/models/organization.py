"""ORGANIZATION: ownership boundaries. Roles live on memberships, so one person can be a creator in one
workspace and a learner in another."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, Timestamps, id_column, utcnow
from ..enums import MembershipStatus, OrgStatus, OrgType, Role
from .common import one_of


class Organization(Timestamps, Base):
    __tablename__ = "organizations"
    __table_args__ = (one_of("type", list(OrgType)), one_of("status", list(OrgStatus)))

    id: Mapped[str] = id_column("org")
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    type: Mapped[str] = mapped_column(String(30), default=OrgType.INDEPENDENT_CREATOR)
    status: Mapped[str] = mapped_column(String(20), default=OrgStatus.ACTIVE)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization")


class Membership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", "role"),
                      one_of("role", list(Role)), one_of("status", list(MembershipStatus)))

    id: Mapped[str] = id_column("mem")
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default=MembershipStatus.ACTIVE)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())

    organization: Mapped[Organization] = relationship(back_populates="memberships")
