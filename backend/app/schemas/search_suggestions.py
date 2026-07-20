from pydantic import BaseModel


class SearchSuggestionsRead(BaseModel):
    recent: list[str]
    popular: list[str]
    ai_generated: list[str]
