from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class FileChunk(TimestampMixin, Base):
    __tablename__ = "file_chunks"

    file_id: Mapped[int] = mapped_column(ForeignKey("indexed_files.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    chroma_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0)

    file: Mapped["IndexedFile"] = relationship(back_populates="chunks")
