import logging
from collections.abc import Iterator

import httpx

from app.schemas.search import ChatMessage, SearchResultItem
from app.services.groq_client import GroqClient, get_groq_client
from app.services.rag_context import (
    INSUFFICIENT_CONTEXT_MESSAGE,
    build_context,
    confidence_from_scores,
    history_to_messages,
)
from app.services.sse import sse_event

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a reverse file search assistant. Answer the user's query using ONLY "
    "the excerpts provided below, each labeled with its source filename. Never use "
    "outside knowledge, and never invent facts, filenames, or details that are not "
    "present in the excerpts. Cite the source filename inline after any claim you "
    "draw from it, like (source: report.pdf).\n\n"
    f'If the excerpts do not contain enough information to answer the query, reply '
    f'with exactly this sentence and nothing else: "{INSUFFICIENT_CONTEXT_MESSAGE}"'
)


class AnswerStreamService:
    """Streams a grounded AI answer as Server-Sent Events.

    Sources and confidence are derived deterministically from retrieval (never
    from the model) and sent as a single 'meta' event before any generated
    tokens, so the UI can render citations immediately without waiting on the
    LLM. Emits, in order: one 'meta' event, zero or more 'token' events, then
    exactly one of 'done' or 'error'.
    """

    def __init__(self, client: GroqClient | None = None) -> None:
        self._client = client or get_groq_client()

    @property
    def enabled(self) -> bool:
        return self._client.configured

    def stream(
        self, query: str, results: list[SearchResultItem], history: list[ChatMessage] | None = None
    ) -> Iterator[str]:
        if not self.enabled:
            yield sse_event({"type": "meta", "sources": [], "confidence": 0.0})
            yield sse_event({"type": "error", "message": "AI answers are not configured on the server."})
            return

        context, sources = build_context(results)
        if not context:
            yield sse_event({"type": "meta", "sources": [], "confidence": 0.0})
            yield sse_event({"type": "token", "text": INSUFFICIENT_CONTEXT_MESSAGE})
            yield sse_event({"type": "done"})
            return

        yield sse_event({"type": "meta", "sources": sources, "confidence": confidence_from_scores(results)})

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            *history_to_messages(history),
            {"role": "user", "content": f"Query: {query}\n\nExcerpts:\n{context}"},
        ]
        try:
            for delta in self._client.chat_stream(messages):
                yield sse_event({"type": "token", "text": delta})
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Groq streaming failed: %s", exc)
            yield sse_event({"type": "error", "message": "AI answer generation failed. Please retry."})
            return

        yield sse_event({"type": "done"})
