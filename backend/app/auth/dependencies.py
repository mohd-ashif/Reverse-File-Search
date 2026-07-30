"""FastAPI dependencies for authentication/authorization.

`get_current_user` validates the Bearer access token, loads the user, and
stashes the decoded claims on `request.state.token_payload` so that
`require_permission`/`require_role` factories can check embedded
permissions/roles without an extra DB hit.
"""

from fastapi import Depends, HTTPException, Request, WebSocket
from sqlalchemy.orm import Session

from app.auth.jwt import TokenError, decode_token
from app.auth.repository import UserRepository
from app.db.session import get_db
from app.models.user import User


def _extract_bearer(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    return auth_header[len("Bearer ") :]


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _extract_bearer(request)
    try:
        payload = decode_token(token, expected_type="access")
    except TokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise HTTPException(status_code=401, detail="Invalid or inactive user")

    request.state.token_payload = payload
    return user


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Same as `get_current_user` but returns None instead of raising.

    For endpoints that behave differently for anonymous callers. Currently
    unused since every existing route requires auth, but implemented per
    spec for completeness/future use.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[len("Bearer ") :]
    try:
        payload = decode_token(token, expected_type="access")
    except TokenError:
        return None

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return None

    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        return None

    request.state.token_payload = payload
    return user


def require_permission(permission: str):
    def _dep(request: Request, user: User = Depends(get_current_user)) -> User:
        if user.is_superadmin:
            return user
        payload = getattr(request.state, "token_payload", {}) or {}
        perms = payload.get("perms", [])
        if permission not in perms:
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")
        return user

    return _dep


def get_current_org_id(request: Request, user: User = Depends(get_current_user)) -> int | None:
    """The org id embedded in the caller's access token.

    Superadmins (and any legacy/service token without an `org` claim) get
    `None`, which callers treat as "no tenant filter" - consistent with
    `require_permission`/`require_role` already bypassing checks entirely for
    `is_superadmin`. Every ordinary member's token carries a real org id since
    `AuthService.register`/`accept_invitation` always assign one.
    """
    payload = getattr(request.state, "token_payload", {}) or {}
    org_id = payload.get("org")
    return int(org_id) if org_id is not None else None


def require_role(role_name: str):
    def _dep(request: Request, user: User = Depends(get_current_user)) -> User:
        if user.is_superadmin:
            return user
        payload = getattr(request.state, "token_payload", {}) or {}
        roles = payload.get("roles", [])
        if role_name not in roles:
            raise HTTPException(status_code=403, detail=f"Requires role: {role_name}")
        return user

    return _dep


async def get_current_user_ws(websocket: WebSocket, db: Session) -> User | None:
    """WebSocket-flavored auth check.

    Reads the access token from `?token=` on the connection URL (browsers
    can't set custom headers on the WS handshake). Never raises
    HTTPException - on any failure it closes the socket with code 4401 and
    returns None. Callers must check this *before* accepting the connection.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return None

    try:
        payload = decode_token(token, expected_type="access")
    except TokenError:
        await websocket.close(code=4401)
        return None

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        await websocket.close(code=4401)
        return None

    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        await websocket.close(code=4401)
        return None

    websocket.state.token_payload = payload
    return user
