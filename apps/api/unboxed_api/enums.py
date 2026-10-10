"""Every status and type value in one place. The database enforces the same lists with CHECK constraints,
and the web app mirrors them in packages/shared-types."""
from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class TokenPurpose(StrEnum):
    VERIFY_EMAIL = "verify_email"
    RESET_PASSWORD = "reset_password"


class OrgType(StrEnum):
    SCHOOL = "school"
    UNIVERSITY = "university"
    COMPANY = "company"
    NGO = "ngo"
    INDEPENDENT_CREATOR = "independent_creator"


class OrgStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Role(StrEnum):
    CREATOR = "creator"
    LEARNER = "learner"
    ORG_ADMIN = "org_admin"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    REMOVED = "removed"


class CourseStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Visibility(StrEnum):
    ORGANIZATION = "organization"  # members of the owning workspace only
    PUBLIC = "public"  # any signed-in learner can enroll


class VersionStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class LessonStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentPurpose(StrEnum):
    SOURCE = "source"  # material a course is built from (Wave 1 ingests these)
    ASSET = "asset"  # an image used inside a lesson block


class EnrollmentStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProgressStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
