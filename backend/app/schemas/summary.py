from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_id: int
    executive_summary: str
    key_points: list[str]
    important_dates: list[str]
    people: list[str]
    organizations: list[str]
    risks: list[str]
    action_items: list[str]
    model: str
    created_at: datetime
    updated_at: datetime
