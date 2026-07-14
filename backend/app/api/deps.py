from collections.abc import Generator

from app.db.session import get_db

__all__ = ["get_db"]


def get_db_session() -> Generator:
    yield from get_db()
