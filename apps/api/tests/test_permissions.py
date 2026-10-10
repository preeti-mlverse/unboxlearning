from unboxed_api.models import User
from unboxed_api.services.permissions import P, Principal


def principal(roles, admin=False):
    return Principal(user=User(id="usr_x", email="x@example.com", is_platform_admin=admin), roles=roles)


def test_creator_permissions_are_scoped_to_their_workspace():
    p = principal({"org_a": {"creator"}})
    assert p.can(P.COURSE_CREATE, "org_a")
    assert not p.can(P.COURSE_CREATE, "org_b")
    assert not p.can(P.ORGANIZATION_MANAGE, "org_a")


def test_learner_cannot_edit_but_can_enroll_anywhere():
    p = principal({"org_a": {"learner"}})
    assert not p.can(P.COURSE_EDIT, "org_a")
    assert p.can(P.LEARNER_ENROLL, "org_a") and p.can(P.LEARNER_ENROLL, None)


def test_one_person_many_roles():
    p = principal({"school_a": {"creator"}, "company_b": {"learner"}, "own": {"org_admin", "creator"}})
    assert p.can(P.COURSE_EDIT, "school_a") and not p.can(P.COURSE_EDIT, "company_b")
    assert p.can(P.ORGANIZATION_MANAGE, "own")
    assert sorted(p.orgs_with(P.COURSE_CREATE)) == ["own", "school_a"]


def test_platform_admin_can_do_everything():
    p = principal({}, admin=True)
    assert p.can(P.ADMIN_VIEW) and p.can(P.COURSE_EDIT, "any_org") and p.is_member("any_org")
