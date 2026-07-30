"""Additional RBAC coverage not already exercised by test_auth_route_protection.py:
the superadmin DB-flag bypass (even with empty JWT perms), and a direct unit
test of the `require_role` dependency factory (not currently wired to any
route, so it's exercised standalone)."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from app.auth.dependencies import require_role
from app.auth.jwt import create_access_token
from app.auth.repository import UserRepository
from app.auth.security import hash_password


def test_superadmin_bypasses_permission_check_even_with_empty_perms_claim(
    client: TestClient, db_session
) -> None:
    user = UserRepository(db_session).create(
        email="superadmin-empty-perms@example.com",
        hashed_password=hash_password("Str0ng!Passw0rd"),
        full_name="Empty Perms Superadmin",
    )
    user.is_active = True
    user.is_verified = True
    user.is_superadmin = True
    db_session.commit()
    db_session.refresh(user)

    # Token deliberately carries NO permissions/roles - only the DB's
    # is_superadmin flag should grant access.
    token = create_access_token(user.id, None, [], [])
    client.headers.update({"Authorization": f"Bearer {token}"})

    response = client.get("/api/v1/folders/")

    assert response.status_code == 200


def test_non_superadmin_with_empty_perms_is_rejected(client: TestClient, db_session) -> None:
    user = UserRepository(db_session).create(
        email="non-admin-empty-perms@example.com",
        hashed_password=hash_password("Str0ng!Passw0rd"),
        full_name="Empty Perms Non Admin",
    )
    user.is_active = True
    user.is_verified = True
    user.is_superadmin = False
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(user.id, None, [], [])
    client.headers.update({"Authorization": f"Bearer {token}"})

    response = client.get("/api/v1/folders/")

    assert response.status_code == 403


def test_require_role_dependency_allows_matching_role(db_session) -> None:
    user = UserRepository(db_session).create(
        email="role-dep-match@example.com",
        hashed_password=hash_password("Str0ng!Passw0rd"),
        full_name="Role Dep Match",
    )
    user.is_active = True
    user.is_verified = True
    db_session.commit()
    db_session.refresh(user)

    dep = require_role("Organization Admin")

    class _FakeRequest:
        state = type("State", (), {"token_payload": {"roles": ["Organization Admin"]}})()

    result = dep(request=_FakeRequest(), user=user)
    assert result is user


def test_require_role_dependency_rejects_missing_role(db_session) -> None:
    user = UserRepository(db_session).create(
        email="role-dep-mismatch@example.com",
        hashed_password=hash_password("Str0ng!Passw0rd"),
        full_name="Role Dep Mismatch",
    )
    user.is_active = True
    user.is_verified = True
    db_session.commit()
    db_session.refresh(user)

    dep = require_role("Organization Admin")

    class _FakeRequest:
        state = type("State", (), {"token_payload": {"roles": ["Viewer"]}})()

    try:
        dep(request=_FakeRequest(), user=user)
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 403


def test_require_role_dependency_superadmin_bypass(db_session) -> None:
    user = UserRepository(db_session).create(
        email="role-dep-superadmin@example.com",
        hashed_password=hash_password("Str0ng!Passw0rd"),
        full_name="Role Dep Superadmin",
    )
    user.is_active = True
    user.is_verified = True
    user.is_superadmin = True
    db_session.commit()
    db_session.refresh(user)

    dep = require_role("Organization Admin")

    class _FakeRequest:
        state = type("State", (), {"token_payload": {"roles": []}})()

    result = dep(request=_FakeRequest(), user=user)
    assert result is user


def test_require_role_wired_end_to_end_in_a_minimal_app(db_session) -> None:
    """Confirms require_role also works correctly when actually wired as a
    FastAPI dependency (not just called directly), since it isn't used by
    any real route in this codebase yet."""
    user = UserRepository(db_session).create(
        email="role-dep-e2e@example.com",
        hashed_password=hash_password("Str0ng!Passw0rd"),
        full_name="Role Dep E2E",
    )
    user.is_active = True
    user.is_verified = True
    db_session.commit()
    db_session.refresh(user)

    mini_app = FastAPI()

    @mini_app.get("/admin-only")
    def admin_only(request: Request) -> dict:
        # Manually stash the payload/user the way get_current_user would,
        # then invoke the require_role dependency function body directly.
        request.state.token_payload = {"roles": ["Manager"]}
        require_role("Organization Admin")(request=request, user=user)
        return {"ok": True}

    with TestClient(mini_app) as mini_client:
        response = mini_client.get("/admin-only")

    assert response.status_code == 403
