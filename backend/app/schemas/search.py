from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class SearchQuery(BaseModel):
    query: str
    top_k: int = 10
    generate_answer: bool = False
    history: list[ChatMessage] = []
    rewrite_query: bool = True
    folder_id: int | None = None
    """Restricts retrieval to chunks from files in this folder."""
    file_id: int | None = None
    """Restricts retrieval to a single file's own chunks (its full content,
    not similarity-searched). Takes precedence over folder_id."""


class SearchResultItem(BaseModel):
    file_id: int
    filename: str
    chunk_text: str | None = None
    score: float | None = None


class AIAnswer(BaseModel):
    text: str
    sources: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    answer: AIAnswer | None = None
    rewritten_query: str
