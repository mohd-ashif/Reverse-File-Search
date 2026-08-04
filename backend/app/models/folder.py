from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.file import IndexedFile


class MonitoredFolder(TimestampMixin, Base):
    __tablename__ = "monitored_folders"

    path: Mapped[str] = mapped_column(String(1024), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    files: Mapped[list["IndexedFile"]] = relationship(back_populates="folder", cascade="all, delete-orphan")
