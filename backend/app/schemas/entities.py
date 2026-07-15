from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentEntitiesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_id: int
    invoice_number: str | None
    vendor: str | None
    customer: str | None
    gst: str | None
    pan: str | None
    amount: str | None
    date: str | None
    email: str | None
    phone: str | None
    address: str | None
    bank: str | None
    po_number: str | None
    contract_number: str | None
    created_at: datetime
    updated_at: datetime
