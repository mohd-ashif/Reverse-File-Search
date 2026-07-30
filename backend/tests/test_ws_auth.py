"""WebSocket auth on /api/v1/ws/scan/{scan_id}: no token, insufficient
permission, and authorized (including superadmin bypass) connections."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from app.auth.jwt import create_access_token
from app.auth.repository import UserRepository
from app.auth.security import hash_password


def _create_active_user(db_session: Session, email: str, is_superadmin: bool = False):
    user = UserRepository(db_session).create(
        email=email, hashed_password=hash_password("Str0ng!Passw0rd"), full_name="WS Test User"
    )
    user.is_active = True
    user.is_verified = True
    user.is_superadmin = is_superadmin
    db_session.commit()
    db_session.refresh(user)
    return user


def test_ws_connect_without_token_is_rejected(client: TestClient) -> None:
    try:
        with client.websocket_connect("/api/v1/ws/scan/some-scan-id") as ws:
            ws.receive_text()
        assert False, "expected the connection to be rejected"
    except WebSocketDisconnect:
        pass


def test_ws_connect_with_valid_token_missing_permission_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    user = _create_active_user(db_session, "ws-no-scan-perm@example.com")
    # Token deliberately omits folder.scan.
    token = create_access_token(user.id, None, ["folder.read"], ["Viewer"])

    try:
        with client.websocket_connect(f"/api/v1/ws/scan/some-scan-id?token={token}") as ws:
            ws.receive_text()
        assert False, "expected the connection to be rejected"
    except WebSocketDisconnect:
        pass


def test_ws_connect_with_folder_scan_permission_is_accepted(client: TestClient, db_session: Session) -> None:
    user = _create_active_user(db_session, "ws-with-scan-perm@example.com")
    token = create_access_token(user.id, None, ["folder.scan"], ["Manager"])

    with client.websocket_connect(f"/api/v1/ws/scan/some-scan-id?token={token}") as ws:
        # Connection accepted - no exception raised opening the context.
        assert ws is not None


def test_ws_connect_as_superadmin_is_accepted_without_explicit_perms(
    client: TestClient, db_session: Session
) -> None:
    user = _create_active_user(db_session, "ws-superadmin@example.com", is_superadmin=True)
    token = create_access_token(user.id, None, [], [])

    with client.websocket_connect(f"/api/v1/ws/scan/some-scan-id?token={token}") as ws:
        assert ws is not None
