import logging
from pathlib import Path

import httpx

from app.repositories.file_repository import FileRepository
from app.schemas.action_items import ActionItem, ActionItemsResult
from app.services.extractors import get_extractor
from app.services.groq_client import GroqClient, get_groq_client

logger = logging.getLogger(__name__)

MAX_DOCUMENT_CHARS = 24_000
VALID_PRIORITIES = ("High", "Medium", "Low")

_SYSTEM_PROMPT = (
    "You extract action items from meeting notes or similar documents. For each "
    "action item, identify: the person responsible (or null if not specified), a "
    "concise task description, a deadline if one is mentioned (or null), and a "
    "priority of High, Medium, or Low based on urgency or emphasis in the text. "
    "Use ONLY information present in the text — never invent a person, deadline, "
    "or task that isn't there. If no action items are found, return an empty "
    "list.\n\n"
    "Respond ONLY with a JSON object of this exact shape:\n"
    '{"action_items": [{"person": string|null, "task": string, "deadline": '
    'string|null, "priority": "High"|"Medium"|"Low"}, ...]}'
)


class ActionItemFileNotFoundError(Exception):
    pass


class ActionItemNotConfiguredError(Exception):
    """Raised when no LLM provider is configured to extract action items."""


class ActionItemExtractionError(Exception):
    """Raised when the file's text can't be extracted or is empty."""


class ActionItemProviderError(Exception):
    """Raised when the LLM call itself fails (unreachable, bad response, etc.)."""


class ActionItemService:
    """Extracts action items (person, task, deadline, priority) from an indexed
    file's text — typically meeting notes — via Groq. Grounded strictly in the
    file's own text. Not persisted — generated fresh on each request."""

    def __init__(self, db, client: GroqClient | None = None) -> None:
        self.file_repo = FileRepository(db)
        self._client = client or get_groq_client()

    @property
    def enabled(self) -> bool:
        return self._client.configured

    def extract(self, file_id: int) -> ActionItemsResult:
        file = self.file_repo.get(file_id)
        if file is None:
            raise ActionItemFileNotFoundError(f"File {file_id} not found")

        if not self.enabled:
            raise ActionItemNotConfiguredError("AI action-item extraction is not configured on the server.")

        try:
            extractor = get_extractor(file.file_type)
            text = extractor.extract(Path(file.absolute_path))
        except Exception as exc:  # noqa: BLE001 - any extraction failure is an extraction failure
            raise ActionItemExtractionError(f"Could not extract text from this file: {exc}") from exc

        if not text.strip():
            raise ActionItemExtractionError("This file has no extractable text to extract action items from.")

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Document text:\n\n{text[:MAX_DOCUMENT_CHARS]}"},
        ]

        try:
            parsed = self._client.chat_json(messages)
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            logger.warning("Groq action-item extraction failed for file %s: %s", file_id, exc)
            raise ActionItemProviderError("Action item extraction failed. Please retry.") from exc

        return ActionItemsResult(
            file_id=file.id, filename=file.filename, action_items=_clean_items(parsed.get("action_items"))
        )


def _clean_items(value: object) -> list[ActionItem]:
    if not isinstance(value, list):
        return []

    cleaned: list[ActionItem] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        task = str(item.get("task") or "").strip()
        if not task:
            continue

        priority = str(item.get("priority") or "").strip().title()
        if priority not in VALID_PRIORITIES:
            priority = "Medium"

        person = item.get("person")
        person = str(person).strip() or None if person is not None else None

        deadline = item.get("deadline")
        deadline = str(deadline).strip() or None if deadline is not None else None

        cleaned.append(ActionItem(person=person, task=task, deadline=deadline, priority=priority))
    return cleaned
