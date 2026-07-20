import logging

import httpx

from app.services.groq_client import GroqClient, get_groq_client

logger = logging.getLogger(__name__)

# Bounds prompt size/cost for very large documents.
MAX_DOCUMENT_CHARS = 24_000

MAX_TAGS = 5

SUGGESTED_TAGS = [
    "Invoice",
    "Contract",
    "Resume",
    "Tax",
    "Purchase Order",
    "Medical Record",
    "Salary Slip",
    "Bank Statement",
    "Receipt",
    "Letter",
]

_SYSTEM_PROMPT = (
    "You classify a document's text with short category tags describing what KIND of "
    "document it is (not a summary of its contents). Prefer one of these common "
    f"categories when it fits: {', '.join(SUGGESTED_TAGS)}. If none fit, choose a "
    'concise category of your own (e.g. "Report", "Letter"). Each tag must be 1-2 '
    "words, in Title Case.\n\n"
    f"Return at most {MAX_TAGS} tags, most relevant first, or an empty list if the "
    "document's type can't be determined. Respond ONLY with a JSON object of this "
    'exact shape: {"tags": string[]}'
)


class TagExtractionService:
    """Classifies an indexed file's extracted text into a small set of category
    tags (Invoice, HR, Medical, etc.) via Groq. Returns None (never raises)
    when disabled, given blank text, or on any provider failure — callers must
    treat this as best-effort and never let it block indexing.
    """

    def __init__(self, client: GroqClient | None = None) -> None:
        self._client = client or get_groq_client()

    @property
    def enabled(self) -> bool:
        return self._client.configured

    def extract(self, text: str) -> list[str] | None:
        if not self.enabled or not text.strip():
            return None

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Document text:\n\n{text[:MAX_DOCUMENT_CHARS]}"},
        ]

        try:
            parsed = self._client.chat_json(messages)
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            logger.warning("Groq tag extraction failed: %s", exc)
            return None

        return _clean_tags(parsed.get("tags"))


def _clean_tags(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in value:
        tag = str(item).strip()
        if not tag:
            continue
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(tag)
        if len(cleaned) >= MAX_TAGS:
            break
    return cleaned
