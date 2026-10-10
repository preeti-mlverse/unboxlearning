"""IDENTITY: who is using UnboxEd. Authentication data (users, sessions, tokens) is kept apart from
the human-facing profile."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base, Timestamps, id_column, utcnow
from ..enums import TokenPurpose, UserStatus
from .common import one_of


class User(Timestamps, Base):
    __tablename__ = "users"
    __table_args__ = (one_of("status", list(UserStatus)),)

    id: Mapped[str] = id_column("usr")
    # "local" today; an external provider (e.g. Supabase) later sets auth_provider + auth_user_id
    auth_provider: Mapped[str] = mapped_column(String(20), default="local")
    auth_user_id: Mapped[str | None] = mapped_column(String(120), unique=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default=UserStatus.ACTIVE)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False, lazy="joined")


class Profile(Timestamps, Base):
    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    timezone: Mapped[str] = mapped_column(String(60), default="Asia/Kolkata")
    # what the person said they were when signing up (learner, educator, school, ngo, organization)
    signup_intent: Mapped[str | None] = mapped_column(String(20))

    user: Mapped[User] = relationship(back_populates="profile")


class AuthSession(Base):
    """One row per logged-in device. Only a hash of the refresh token is stored, and it rotates on every use."""
    __tablename__ = "auth_sessions"

    id: Mapped[str] = id_column("ses")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    remember: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())


class AuthToken(Base):
    """Single-use tokens sent by email: verify an address, or reset a password."""
    __tablename__ = "auth_tokens"
    __table_args__ = (one_of("purpose", list(TokenPurpose)),)

    id: Mapped[str] = id_column("tok")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    # the same email also carries a 6-digit code (typed into the app); only its hash is stored
    code_hash: Mapped[str | None] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())
