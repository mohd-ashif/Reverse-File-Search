from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FolderCreate(BaseModel):
    path: str


class FolderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
