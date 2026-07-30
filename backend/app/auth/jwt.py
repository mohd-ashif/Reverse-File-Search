"""RS256 JWT creation/verification for access and refresh tokens.

Framework-agnostic: this module never raises HTTPException. Callers in
app/auth/dependencies.py (a later phase) translate TokenError into HTTP
responses.
"""

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jose import jwt
from jose.exceptions import JWTError

from app.core.config import settings

_BACKEND_DIR = Path(__file__).resolve().parents[2]


def _read_key(path_setting: str, label: str) -> str:
    path = Path(path_setting)
    if not path.is_absolute():
        path = _BACKEND_DIR / path
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"Could not read {label} at '{path}'. "
            "Run `python scripts/generate_jwt_keys.py` from the backend/ directory to generate it."
        ) from exc


_PRIVATE_KEY: str = _read_key(settings.JWT_PRIVATE_KEY_PATH, "JWT private key")
_PUBLIC_KEY: str = _read_key(settings.JWT_PUBLIC_KEY_PATH, "JWT public key")


class TokenError(Exception):
    """Raised for any JWT decode/validation failure (expired, malformed, wrong type, bad signature)."""


def create_access_token(
    user_id: int,
    org_id: int | None,
    permissions: list[str],
    roles: list[str],
) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "type": "access",
        "org": org_id,
        "perms": permissions,
        "roles": roles,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(claims, key=_PRIVATE_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int, family_id: str) -> tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    claims = {
        "sub": str(user_id),
        "type": "refresh",
        "family": family_id,
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    encoded = jwt.encode(claims, key=_PRIVATE_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded, jti, expires_at


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, key=_PUBLIC_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise TokenError(f"Invalid token: {exc}") from exc

    if payload.get("type") != expected_type:
        raise TokenError(f"Expected token type '{expected_type}', got '{payload.get('type')}'.")

    return payload
