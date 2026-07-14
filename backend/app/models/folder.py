from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class MonitoredFolder(TimestampMixin, Base):
    __tablename__ = "monitored_folders"

    path: Mapped[str] = mapped_column(String(1024), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    files: Mapped[list["IndexedFile"]] = relationship(back_populates="folder", cascade="all, delete-orphan")
