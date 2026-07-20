from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.search_query import SearchQueryLog


class SearchQueryRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(self, query_text: str) -> None:
        query_text = query_text.strip()
        if not query_text:
            return
        self.db.add(SearchQueryLog(query_text=query_text))
        self.db.commit()

    def list_recent(self, limit: int = 5, prefix: str | None = None) -> list[str]:
        """Most recently issued distinct queries, newest first."""
        query = self.db.query(SearchQueryLog.query_text, func.max(SearchQueryLog.id).label("last_id")).group_by(
            SearchQueryLog.query_text
        )
        if prefix:
            query = query.filter(SearchQueryLog.query_text.ilike(f"{prefix}%"))
        rows = query.order_by(func.max(SearchQueryLog.id).desc()).limit(limit).all()
        return [row[0] for row in rows]

    def list_popular(self, limit: int = 5, prefix: str | None = None) -> list[str]:
        """Distinct queries ordered by how often they've been searched."""
        query = self.db.query(SearchQueryLog.query_text, func.count(SearchQueryLog.id).label("hits")).group_by(
            SearchQueryLog.query_text
        )
        if prefix:
            query = query.filter(SearchQueryLog.query_text.ilike(f"{prefix}%"))
        rows = query.order_by(func.count(SearchQueryLog.id).desc()).limit(limit).all()
        return [row[0] for row in rows]
