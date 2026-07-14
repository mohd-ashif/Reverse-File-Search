import logging

import httpx

from app.schemas.search import AIAnswer, ChatMessage, SearchResultItem
from app.services.groq_client import GroqClient, get_groq_client
from app.services.rag_context import INSUFFICIENT_CONTEXT_MESSAGE, build_context, history_to_messages

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a reverse file search assistant. Answer the user's query using ONLY "
    "the excerpts provided below, each labeled with its source filename. Never use "
    "outside knowledge, and never invent facts, filenames, or details that are not "
    "present in the excerpts.\n\n"
    f'If the excerpts do not contain enough information to answer the query, set '
    f'"sufficient" to false and set "answer" to exactly: "{INSUFFICIENT_CONTEXT_MESSAGE}"\n\n'
    "Respond ONLY with a JSON object of this exact shape:\n"
    '{"answer": string, "sufficient": boolean, "confidence": number between 0 and 1}\n\n'
    '"sufficient" must be true only if the excerpts directly support the answer. '
    '"confidence" reflects how strongly the excerpts support the answer '
    "(0 = not at all, 1 = fully and unambiguously)."
)


def _clamp_confidence(value: object) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, number))


class AnswerService:
    """Turns already-retrieved search chunks into a grounded, cited answer.

    Retrieval (embedding + vector search) stays entirely in SearchService; this
    service is a pure post-processing step over its results, so a Groq outage
    or missing API key degrades to "no AI answer" without affecting search.
    """

    def __init__(self, client: GroqClient | None = None) -> None:
        self._client = client or get_groq_client()

    @property
    def enabled(self) -> bool:
        return self._client.configured

    def answer(
        self, query: str, results: list[SearchResultItem], history: list[ChatMessage] | None = None
    ) -> AIAnswer | None:
        if not self.enabled or not results:
            return None

        context, sources = build_context(results)
        if not context:
            return None

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            *history_to_messages(history),
            {"role": "user", "content": f"Query: {query}\n\nExcerpts:\n{context}"},
        ]

        try:
            parsed = self._client.chat_json(messages)
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            logger.warning("Groq answer generation failed: %s", exc)
            return None

        sufficient = bool(parsed.get("sufficient", False))
        text = str(parsed.get("answer") or "").strip()

        if not sufficient or not text:
            return AIAnswer(text=INSUFFICIENT_CONTEXT_MESSAGE, sources=[], confidence=0.0)

        return AIAnswer(
            text=text,
            sources=sources,
            confidence=_clamp_confidence(parsed.get("confidence")),
        )
