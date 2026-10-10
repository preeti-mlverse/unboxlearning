"""API data contracts. The web app's types are generated from the OpenAPI document these produce
(packages/shared-types), so the two sides can't drift apart: rename a field here and the web build fails."""
import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .enums import (CourseStatus, DocumentPurpose, DocumentStatus, EnrollmentStatus, JobStatus, LessonStatus, OrgType,
                    ProgressStatus, Role, VersionStatus, Visibility)


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Ok(BaseModel):
    ok: bool = True
    message: str | None = None


def _clean(v: str) -> str:
    return re.sub(r"\s+", " ", v).strip()


def _tidy(v):
    return _clean(v) if v else v


def _strong(v: str) -> str:
    if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
        raise ValueError("Use at least 8 characters, with letters and numbers")
    return v


# ---------------------------------------------------------------- auth
SignupIntent = Literal["learner", "educator", "school", "ngo", "organization"]
LANGS = {"en", "hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa", "or", "ur", "es", "fr", "ar"}


class SignupIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: SignupIntent = "learner"
    phone: str | None = None
    org: str | None = Field(default=None, max_length=160)
    language: str = "en"
    agree: bool

    @field_validator("name", "org")
    @classmethod
    def tidy(cls, v):
        return _clean(v) if v else v

    @field_validator("phone")
    @classmethod
    def indian_mobile(cls, v):
        if not v:
            return None
        digits = re.sub(r"\D", "", v)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if not re.fullmatch(r"[6-9]\d{9}", digits):
            raise ValueError("Enter a 10-digit Indian mobile number")
        return digits

    @field_validator("password")
    @classmethod
    def strong_enough(cls, v):
        return _strong(v)

    @field_validator("language")
    @classmethod
    def known_language(cls, v):
        return v if v in LANGS else "en"

    @field_validator("agree")
    @classmethod
    def must_agree(cls, v):
        if not v:
            raise ValueError("Please accept the Terms and Privacy policy")
        return v


class LoginIn(BaseModel):
    identifier: str = Field(min_length=3, max_length=254, description="Email or 10-digit mobile number")
    password: str = Field(min_length=1, max_length=128)
    remember: bool = True


class EmailIn(BaseModel):
    email: EmailStr


class TokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class ResetPasswordIn(TokenIn):
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_enough(cls, v):
        return _strong(v)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong_enough(cls, v):
        return _strong(v)


# ---------------------------------------------------------------- users & organizations
class MembershipOut(BaseModel):
    organization_id: str
    organization_name: str
    organization_slug: str
    organization_type: OrgType
    roles: list[Role]


class ProfileOut(Out):
    display_name: str
    avatar_url: str | None
    preferred_language: str
    timezone: str
    signup_intent: str | None


class MeOut(BaseModel):
    id: str
    email: str
    phone: str | None
    email_verified: bool
    is_platform_admin: bool
    profile: ProfileOut
    memberships: list[MembershipOut]
    # where the app should send this person after logging in: "create", "learn" or "onboarding"
    home: Literal["create", "learn", "onboarding", "admin"]


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    preferred_language: str | None = None
    timezone: str | None = Field(default=None, max_length=60)
    avatar_url: str | None = Field(default=None, max_length=500)


class AuthOut(BaseModel):
    user: MeOut
    redirect_to: str
    message: str | None = None


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    type: OrgType = OrgType.INDEPENDENT_CREATOR

    @field_validator("name")
    @classmethod
    def tidy(cls, v):
        return _tidy(v)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    type: OrgType | None = None


class OrganizationOut(Out):
    id: str
    name: str
    slug: str
    type: OrgType
    status: str
    created_at: datetime


class MemberOut(BaseModel):
    user_id: str
    email: str
    display_name: str
    roles: list[Role]
    joined_at: datetime


# ---------------------------------------------------------------- courses
class CourseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=5000)
    organization_id: str | None = None
    visibility: Visibility = Visibility.PUBLIC

    @field_validator("title")
    @classmethod
    def tidy(cls, v):
        return _tidy(v)


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    visibility: Visibility | None = None


class VersionOut(Out):
    id: str
    version_number: int
    status: VersionStatus
    created_at: datetime
    published_at: datetime | None


class CourseSummary(Out):
    id: str
    organization_id: str
    deleted_at: datetime | None = None
    title: str
    description: str
    status: CourseStatus
    visibility: Visibility
    current_draft_version_id: str | None
    current_published_version_id: str | None
    created_at: datetime
    updated_at: datetime
    module_count: int = 0
    lesson_count: int = 0
    published_version_number: int | None = None
    has_unpublished_changes: bool = False


class BlockIn(BaseModel):
    block_type: str = Field(min_length=1, max_length=40)
    config: dict[str, Any] = Field(default_factory=dict)


class BlockOut(Out):
    id: str
    lineage_id: str
    block_type: str
    position: int
    config: dict[str, Any]
    # for image blocks: a short-lived signed path (relative to the API root) to fetch the picture
    media_path: str | None = None


class LessonCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    estimated_minutes: int = Field(default=5, ge=1, le=240)


class LessonUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    estimated_minutes: int | None = Field(default=None, ge=1, le=240)
    status: LessonStatus | None = None


class LessonOut(Out):
    id: str
    lineage_id: str
    module_id: str
    title: str
    description: str
    position: int
    estimated_minutes: int
    status: LessonStatus
    block_count: int = 0


class LessonDetail(LessonOut):
    blocks: list[BlockOut]


class ModuleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


class ModuleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class ModuleOut(Out):
    id: str
    lineage_id: str
    title: str
    description: str
    position: int
    lessons: list[LessonOut]


class ReorderIn(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=500)


class CourseDetail(CourseSummary):
    version: VersionOut | None  # the version these modules belong to
    modules: list[ModuleOut]
    versions: list[VersionOut]
    can_edit: bool = False


class PublishIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------- documents
class DocumentOut(Out):
    id: str
    organization_id: str
    course_id: str | None
    title: str
    original_filename: str
    mime_type: str
    file_size: int
    checksum: str
    purpose: DocumentPurpose
    processing_status: DocumentStatus
    page_count: int | None
    error: str | None
    created_at: datetime
    job_id: str | None = None


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    course_id: str | None = None


class SignedUrlOut(BaseModel):
    url: str
    expires_in: int


# ---------------------------------------------------------------- learning
class CatalogCourse(BaseModel):
    id: str
    title: str
    description: str
    organization_name: str
    module_count: int
    lesson_count: int
    estimated_minutes: int
    enrollment_id: str | None = None


class LessonProgressOut(BaseModel):
    lesson_id: str
    status: ProgressStatus
    started_at: datetime | None
    completed_at: datetime | None


class EnrollmentOut(BaseModel):
    id: str
    course_id: str
    course_title: str
    course_version_id: str
    version_number: int
    status: EnrollmentStatus
    enrolled_at: datetime
    completed_at: datetime | None
    lessons_total: int
    lessons_completed: int
    percent: int
    next_lesson_id: str | None
    last_activity_at: datetime | None
    newer_version_available: bool = False


class LearnCourseOut(EnrollmentOut):
    description: str
    modules: list[ModuleOut]
    progress: list[LessonProgressOut]


class ProgressUpdate(BaseModel):
    status: Literal["in_progress", "completed"]


class LearnLessonOut(BaseModel):
    lesson: LessonDetail
    module_title: str
    course_id: str
    course_title: str
    enrollment_id: str
    progress: LessonProgressOut
    previous_lesson_id: str | None
    next_lesson_id: str | None
    position: int
    total: int


# ---------------------------------------------------------------- jobs & admin
class JobOut(Out):
    id: str
    job_type: str
    status: JobStatus
    entity_type: str | None
    entity_id: str | None
    progress: int
    progress_message: str | None
    attempt_count: int
    max_attempts: int
    error: str | None
    result: dict | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class AdminUserOut(BaseModel):
    id: str
    email: str
    display_name: str
    status: str
    email_verified: bool
    is_platform_admin: bool
    organizations: int
    created_at: datetime
    last_login_at: datetime | None


class AdminOrgOut(OrganizationOut):
    members: int = 0
    courses: int = 0


class AdminStats(BaseModel):
    users: int
    organizations: int
    courses: int
    published_courses: int
    enrollments: int
    documents: int
    jobs_pending: int
    jobs_failed: int


class Page(BaseModel):
    total: int
    items: list[Any]
