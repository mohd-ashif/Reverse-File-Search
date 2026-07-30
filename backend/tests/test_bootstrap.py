"""Bootstrap super-admin rules (Rule 1/Rule 2 of the org-onboarding spec):
first-ever registrant becomes Super Admin + owns a new default org; every
later registrant becomes an Employee inside that same default org.

`UserRepository.count` is monkeypatched rather than relying on the shared
test database actually having zero rows, since that precondition can't be
guaranteed across a real (non-empty) Postgres instance.
"""

from sqlalchemy.orm import Session

from app.auth.repository import UserRepository
from app.auth.service import AuthService
from app.models.organization import OrganizationMemberStatus, OrganizationUser


def _patch_mailer(monkeypatch) -> None:
    async def _noop(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr("app.auth.service.send_verification_email", _noop)


def test_first_user_becomes_super_admin_and_owns_new_org(db_session: Session, monkeypatch) -> None:
    _patch_mailer(monkeypatch)
    monkeypatch.setattr(UserRepository, "count", lambda self: 0)

    user = AuthService(db_session).register(email="first@example.com", password="Str0ng!Passw0rd")

    assert user.is_superadmin is True
    assert user.is_platform_owner is True
    assert user.organization_id is not None

    org = user.organization
    assert org.name == "My Organization"
    assert org.is_platform_owner_org is True

    membership = (
        db_session.query(OrganizationUser)
        .filter(OrganizationUser.user_id == user.id, OrganizationUser.organization_id == org.id)
        .one()
    )
    assert membership.status == OrganizationMemberStatus.OWNER
    assert membership.is_primary is True

    role_names = AuthService(db_session).role_repo.get_role_names_for_user(user.id, organization_id=org.id)
    assert role_names == ["Super Admin"]


def test_second_user_becomes_employee_in_the_default_org(db_session: Session, monkeypatch) -> None:
    _patch_mailer(monkeypatch)

    monkeypatch.setattr(UserRepository, "count", lambda self: 0)
    first_user = AuthService(db_session).register(email="owner@example.com", password="Str0ng!Passw0rd")
    default_org_id = first_user.organization_id

    monkeypatch.setattr(UserRepository, "count", lambda self: 1)
    second_user = AuthService(db_session).register(email="second@example.com", password="Str0ng!Passw0rd")

    assert second_user.is_superadmin is False
    assert second_user.is_platform_owner is False
    assert second_user.organization_id == default_org_id

    membership = (
        db_session.query(OrganizationUser)
        .filter(OrganizationUser.user_id == second_user.id, OrganizationUser.organization_id == default_org_id)
        .one()
    )
    assert membership.status == OrganizationMemberStatus.JOINED

    role_names = AuthService(db_session).role_repo.get_role_names_for_user(second_user.id, organization_id=default_org_id)
    assert role_names == ["Employee"]
