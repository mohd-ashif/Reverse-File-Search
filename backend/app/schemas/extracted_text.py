from pydantic import BaseModel


class ExtractedTextRead(BaseModel):
    file_id: int
    filename: str
    corrected_text: str | None
    was_corrected: bool
