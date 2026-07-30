"""End-to-end verification that route-level permission gating actually
works: no token -> 401, token missing the required permission -> 403,
token with the required permission -> 200.

The superadmin-bypass path is implicitly covered by every retrofitted test
that uses the `auth_client` fixture, so this file focuses specifically on
non-superadmin permission checks.
"""

from fastapi.testclient import TestClient

from app.auth.jwt import create_access_token
from app.auth.repository import UserRepository
from app.auth.security import hash_password


def _create_non_admin_user(db_session):
    user = UserRepository(db_session).create(
        email="test-viewer@example.test",
        hashed_password=hash_password("Test1234!"),
        full_name="Test Viewer",
    )
    user.is_active = True
    user.is_verified = True
    user.is_superadmin = False
    db_session.commit()
    db_session.refresh(user)
    return user


def test_list_folders_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/folders/")
    assert response.status_code == 401


def test_add_folder_without_folder_create_permission_returns_403(client: TestClient, db_session) -> None:
    user = _create_non_admin_user(db_session)
    # Token carries folder.read but deliberately omits folder.create.
    token = create_access_token(user.id, None, ["folder.read"], ["Viewer"])
    client.headers.update({"Authorization": f"Bearer {token}"})

    response = client.post("/api/v1/folders/", json={"path": "C:\\Invoices"})

    assert response.status_code == 403


def test_list_folders_with_folder_read_permission_returns_200(client: TestClient, db_session) -> None:
    user = _create_non_admin_user(db_session)
    token = create_access_token(user.id, None, ["folder.read"], ["Viewer"])
    client.headers.update({"Authorization": f"Bearer {token}"})

    response = client.get("/api/v1/folders/")

    assert response.status_code == 200
