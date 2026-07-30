"""Register/login flows against the real (rollback-transaction) DB, with the
mailer's SMTP-sending functions patched out so no real network call happens."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.repository import UserRepository
from app.core.config import settings

TEST_PASSWORD = "Str0ng!Passw0rd"


def _patch_mailer(monkeypatch) -> None:
    async def _noop(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr("app.auth.service.send_verification_email", _noop)
    monkeypatch.setattr("app.auth.service.send_login_alert_email", _noop)
    monkeypatch.setattr("app.auth.service.send_password_reset_email", _noop)


def _register(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "full_name": "Test User"},
    )
    assert response.status_code == 201


def test_register_creates_user_and_does_not_leak_token(client: TestClient, db_session: Session, monkeypatch) -> None:
    _patch_mailer(monkeypatch)
    email = "register-flow@example.com"

    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": TEST_PASSWORD, "full_name": "Register Flow"},
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"message"}
    assert "accessToken" not in body
    assert "refreshToken" not in body

    user = UserRepository(db_session).get_by_email(email)
    assert user is not None
    assert user.is_verified is False
    assert user.hashed_password != TEST_PASSWORD


def test_login_before_verification_fails(client: TestClient, monkeypatch) -> None:
    _patch_mailer(monkeypatch)
    email = "unverified-login@example.com"
    _register(client, email)

    response = client.post("/api/v1/auth/login", json={"email": email, "password": TEST_PASSWORD})

    assert response.status_code == 401


def test_login_after_verification_succeeds_with_expected_response_shape(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    _patch_mailer(monkeypatch)
    email = "verified-login@example.com"
    _register(client, email)

    user = UserRepository(db_session).get_by_email(email)
    user.is_verified = True
    db_session.commit()

    response = client.post("/api/v1/auth/login", json={"email": email, "password": TEST_PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "accessToken",
        "refreshToken",
        "expiresIn",
        "user",
        "permissions",
        "roles",
        "organization",
    }
    assert body["user"]["email"] == email
    assert isinstance(body["permissions"], list)
    assert settings.REFRESH_TOKEN_COOKIE_NAME in response.cookies


def test_repeated_wrong_password_locks_account(client: TestClient, db_session: Session, monkeypatch) -> None:
    _patch_mailer(monkeypatch)
    email = "lockout-test@example.com"
    _register(client, email)

    user = UserRepository(db_session).get_by_email(email)
    user.is_verified = True
    db_session.commit()

    max_attempts = settings.MAX_FAILED_LOGIN_ATTEMPTS
    last_response = None
    for attempt in range(1, max_attempts + 1):
        last_response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": "TotallyWrong!1"}
        )

    db_session.refresh(user)
    assert user.failed_login_count == max_attempts
    assert user.locked_until is not None

    # The Nth (lockout-triggering) attempt itself: the account is now locked,
    # but its failure_reason recorded at request time depends on whether the
    # lock was applied before or after this request completed. Either a 401
    # (bad password, lock applied afterwards) or 423 (already locked at the
    # start of this call) is acceptable/correct here - what matters is that
    # the account is provably locked afterwards (asserted above).
    assert last_response.status_code in (401, 423)

    # A subsequent attempt with the CORRECT password must still fail while locked.
    # NOTE: this is one more call to /auth/login within the same minute as the
    # lockout attempts above; MAX_FAILED_LOGIN_ATTEMPTS (5) equals the slowapi
    # rate limit (5/min) on this endpoint, so depending on exact timing this
    # call may be rejected by the rate limiter (429) instead of the lockout
    # check (423) - both are correct proof that login is blocked, so either is
    # accepted.
    final_response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": TEST_PASSWORD}
    )
    assert final_response.status_code in (423, 429)


def test_login_unknown_email_fails(client: TestClient, monkeypatch) -> None:
    _patch_mailer(monkeypatch)
    response = client.post(
        "/api/v1/auth/login", json={"email": "no-such-user@example.com", "password": TEST_PASSWORD}
    )
    assert response.status_code == 401
