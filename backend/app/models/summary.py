from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class FileSummary(TimestampMixin, Base):
    __tablename__ = "file_summaries"

    file_id: Mapped[int] = mapped_column(
        ForeignKey("indexed_files.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    important_dates: Mapped[list[str]] = mapped_column(JSON, default=list)
    people: Mapped[list[str]] = mapped_column(JSON, default=list)
    organizations: Mapped[list[str]] = mapped_column(JSON, default=list)
    risks: Mapped[list[str]] = mapped_column(JSON, default=list)
    action_items: Mapped[list[str]] = mapped_column(JSON, default=list)
    model: Mapped[str] = mapped_column(String(128), nullable=False)

    file: Mapped["IndexedFile"] = relationship(back_populates="summary")
