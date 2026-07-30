"""Organization CRUD, member management, and invitation endpoints."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.auth.permissions import PermissionCode, ROLE_PERMISSION_MATRIX
from app.auth.repository import RoleRepository, UserRepository
from app.auth.security import hash_password
from app.models.organization import Organization, OrganizationMemberStatus, OrganizationUser


def _patch_mailer(monkeypatch) -> None:
    async def _noop(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr("app.services.organization_service.send_invitation_email", _noop)
    monkeypatch.setattr("app.services.organization_service.send_role_changed_email", _noop)
    monkeypatch.setattr("app.auth.mailer.send_org_join_email", _noop)
    monkeypatch.setattr("app.auth.service.send_verification_email", _noop)


def _make_org(db_session: Session, name: str = "Acme Inc") -> Organization:
    org = Organization(name=name, slug=name.lower().replace(" ", "-"))
    db_session.add(org)
    db_session.flush()
    return org


def _make_member(
    db_session: Session,
    org: Organization,
    role_name: str,
    email: str,
    status: OrganizationMemberStatus = OrganizationMemberStatus.JOINED,
):
    role = RoleRepository(db_session).get_by_name(role_name)
    user = UserRepository(db_session).create(email=email, hashed_password=hash_password("Str0ng!Passw0rd"))
    user.is_active = True
    user.is_verified = True
    user.organization_id = org.id
    db_session.commit()
    db_session.refresh(user)

    db_session.add(
        OrganizationUser(organization_id=org.id, user_id=user.id, role_id=role.id, status=status, is_primary=True)
    )
    db_session.flush()

    perms = ROLE_PERMISSION_MATRIX[role_name]
    token = create_access_token(user.id, org.id, perms, [role_name])
    return user, token


def _client_as(client: TestClient, token: str) -> TestClient:
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_org_admin_can_update_settings(client: TestClient, db_session: Session, monkeypatch) -> None:
    _patch_mailer(monkeypatch)
    org = _make_org(db_session)
    _admin, token = _make_member(db_session, org, "Organization Admin", "admin@acme.com")
    admin_client = _client_as(client, token)

    response = admin_client.patch(f"/api/v1/organizations/{org.id}", json={"name": "Acme Corp"})

    assert response.status_code == 200
    assert response.json()["name"] == "Acme Corp"


def test_non_admin_cannot_update_settings(client: TestClient, db_session: Session, monkeypatch) -> None:
    _patch_mailer(monkeypatch)
    org = _make_org(db_session)
    _employee, token = _make_member(db_session, org, "Employee", "employee@acme.com")
    employee_client = _client_as(client, token)

    response = employee_client.patch(f"/api/v1/organizations/{org.id}", json={"name": "Hijacked"})

    assert response.status_code == 403


def test_invite_then_accept_assigns_selected_role(client: TestClient, db_session: Session, monkeypatch) -> None:
    _patch_mailer(monkeypatch)
    org = _make_org(db_session)
    _admin, token = _make_member(db_session, org, "Organization Admin", "admin2@acme.com")
    admin_client = _client_as(client, token)

    invite_response = admin_client.post(
        f"/api/v1/organizations/{org.id}/invite", json={"email": "newhire@acme.com", "role": "Manager"}
    )
    assert invite_response.status_code == 201
    assert invite_response.json()["status"] == "pending"

    # The API never returns the raw token (only its hash is persisted), so
    # overwrite the persisted hash with one derived from a known raw token to
    # exercise the accept flow end-to-end via the public endpoint.
    from app.auth.security import hash_token
    from app.models.organization import OrganizationInvitation

    invitation = db_session.query(OrganizationInvitation).filter_by(email="newhire@acme.com").one()
    raw_token = "known-raw-token-for-test"
    invitation.token_hash = hash_token(raw_token)
    db_session.commit()

    accept_response = client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_token, "password": "Str0ng!Passw0rd", "full_name": "New Hire"},
    )

    assert accept_response.status_code == 200
    body = accept_response.json()
    assert body["user"]["email"] == "newhire@acme.com"
    assert "Manager" in body["roles"]
    assert PermissionCode.FOLDER_CREATE in body["permissions"]


def test_invite_rejects_super_admin_role(client: TestClient, db_session: Session, monkeypatch) -> None:
    _patch_mailer(monkeypatch)
    org = _make_org(db_session)
    _admin, token = _make_member(db_session, org, "Organization Admin", "admin3@acme.com")
    admin_client = _client_as(client, token)

    response = admin_client.post(
        f"/api/v1/organizations/{org.id}/invite", json={"email": "wannabe@acme.com", "role": "Super Admin"}
    )

    assert response.status_code == 400


def test_change_member_role_rejects_super_admin_and_owner(client: TestClient, db_session: Session, monkeypatch) -> None:
    _patch_mailer(monkeypatch)
    org = _make_org(db_session)
    _admin, token = _make_member(db_session, org, "Organization Admin", "admin4@acme.com")
    owner, _owner_token = _make_member(
        db_session, org, "Super Admin", "owner@acme.com", status=OrganizationMemberStatus.OWNER
    )
    employee, _employee_token = _make_member(db_session, org, "Employee", "employee2@acme.com")
    admin_client = _client_as(client, token)

    owner_membership = (
        db_session.query(OrganizationUser)
        .filter_by(organization_id=org.id, user_id=owner.id)
        .one()
    )
    employee_membership = (
        db_session.query(OrganizationUser)
        .filter_by(organization_id=org.id, user_id=employee.id)
        .one()
    )

    reject_super_admin = admin_client.patch(
        f"/api/v1/members/{employee_membership.id}/role", json={"role": "Super Admin"}
    )
    assert reject_super_admin.status_code == 400

    reject_owner_change = admin_client.patch(
        f"/api/v1/members/{owner_membership.id}/role", json={"role": "Viewer"}
    )
    assert reject_owner_change.status_code == 400

    allowed_change = admin_client.patch(
        f"/api/v1/members/{employee_membership.id}/role", json={"role": "Manager"}
    )
    assert allowed_change.status_code == 200
    assert allowed_change.json()["role"] == "Manager"


def test_remove_member_rejects_owner(client: TestClient, db_session: Session, monkeypatch) -> None:
    _patch_mailer(monkeypatch)
    org = _make_org(db_session)
    _admin, token = _make_member(db_session, org, "Organization Admin", "admin5@acme.com")
    owner, _owner_token = _make_member(
        db_session, org, "Super Admin", "owner2@acme.com", status=OrganizationMemberStatus.OWNER
    )
    admin_client = _client_as(client, token)

    owner_membership = db_session.query(OrganizationUser).filter_by(organization_id=org.id, user_id=owner.id).one()

    response = admin_client.delete(f"/api/v1/members/{owner_membership.id}")
    assert response.status_code == 400
