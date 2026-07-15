import logging
from pathlib import Path

import httpx

from app.core.config import settings
from app.models.file import IndexedFile
from app.services.extractors import get_extractor
from app.services.groq_client import GroqClient, get_groq_client

logger = logging.getLogger(__name__)

# Bounds prompt size/cost for very large documents. The summary trades
# completeness for a bounded, predictable cost on huge files rather than
# failing outright or sending unbounded text to the LLM.
MAX_DOCUMENT_CHARS = 24_000

_SYSTEM_PROMPT = (
    "You are a document summarization assistant. Read the provided document text and "
    "produce a structured summary using ONLY information present in the document — "
    "never invent facts, names, dates, or figures that aren't there. If a section has "
    "nothing relevant, return an empty list for it (or a short factual note for "
    "executive_summary if the document has no substantive content).\n\n"
    "Respond ONLY with a JSON object of this exact shape:\n"
    '{"executive_summary": string, "key_points": string[], "important_dates": string[], '
    '"people": string[], "organizations": string[], "risks": string[], "action_items": string[]}\n\n'
    'executive_summary is a short paragraph (3-6 sentences) capturing the document\'s '
    "overall purpose and content. Each list item must be a concise, self-contained "
    'statement grounded in the text. important_dates should describe what each date '
    'refers to, not just the date itself (e.g. "Sept 30, 2024 — GST filing deadline").'
)


class SummaryNotConfiguredError(Exception):
    """Raised when no LLM provider is configured to generate summaries."""


class SummaryExtractionError(Exception):
    """Raised when the file's text can't be extracted or is empty."""


class SummaryProviderError(Exception):
    """Raised when the LLM call itself fails (unreachable, bad response, etc.)."""


class SummaryService:
    """Generates a structured, grounded summary of an indexed file's extracted
    text via Groq. Pure generation logic — persistence is FileSummaryService's job.
    """

    def __init__(self, client: GroqClient | None = None) -> None:
        self._client = client or get_groq_client()

    @property
    def enabled(self) -> bool:
        return self._client.configured

    def generate(self, file: IndexedFile) -> dict:
        if not self.enabled:
            raise SummaryNotConfiguredError("AI summaries are not configured on the server.")

        try:
            extractor = get_extractor(file.file_type)
            text = extractor.extract(Path(file.absolute_path))
        except Exception as exc:  # noqa: BLE001 - any extraction failure is a generation failure
            raise SummaryExtractionError(f"Could not extract text from this file: {exc}") from exc

        if not text.strip():
            raise SummaryExtractionError("This file has no extractable text to summarize.")

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Document text:\n\n{text[:MAX_DOCUMENT_CHARS]}"},
        ]

        try:
            parsed = self._client.chat_json(messages)
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            logger.warning("Groq summary generation failed for file %s: %s", file.id, exc)
            raise SummaryProviderError("Summary generation failed. Please retry.") from exc

        return {
            "executive_summary": str(parsed.get("executive_summary") or "").strip(),
            "key_points": _as_str_list(parsed.get("key_points")),
            "important_dates": _as_str_list(parsed.get("important_dates")),
            "people": _as_str_list(parsed.get("people")),
            "organizations": _as_str_list(parsed.get("organizations")),
            "risks": _as_str_list(parsed.get("risks")),
            "action_items": _as_str_list(parsed.get("action_items")),
            "model": settings.GROQ_MODEL,
        }


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
