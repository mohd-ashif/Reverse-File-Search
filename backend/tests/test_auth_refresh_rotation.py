"""Refresh-token rotation, reuse detection (full family revoke), and expiry."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.jwt import create_refresh_token
from app.auth.repository import RefreshTokenRepository, UserRepository
from app.auth.security import hash_password, hash_token
from app.models.refresh_token import RefreshToken

EMAIL = "refresh-rotation@example.com"
PASSWORD = "Str0ng!Passw0rd"


def _create_verified_user(db_session: Session):
    user = UserRepository(db_session).create(
        email=EMAIL, hashed_password=hash_password(PASSWORD), full_name="Refresh Test"
    )
    user.is_active = True
    user.is_verified = True
    db_session.commit()
    db_session.refresh(user)
    return user


def _login(client: TestClient, db_session: Session) -> dict:
    _create_verified_user(db_session)
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 200
    return response.json()


def test_refresh_rotates_tokens_and_revokes_old_row(client: TestClient, db_session: Session) -> None:
    login_body = _login(client, db_session)
    old_refresh_token = login_body["refreshToken"]
    old_hash = hash_token(old_refresh_token)

    refresh_response = client.post(
        "/api/v1/auth/refresh", headers={"X-Requested-With": "XMLHttpRequest"}
    )

    assert refresh_response.status_code == 200
    new_body = refresh_response.json()
    assert new_body["accessToken"] != login_body["accessToken"]
    assert new_body["refreshToken"] != old_refresh_token

    refresh_repo = RefreshTokenRepository(db_session)
    old_row = refresh_repo.get_by_hash(old_hash)
    assert old_row is not None
    assert old_row.revoked_at is not None
    assert old_row.replaced_by_id is not None

    new_row = refresh_repo.get_by_hash(hash_token(new_body["refreshToken"]))
    assert new_row is not None
    assert new_row.id == old_row.replaced_by_id
    assert new_row.family_id == old_row.family_id


def test_reusing_a_revoked_refresh_token_revokes_entire_family(client: TestClient, db_session: Session) -> None:
    login_body = _login(client, db_session)
    original_token = login_body["refreshToken"]
    original_hash = hash_token(original_token)

    original_row = RefreshTokenRepository(db_session).get_by_hash(original_hash)
    family_id = original_row.family_id

    # Rotate once - original becomes revoked, a new row takes its place.
    first_refresh = client.post(
        "/api/v1/auth/refresh", headers={"X-Requested-With": "XMLHttpRequest"}
    )
    assert first_refresh.status_code == 200
    rotated_token = first_refresh.json()["refreshToken"]

    # Now reuse the ORIGINAL (already-revoked) token via the cookie jar: set the
    # cookie back to the original token to simulate an attacker replaying it.
    client.cookies.set("refresh_token", original_token)
    reuse_response = client.post(
        "/api/v1/auth/refresh", headers={"X-Requested-With": "XMLHttpRequest"}
    )
    assert reuse_response.status_code == 401

    # The entire family must now be revoked, including the row that WAS valid
    # (the one issued by the first rotation).
    all_family_rows = (
        db_session.query(RefreshToken).filter(RefreshToken.family_id == family_id).all()
    )
    assert len(all_family_rows) >= 2
    assert all(row.revoked_at is not None for row in all_family_rows)

    # And using the token that was the valid rotated one now also fails.
    client.cookies.set("refresh_token", rotated_token)
    second_reuse_response = client.post(
        "/api/v1/auth/refresh", headers={"X-Requested-With": "XMLHttpRequest"}
    )
    assert second_reuse_response.status_code == 401


def test_expired_refresh_token_rejected_without_rotating(client: TestClient, db_session: Session) -> None:
    user = _create_verified_user(db_session)

    now = datetime.now(timezone.utc)
    expired_token, _jti, _expires_at = create_refresh_token(user_id=user.id, family_id="expired-family")
    RefreshTokenRepository(db_session).create(
        user_id=user.id,
        token_hash=hash_token(expired_token),
        family_id="expired-family",
        expires_at=now - timedelta(days=1),
    )

    client.cookies.set("refresh_token", expired_token)
    response = client.post(
        "/api/v1/auth/refresh", headers={"X-Requested-With": "XMLHttpRequest"}
    )

    assert response.status_code == 401

    row = RefreshTokenRepository(db_session).get_by_hash(hash_token(expired_token))
    assert row.revoked_at is None
