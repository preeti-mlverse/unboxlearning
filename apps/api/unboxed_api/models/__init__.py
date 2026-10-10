"""All tables, grouped by domain: identity, organization, content, files, learning, system.

Importing this package registers every model on Base.metadata (Alembic relies on that)."""
from .identity import AuthSession, AuthToken, Profile, User
from .organization import Membership, Organization
from .content import Course, CourseVersion, Lesson, LessonBlock, Module
from .files import Document
from .learning import Enrollment, LessonProgress
from .system import Job

__all__ = ["User", "Profile", "AuthSession", "AuthToken", "Organization", "Membership", "Course", "CourseVersion",
           "Module", "Lesson", "LessonBlock", "Document", "Enrollment", "LessonProgress", "Job"]
