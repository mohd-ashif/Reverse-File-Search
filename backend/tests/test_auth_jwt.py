"""Access/refresh token round-trips, expiry, tampering, and wrong-type checks."""

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt as jose_jwt

from app.auth import jwt as auth_jwt
from app.auth.jwt import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import settings


def test_access_token_round_trip_preserves_claims() -> None:
    token = create_access_token(
        user_id=42, org_id=7, permissions=["folder.read", "file.read"], roles=["Viewer"]
    )

    payload = decode_token(token, expected_type="access")

    assert payload["sub"] == "42"
    assert payload["org"] == 7
    assert payload["perms"] == ["folder.read", "file.read"]
    assert payload["roles"] == ["Viewer"]
    assert payload["type"] == "access"


def test_refresh_token_round_trip() -> None:
    token, jti, expires_at = create_refresh_token(user_id=42, family_id="fam-123")

    payload = decode_token(token, expected_type="refresh")

    assert payload["sub"] == "42"
    assert payload["family"] == "fam-123"
    assert payload["jti"] == jti
    assert payload["type"] == "refresh"
    assert expires_at > datetime.now(timezone.utc)


def _craft_expired_token(claims_overrides: dict) -> str:
    """Hand-crafts a token with a past `exp` using the same private key/algorithm
    that app.auth.jwt loads, so it verifies (signature-wise) but is expired."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "1",
        "type": "access",
        "org": None,
        "perms": [],
        "roles": [],
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
        "jti": "expired-jti",
    }
    claims.update(claims_overrides)
    return jose_jwt.encode(claims, key=auth_jwt._PRIVATE_KEY, algorithm=settings.JWT_ALGORITHM)


def test_decode_expired_token_raises() -> None:
    token = _craft_expired_token({})

    with pytest.raises(TokenError):
        decode_token(token, expected_type="access")


def test_decode_tampered_signature_raises() -> None:
    token = create_access_token(user_id=1, org_id=None, permissions=[], roles=[])
    # Flip a character somewhere in the signature segment (last part after final dot).
    header_payload, signature = token.rsplit(".", 1)
    flipped_char = "A" if signature[-1] != "A" else "B"
    tampered = f"{header_payload}.{flipped_char}{signature[1:]}"

    with pytest.raises(TokenError):
        decode_token(tampered, expected_type="access")


def test_decode_wrong_expected_type_raises() -> None:
    token = create_access_token(user_id=1, org_id=None, permissions=[], roles=[])

    with pytest.raises(TokenError):
        decode_token(token, expected_type="refresh")


def test_decode_garbage_raises() -> None:
    with pytest.raises(TokenError):
        decode_token("this.is.not-a-jwt", expected_type="access")

    with pytest.raises(TokenError):
        decode_token("complete-garbage", expected_type="access")
