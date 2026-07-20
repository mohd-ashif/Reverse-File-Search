from typing import Literal

from pydantic import BaseModel

Priority = Literal["High", "Medium", "Low"]


class ActionItem(BaseModel):
    person: str | None
    task: str
    deadline: str | None
    priority: Priority


class ActionItemsResult(BaseModel):
    file_id: int
    filename: str
    action_items: list[ActionItem]
