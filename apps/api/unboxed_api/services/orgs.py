"""Workspaces (organizations) and memberships."""
import re
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import MembershipStatus, OrgType, Role
from ..models import Membership, Organization, User

# what someone picked on the sign-up form → the kind of workspace we make for them
INTENT_TO_ORG = {"educator": OrgType.INDEPENDENT_CREATOR, "school": OrgType.SCHOOL, "ngo": OrgType.NGO,
                 "organization": OrgType.COMPANY}


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]
    return slug or "workspace"


def unique_slug(db: Session, name: str) -> str:
    base = slugify(name)
    slug = base
    while db.scalar(select(Organization.id).where(Organization.slug == slug)):
        slug = f"{base}-{secrets.token_hex(2)}"
    return slug


def add_role(db: Session, org_id: str, user_id: str, role: Role) -> Membership:
    m = db.scalar(select(Membership).where(Membership.organization_id == org_id, Membership.user_id == user_id,
                                           Membership.role == role))
    if m is None:
        m = Membership(organization_id=org_id, user_id=user_id, role=role)
        db.add(m)
    m.status = MembershipStatus.ACTIVE
    return m


def create_workspace(db: Session, owner: User, name: str, org_type: str) -> Organization:
    """The person who creates a workspace administers it and can create courses in it."""
    org = Organization(name=name, slug=unique_slug(db, name), type=org_type, created_by=owner.id)
    db.add(org)
    db.flush()
    add_role(db, org.id, owner.id, Role.ORG_ADMIN)
    add_role(db, org.id, owner.id, Role.CREATOR)
    db.flush()
    return org


def default_workspace_name(intent: str, person: str, org: str | None) -> str | None:
    if org:
        return org
    if intent == "educator":
        return f"{person.split()[0]}'s workspace"
    return None  # schools, NGOs and organizations name theirs in onboarding
