from pydantic import BaseModel


class FileTagsRead(BaseModel):
    file_id: int
    tags: list[str]
