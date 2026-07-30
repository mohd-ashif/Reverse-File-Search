"""GET/PATCH /me, session listing/isolation, and session revocation ownership checks."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.auth.repository import RefreshTokenRepository, UserRepository
from app.auth.security import hash_password
from app.main import app


@pytest.fixture(autouse=True)
def _patch_mailer(monkeypatch) -> None:
    async def _noop(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr("app.auth.service.send_login_alert_email", _noop)
    monkeypatch.setattr("app.auth.service.send_verification_email", _noop)
    monkeypatch.setattr("app.auth.service.send_password_reset_email", _noop)


def _create_verified_user(db_session: Session, email: str, full_name: str = "Me Test"):
    user = UserRepository(db_session).create(
        email=email, hashed_password=hash_password("Str0ng!Passw0rd"), full_name=full_name
    )
    user.is_active = True
    user.is_verified = True
    db_session.commit()
    db_session.refresh(user)
    return user


def _login_as(client: TestClient, email: str, password: str = "Str0ng!Passw0rd") -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    body = response.json()
    client.headers.update({"Authorization": f"Bearer {body['accessToken']}"})
    return body


def test_get_me_returns_authenticated_user(client: TestClient, db_session: Session) -> None:
    user = _create_verified_user(db_session, "get-me@example.com")
    token = create_access_token(user.id, None, [], [])
    client.headers.update({"Authorization": f"Bearer {token}"})

    response = client.get("/api/v1/me/")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user.id
    assert body["email"] == "get-me@example.com"
    assert body["full_name"] == "Me Test"
    assert "hashed_password" not in body


def test_patch_me_updates_and_persists_allowed_fields(client: TestClient, db_session: Session) -> None:
    user = _create_verified_user(db_session, "patch-me@example.com")
    token = create_access_token(user.id, None, [], [])
    client.headers.update({"Authorization": f"Bearer {token}"})

    response = client.patch(
        "/api/v1/me/", json={"full_name": "Updated Name", "phone": "+1-555-0100"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Updated Name"
    assert body["phone"] == "+1-555-0100"

    follow_up = client.get("/api/v1/me/")
    assert follow_up.json()["full_name"] == "Updated Name"
    assert follow_up.json()["phone"] == "+1-555-0100"

    db_session.refresh(user)
    assert user.full_name == "Updated Name"
    assert user.phone == "+1-555-0100"


def test_list_sessions_only_shows_own_sessions(client: TestClient, db_session: Session) -> None:
    _create_verified_user(db_session, "sessions-user-a@example.com")
    _create_verified_user(db_session, "sessions-user-b@example.com")

    login_a = _login_as(client, "sessions-user-a@example.com")

    sessions_response = client.get("/api/v1/me/sessions")
    assert sessions_response.status_code == 200
    sessions = sessions_response.json()
    assert len(sessions) == 1

    # Log in as user B on a fresh (unauthenticated) client to create a second,
    # independent session that must not leak into user A's session list.
    second_client = TestClient(app)
    login_b_response = second_client.post(
        "/api/v1/auth/login",
        json={"email": "sessions-user-b@example.com", "password": "Str0ng!Passw0rd"},
    )
    assert login_b_response.status_code == 200
    second_client.headers.update(
        {"Authorization": f"Bearer {login_b_response.json()['accessToken']}"}
    )

    sessions_after = client.get("/api/v1/me/sessions")
    assert len(sessions_after.json()) == 1  # still just user A's own session

    b_sessions = second_client.get("/api/v1/me/sessions")
    assert len(b_sessions.json()) == 1  # user B sees only their own


def test_revoke_session_revokes_refresh_token_and_blocks_future_refresh(
    client: TestClient, db_session: Session
) -> None:
    login_body = _login_as(client, *_two(db_session, "revoke-own-session@example.com"))

    sessions = client.get("/api/v1/me/sessions").json()
    assert len(sessions) == 1
    session_id = sessions[0]["id"]

    delete_response = client.delete(f"/api/v1/me/sessions/{session_id}")
    assert delete_response.status_code == 204

    refresh_repo = RefreshTokenRepository(db_session)
    from app.auth.security import hash_token

    token_row = refresh_repo.get_by_hash(hash_token(login_body["refreshToken"]))
    assert token_row.revoked_at is not None

    refresh_attempt = client.post(
        "/api/v1/auth/refresh", headers={"X-Requested-With": "XMLHttpRequest"}
    )
    assert refresh_attempt.status_code == 401


def _two(db_session: Session, email: str) -> tuple[str, str]:
    _create_verified_user(db_session, email)
    return email, "Str0ng!Passw0rd"


def test_revoke_session_of_a_different_user_returns_404(client: TestClient, db_session: Session) -> None:
    _create_verified_user(db_session, "owner-user@example.com")
    _create_verified_user(db_session, "other-user@example.com")

    owner_login = _login_as(client, "owner-user@example.com")
    owner_sessions = client.get("/api/v1/me/sessions").json()
    owner_session_id = owner_sessions[0]["id"]

    # Switch the same client to be authenticated as the OTHER user, then try
    # to delete the owner's session id.
    other_login = client.post(
        "/api/v1/auth/login",
        json={"email": "other-user@example.com", "password": "Str0ng!Passw0rd"},
    )
    assert other_login.status_code == 200
    client.headers.update({"Authorization": f"Bearer {other_login.json()['accessToken']}"})

    response = client.delete(f"/api/v1/me/sessions/{owner_session_id}")

    assert response.status_code == 404
