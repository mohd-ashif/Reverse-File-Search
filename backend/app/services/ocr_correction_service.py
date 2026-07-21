import logging

import httpx

from app.services.groq_client import GroqClient, get_groq_client

logger = logging.getLogger(__name__)

# Bounds prompt size/cost. Only the head of very long OCR text is corrected;
# the remainder is appended unchanged so no content is ever silently dropped.
MAX_CHARS = 24_000

_SYSTEM_PROMPT = (
    "You correct OCR (optical character recognition) mistakes in the text below. "
    "Fix ONLY character-level recognition errors — e.g. a digit misread for a "
    'similar-looking letter or vice versa, broken or garbled words, and spacing '
    'artifacts introduced by OCR. Examples: "Inv0ice" -> "Invoice", "GSTlN" -> '
    '"GSTIN", "T0tal" -> "Total".\n\n'
    "Never change the document's meaning, wording, numbers, or facts — do not "
    "rephrase, summarize, translate, or add/remove content. If a word or number "
    "looks intentional rather than OCR noise, leave it exactly as-is. Preserve "
    "line breaks and overall structure.\n\n"
    'Respond ONLY with a JSON object of this exact shape: {"corrected_text": string}'
)


class OCRCorrectionService:
    """Cleans up common OCR misrecognition errors in text extracted from image
    files via Groq, without altering the document's meaning. Returns the
    original text unchanged (never raises) when disabled, given blank text,
    or on any provider failure — callers must treat this as best-effort and
    never let it block indexing."""

    def __init__(self, client: GroqClient | None = None) -> None:
        self._client = client or get_groq_client()

    @property
    def enabled(self) -> bool:
        return self._client.configured

    def correct(self, text: str) -> str:
        if not self.enabled or not text.strip():
            return text

        head, tail = text[:MAX_CHARS], text[MAX_CHARS:]

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": head},
        ]

        try:
            parsed = self._client.chat_json(messages)
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            logger.warning("Groq OCR correction failed: %s", exc)
            return text

        corrected_head = str(parsed.get("corrected_text") or "").strip()
        return (corrected_head or head) + tail
