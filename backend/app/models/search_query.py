from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin


class SearchQueryLog(TimestampMixin, Base):
    """One row per search submitted through /search/ or /search/stream. Purely
    an append-only log used to derive "recent" and "popular" search
    suggestions — never read back as search results themselves."""

    __tablename__ = "search_query_logs"

    query_text: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
