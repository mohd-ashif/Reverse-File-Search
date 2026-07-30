from collections.abc import Generator

from app.auth.dependencies import (
    get_current_org_id,
    get_current_user,
    get_current_user_optional,
    get_current_user_ws,
    require_permission,
    require_role,
)
from app.db.session import get_db

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_user_optional",
    "get_current_user_ws",
    "get_current_org_id",
    "require_permission",
    "require_role",
]


def get_db_session() -> Generator:
    yield from get_db()
