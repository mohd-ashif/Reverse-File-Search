"""Password hashing (Argon2id) and generic token hashing utilities."""

import hashlib

from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__type="id",
    argon2__time_cost=3,
    argon2__memory_cost=65536,
    argon2__parallelism=4,
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_token(raw_token: str) -> str:
    """SHA-256 hex digest used for at-rest storage of refresh/reset/verification tokens."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
