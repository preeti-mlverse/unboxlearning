"""/users/me and /organizations (workspaces)."""
from fastapi import APIRouter
from sqlalchemy import select

from ..deps import DB, Me
from ..enums import MembershipStatus, Role
from ..errors import not_found
from ..models import Membership, Organization, Profile, User
from ..schemas import LANGS, MemberOut, MeOut, OrganizationCreate, OrganizationOut, OrganizationUpdate, ProfileUpdate
from ..services import accounts, orgs
from ..services.permissions import P, load_principal

router = APIRouter(tags=["users"])


@router.get("/users/me", response_model=MeOut)
def get_me(me: Me, db: DB):
    return accounts.me(db, me)


@router.patch("/users/me", response_model=MeOut)
def update_me(data: ProfileUpdate, me: Me, db: DB):
    profile = db.get(Profile, me.id)
    for k, v in data.model_dump(exclude_unset=True).items():
        if v is None:
            continue
        if k == "preferred_language" and v not in LANGS:
            continue
        setattr(profile, k, v.strip() if isinstance(v, str) else v)
    db.flush()
    return accounts.me(db, me)


@router.post("/organizations", response_model=OrganizationOut, status_code=201)
def create_organization(data: OrganizationCreate, me: Me, db: DB):
    """Create a workspace. Its creator becomes its admin and a creator in it."""
    return orgs.create_workspace(db, me.user, data.name, data.type)


@router.get("/organizations", response_model=list[OrganizationOut])
def my_organizations(me: Me, db: DB):
    ids = list(me.roles)
    if not ids:
        return []
    return db.scalars(select(Organization).where(Organization.id.in_(ids)).order_by(Organization.created_at)).all()


def _org(db, me, org_id: str, permission: str) -> Organization:
    org = db.get(Organization, org_id)
    if org is None or not me.is_member(org_id):
        raise not_found("That workspace")
    me.require(permission, org_id)
    return org


@router.get("/organizations/{org_id}", response_model=OrganizationOut)
def get_organization(org_id: str, me: Me, db: DB):
    return _org(db, me, org_id, P.LESSON_VIEW) if me.is_member(org_id) else _org(db, me, org_id, P.ADMIN_VIEW)


@router.patch("/organizations/{org_id}", response_model=OrganizationOut)
def update_organization(org_id: str, data: OrganizationUpdate, me: Me, db: DB):
    org = _org(db, me, org_id, P.ORGANIZATION_MANAGE)
    for k, v in data.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(org, k, v.strip() if isinstance(v, str) else v)
    return org


@router.get("/organizations/{org_id}/members", response_model=list[MemberOut])
def members(org_id: str, me: Me, db: DB):
    _org(db, me, org_id, P.ORGANIZATION_VIEW_MEMBERS)
    rows = db.execute(select(Membership, User).join(User, User.id == Membership.user_id)
                      .where(Membership.organization_id == org_id, Membership.status == MembershipStatus.ACTIVE)
                      .order_by(Membership.joined_at)).all()
    out: dict[str, MemberOut] = {}
    for m, u in rows:
        item = out.setdefault(u.id, MemberOut(user_id=u.id, email=u.email, display_name=u.profile.display_name,
                                              roles=[], joined_at=m.joined_at))
        item.roles.append(Role(m.role))
    return list(out.values())


# re-export for the admin router
__all__ = ["router", "load_principal"]
