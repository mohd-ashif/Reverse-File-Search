import logging

import httpx
from sqlalchemy.orm import Session

from app.repositories.search_query_repository import SearchQueryRepository
from app.schemas.search_suggestions import SearchSuggestionsRead
from app.services.groq_client import GroqClient, get_groq_client
from app.services.tag_extraction_service import SUGGESTED_TAGS

logger = logging.getLogger(__name__)

RECENT_LIMIT = 5
POPULAR_LIMIT = 5
AI_SUGGESTION_LIMIT = 4

_SYSTEM_PROMPT = (
    "You suggest realistic search queries for a personal document search assistant. "
    f"Indexed documents commonly fall into these categories: {', '.join(SUGGESTED_TAGS)}, "
    "and often contain invoice numbers, GST numbers, amounts, vendors, and dates. "
    f"Suggest up to {AI_SUGGESTION_LIMIT} short, natural-language search queries.\n\n"
    "If the user has typed a partial query, your suggestions should complete or "
    "closely extend it. If they haven't typed anything yet, suggest generally useful "
    "example queries instead (e.g. filtering by amount, date, status, or document "
    "type).\n\n"
    'Respond ONLY with JSON of this exact shape: {"suggestions": string[]}'
)


class SearchSuggestionService:
    """Backs the search box's autocomplete dropdown: recent and popular past
    searches (from the query log) plus AI-generated suggestions from Groq.
    AI generation is best-effort — it returns an empty list (never raises)
    when Groq is unconfigured or unreachable."""

    def __init__(self, db: Session, client: GroqClient | None = None) -> None:
        self.repo = SearchQueryRepository(db)
        self._client = client or get_groq_client()

    def log_query(self, query_text: str) -> None:
        self.repo.log(query_text)

    def get_suggestions(self, q: str) -> SearchSuggestionsRead:
        partial = q.strip()
        prefix = partial or None
        recent = self.repo.list_recent(RECENT_LIMIT, prefix)
        popular = self.repo.list_popular(POPULAR_LIMIT, prefix)
        ai_generated = self._generate_ai_suggestions(partial)
        return SearchSuggestionsRead(recent=recent, popular=popular, ai_generated=ai_generated)

    def _generate_ai_suggestions(self, partial: str) -> list[str]:
        if not self._client.configured:
            return []

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f'Partial input: "{partial}"' if partial else "Partial input: (empty)"},
        ]

        try:
            parsed = self._client.chat_json(messages)
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            logger.warning("Search suggestion generation failed: %s", exc)
            return []

        return _clean_suggestions(parsed.get("suggestions"))


def _clean_suggestions(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in value:
        text = str(item).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
        if len(cleaned) >= AI_SUGGESTION_LIMIT:
            break
    return cleaned
