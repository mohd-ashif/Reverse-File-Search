from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.auth.middleware import limiter
from app.db.session import engine, get_db
from app.main import app


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> Generator[None, None, None]:
    """slowapi's in-memory limiter storage is process-wide, so without this
    reset, request counts from one test (e.g. repeated /auth/login calls to
    trigger account lockout) would bleed into the next test and cause
    order-dependent 429s. Reset before and after each test for safety."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """A DB session wrapped in an outer transaction that is always rolled
    back, so integration tests can hit the real database without leaving
    data behind."""
    connection = engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestingSessionLocal()

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess: Session, trans: object) -> None:
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def test_org(db_session: Session):
    """A default `Organization` row - every `monitored_folders`/`indexed_files`
    row requires a non-null `organization_id` FK, so any test that creates
    folders/files (directly or via a service) needs one of these."""
    from app.models.organization import Organization

    org = Organization(name="Test Org", slug="test-org")
    db_session.add(org)
    db_session.flush()
    return org


@pytest.fixture()
def auth_client(client: TestClient, db_session: Session, test_org) -> TestClient:
    """A TestClient pre-authenticated as a superadmin user, so every
    permission check passes - use for endpoint tests that aren't
    specifically testing RBAC itself."""
    from app.auth.jwt import create_access_token
    from app.auth.repository import UserRepository
    from app.auth.security import hash_password

    user = UserRepository(db_session).create(
        email="test-superadmin@example.test",
        hashed_password=hash_password("Test1234!"),
        full_name="Test Superadmin",
    )
    user.is_active = True
    user.is_verified = True
    user.is_superadmin = True
    user.organization_id = test_org.id
    db_session.commit()
    db_session.refresh(user)

    # Mirrors what AuthService._issue_token_pair actually embeds for any real
    # login (org=user.organization_id) - empty perms/roles are fine since
    # is_superadmin bypasses permission/role checks regardless.
    token = create_access_token(user.id, test_org.id, [], [])
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
