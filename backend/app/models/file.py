import enum

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class FileType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "markdown"
    IMAGE = "image"
    EXCEL = "excel"
    UNKNOWN = "unknown"


class FileIndexStatus(str, enum.Enum):
    PENDING = "pending"
    EXTRACTED = "extracted"
    EMBEDDED = "embedded"
    FAILED = "failed"


class IndexedFile(TimestampMixin, Base):
    __tablename__ = "indexed_files"

    folder_id: Mapped[int] = mapped_column(ForeignKey("monitored_folders.id", ondelete="CASCADE"), nullable=False)
    absolute_path: Mapped[str] = mapped_column(String(2048), unique=True, index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    extension: Mapped[str] = mapped_column(String(32), nullable=False)
    file_type: Mapped[FileType] = mapped_column(Enum(FileType), default=FileType.UNKNOWN)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    mtime: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[FileIndexStatus] = mapped_column(Enum(FileIndexStatus), default=FileIndexStatus.PENDING)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    """AI-corrected OCR text (e.g. "Inv0ice" -> "Invoice"), populated only for
    image files whose text came from OCR. Null for every other file type,
    since their extraction doesn't go through OCR and has nothing to correct."""

    folder: Mapped["MonitoredFolder"] = relationship(back_populates="files")
    chunks: Mapped[list["FileChunk"]] = relationship(back_populates="file", cascade="all, delete-orphan")
    summary: Mapped["FileSummary | None"] = relationship(
        back_populates="file", cascade="all, delete-orphan", uselist=False
    )
    entities: Mapped["DocumentEntities | None"] = relationship(
        back_populates="file", cascade="all, delete-orphan", uselist=False
    )
    tags: Mapped[list["FileTag"]] = relationship(back_populates="file", cascade="all, delete-orphan")
