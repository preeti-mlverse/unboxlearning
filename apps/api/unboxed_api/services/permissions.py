"""Authorization in one place: roles grant permissions, and every check goes through `can()` / `require()`.

Roles come from organization memberships (never from anything the browser sends). Platform admins can
do everything. Routes never write their own role checks."""
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import MembershipStatus, Role
from ..errors import forbidden
from ..models import Membership, User


class P:
    COURSE_CREATE = "course.create"
    COURSE_EDIT = "course.edit"
    COURSE_PUBLISH = "course.publish"
    COURSE_VIEW_DRAFT = "course.view_draft"
    DOCUMENT_UPLOAD = "document.upload"
    DOCUMENT_VIEW = "document.view"
    LESSON_VIEW = "lesson.view"
    LEARNER_ENROLL = "learner.enroll"
    ASSESSMENT_SUBMIT = "assessment.submit"
    ORGANIZATION_MANAGE = "organization.manage"
    ORGANIZATION_VIEW_MEMBERS = "organization.view_members"
    ADMIN_VIEW = "admin.view"


CREATOR_PERMS = {P.COURSE_CREATE, P.COURSE_EDIT, P.COURSE_PUBLISH, P.COURSE_VIEW_DRAFT, P.DOCUMENT_UPLOAD,
                 P.DOCUMENT_VIEW, P.LESSON_VIEW}
LEARNER_PERMS = {P.LESSON_VIEW, P.LEARNER_ENROLL, P.ASSESSMENT_SUBMIT}
ORG_ADMIN_PERMS = {P.ORGANIZATION_MANAGE, P.ORGANIZATION_VIEW_MEMBERS, P.COURSE_VIEW_DRAFT, P.DOCUMENT_VIEW, P.LESSON_VIEW}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    Role.CREATOR: CREATOR_PERMS,
    Role.LEARNER: LEARNER_PERMS,
    Role.ORG_ADMIN: ORG_ADMIN_PERMS,
}

# Things any signed-in person may do anywhere (a learner without a workspace can still enroll in public courses).
EVERYONE = {P.LEARNER_ENROLL, P.ASSESSMENT_SUBMIT}


@dataclass
class Principal:
    user: User
    roles: dict[str, set[str]] = field(default_factory=dict)  # organization_id -> roles

    @property
    def id(self) -> str:
        return self.user.id

    @property
    def is_admin(self) -> bool:
        return bool(self.user.is_platform_admin)

    def permissions(self, organization_id: str | None) -> set[str]:
        perms = set(EVERYONE)
        for role in self.roles.get(organization_id or "", set()):
            perms |= ROLE_PERMISSIONS.get(role, set())
        return perms

    def can(self, permission: str, organization_id: str | None = None) -> bool:
        return self.is_admin or permission in self.permissions(organization_id)

    def require(self, permission: str, organization_id: str | None = None) -> None:
        if not self.can(permission, organization_id):
            raise forbidden()

    def is_member(self, organization_id: str) -> bool:
        return self.is_admin or bool(self.roles.get(organization_id))

    def orgs_with(self, permission: str) -> list[str]:
        return [org for org in self.roles if permission in self.permissions(org)]


def load_principal(db: Session, user: User) -> Principal:
    rows = db.execute(select(Membership.organization_id, Membership.role)
                      .where(Membership.user_id == user.id, Membership.status == MembershipStatus.ACTIVE)).all()
    roles: dict[str, set[str]] = {}
    for org_id, role in rows:
        roles.setdefault(org_id, set()).add(role)
    return Principal(user=user, roles=roles)
