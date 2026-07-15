import logging

import httpx

from app.services.groq_client import GroqClient, get_groq_client

logger = logging.getLogger(__name__)

# Bounds prompt size/cost for very large documents.
MAX_DOCUMENT_CHARS = 24_000

ENTITY_FIELDS = [
    "invoice_number",
    "vendor",
    "customer",
    "gst",
    "pan",
    "amount",
    "date",
    "email",
    "phone",
    "address",
    "bank",
    "po_number",
    "contract_number",
]

_SYSTEM_PROMPT = (
    "You extract structured business/financial fields from a document's text. "
    "Extract ONLY values explicitly present in the text — never guess, infer, or "
    "fabricate a value. If a field is not present in the document, its value must "
    "be null.\n\n"
    "Respond ONLY with a JSON object with exactly these keys, each either a string "
    "or null:\n"
    '{"invoice_number": string|null, "vendor": string|null, "customer": string|null, '
    '"gst": string|null, "pan": string|null, "amount": string|null, "date": string|null, '
    '"email": string|null, "phone": string|null, "address": string|null, '
    '"bank": string|null, "po_number": string|null, "contract_number": string|null}'
)


class EntityExtractionService:
    """Extracts structured document fields (invoice number, vendor, GST, PAN,
    amount, dates, contact details, etc.) from already-extracted document text
    via Groq. Returns None (never raises) when disabled, given blank text, or
    on any provider failure — callers must treat this as best-effort and never
    let it block indexing.
    """

    def __init__(self, client: GroqClient | None = None) -> None:
        self._client = client or get_groq_client()

    @property
    def enabled(self) -> bool:
        return self._client.configured

    def extract(self, text: str) -> dict[str, str | None] | None:
        if not self.enabled or not text.strip():
            return None

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Document text:\n\n{text[:MAX_DOCUMENT_CHARS]}"},
        ]

        try:
            parsed = self._client.chat_json(messages)
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            logger.warning("Groq entity extraction failed: %s", exc)
            return None

        return {field: _clean(parsed.get(field)) for field in ENTITY_FIELDS}


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
