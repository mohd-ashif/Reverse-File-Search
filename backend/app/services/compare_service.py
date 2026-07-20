import logging
from pathlib import Path

import httpx

from app.repositories.file_repository import FileRepository
from app.schemas.compare import FileCompareResult
from app.services.extractors import get_extractor
from app.services.groq_client import GroqClient, get_groq_client

logger = logging.getLogger(__name__)

# Bounds prompt size/cost — each document gets its own budget so a combined
# comparison prompt stays predictable regardless of file size.
MAX_CHARS_PER_DOCUMENT = 12_000

_SYSTEM_PROMPT = (
    "You compare two documents and describe how Document B differs from Document A. "
    "Use ONLY the text provided for each document — never invent facts, clauses, "
    "or figures that aren't there. If a category has nothing relevant, return an "
    "empty list for it.\n\n"
    "Respond ONLY with a JSON object of this exact shape:\n"
    '{"summary": string, "differences": string[], "added_clauses": string[], '
    '"removed_clauses": string[], "financial_changes": string[]}\n\n'
    "summary is a short paragraph (2-5 sentences) describing the overall nature of "
    "the differences. differences lists specific, concrete factual differences "
    "between the two documents. added_clauses lists clauses, sections, or terms "
    "present in Document B but not in Document A. removed_clauses lists clauses, "
    "sections, or terms present in Document A but not in Document B. "
    "financial_changes lists any differences in amounts, prices, totals, or other "
    "financial figures between the two documents, describing both values when "
    'possible (e.g. "Total changed from $1,200 to $1,450").'
)


class FileCompareNotFoundError(Exception):
    pass


class CompareNotConfiguredError(Exception):
    """Raised when no LLM provider is configured to run a comparison."""


class CompareExtractionError(Exception):
    """Raised when one or both files' text can't be extracted or is empty."""


class CompareProviderError(Exception):
    """Raised when the LLM call itself fails (unreachable, bad response, etc.)."""


class FileCompareService:
    """Compares two indexed files via Groq: a summary of how they differ, added
    and removed clauses, and financial changes — grounded strictly in both
    files' own extracted text, never outside knowledge."""

    def __init__(self, db, client: GroqClient | None = None) -> None:
        self.file_repo = FileRepository(db)
        self._client = client or get_groq_client()

    @property
    def enabled(self) -> bool:
        return self._client.configured

    def compare(self, file_id_a: int, file_id_b: int) -> FileCompareResult:
        file_a = self.file_repo.get(file_id_a)
        file_b = self.file_repo.get(file_id_b)
        if file_a is None:
            raise FileCompareNotFoundError(f"File {file_id_a} not found")
        if file_b is None:
            raise FileCompareNotFoundError(f"File {file_id_b} not found")

        if not self.enabled:
            raise CompareNotConfiguredError("AI comparison is not configured on the server.")

        text_a = self._extract(file_a)
        text_b = self._extract(file_b)
        if not text_a.strip() or not text_b.strip():
            raise CompareExtractionError("One or both files have no extractable text to compare.")

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Document A ({file_a.filename}):\n\n{text_a[:MAX_CHARS_PER_DOCUMENT]}\n\n"
                    f"---\n\nDocument B ({file_b.filename}):\n\n{text_b[:MAX_CHARS_PER_DOCUMENT]}"
                ),
            },
        ]

        try:
            parsed = self._client.chat_json(messages)
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            logger.warning("Groq file comparison failed for files %s/%s: %s", file_id_a, file_id_b, exc)
            raise CompareProviderError("Comparison generation failed. Please retry.") from exc

        return FileCompareResult(
            file_a=file_a.filename,
            file_b=file_b.filename,
            summary=str(parsed.get("summary") or "").strip(),
            differences=_as_str_list(parsed.get("differences")),
            added_clauses=_as_str_list(parsed.get("added_clauses")),
            removed_clauses=_as_str_list(parsed.get("removed_clauses")),
            financial_changes=_as_str_list(parsed.get("financial_changes")),
        )

    def _extract(self, file) -> str:
        try:
            extractor = get_extractor(file.file_type)
            return extractor.extract(Path(file.absolute_path))
        except Exception as exc:  # noqa: BLE001 - any extraction failure is a comparison failure
            raise CompareExtractionError(f"Could not extract text from '{file.filename}': {exc}") from exc


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
