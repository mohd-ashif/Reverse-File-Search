from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class FileTag(TimestampMixin, Base):
    """A single AI-classified category tag for a file (e.g. "Invoice", "HR").
    A file can have several tags; each (file, tag) pair is unique."""

    __tablename__ = "file_tags"
    __table_args__ = (UniqueConstraint("file_id", "tag", name="uq_file_tags_file_id_tag"),)

    file_id: Mapped[int] = mapped_column(ForeignKey("indexed_files.id", ondelete="CASCADE"), nullable=False)
    tag: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    file: Mapped["IndexedFile"] = relationship(back_populates="tags")
