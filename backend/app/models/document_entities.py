from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin


class DocumentEntities(TimestampMixin, Base):
    """Structured business/financial fields extracted from a file's text
    (invoice number, vendor, GST, etc.). Populated automatically after
    indexing; any field not found in the document is left null — never
    guessed or fabricated."""

    __tablename__ = "document_entities"

    file_id: Mapped[int] = mapped_column(
        ForeignKey("indexed_files.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    invoice_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gst: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pan: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount: Mapped[str | None] = mapped_column(String(128), nullable=True)
    date: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    bank: Mapped[str | None] = mapped_column(String(255), nullable=True)
    po_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contract_number: Mapped[str | None] = mapped_column(String(255), nullable=True)

    file: Mapped["IndexedFile"] = relationship(back_populates="entities")
