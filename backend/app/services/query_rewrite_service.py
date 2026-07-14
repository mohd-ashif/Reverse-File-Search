import logging

import httpx

from app.services.groq_client import GroqClient, get_groq_client

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You rewrite short or ambiguous search queries into more effective queries for "
    "semantic (embedding-based) search over a user's personal files. Expand acronyms "
    "and abbreviations, and add likely relevant context words, but preserve the "
    "original intent exactly — never introduce new topics, assumptions, or specifics "
    "the query doesn't support. Keep it a single concise phrase, not a question and "
    "not an answer.\n\n"
    'Respond ONLY with a JSON object of this exact shape: {"rewritten_query": string}'
)


class QueryRewriteService:
    """Rewrites a user's search query with Groq before it's embedded, to improve
    retrieval accuracy for short or acronym-heavy queries (e.g. "GST" ->
    "GST invoices issued during financial year"). Retrieval must never be blocked
    by this: disabled or failed rewrites fall back to the original query unchanged.
    """

    def __init__(self, client: GroqClient | None = None) -> None:
        self._client = client or get_groq_client()

    @property
    def enabled(self) -> bool:
        return self._client.configured

    def rewrite(self, query: str) -> str:
        if not self.enabled or not query.strip():
            return query

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        try:
            parsed = self._client.chat_json(messages)
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            logger.warning("Groq query rewrite failed: %s", exc)
            return query

        rewritten = str(parsed.get("rewritten_query") or "").strip()
        return rewritten or query
