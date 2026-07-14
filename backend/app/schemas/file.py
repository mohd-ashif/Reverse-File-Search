from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.file import FileIndexStatus, FileType


class IndexedFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folder_id: int
    absolute_path: str
    filename: str
    extension: str
    file_type: FileType
    size_bytes: int
    checksum: str
    status: FileIndexStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
