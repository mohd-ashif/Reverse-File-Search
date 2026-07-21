import logging
from pathlib import Path

import httpx

from app.repositories.file_repository import FileRepository
from app.schemas.contract_risk import ContractRiskAnalysis, ContractRiskFlag
from app.services.extractors import get_extractor
from app.services.groq_client import GroqClient, get_groq_client

logger = logging.getLogger(__name__)

MAX_DOCUMENT_CHARS = 24_000

RISK_CATEGORIES = [
    "Missing Signature",
    "Unlimited Liability",
    "Auto-Renewal",
    "Late Fees",
    "Termination Clause",
]

_SYSTEM_PROMPT = (
    "You are a contract risk analyzer. Analyze the provided contract text for "
    f"exactly these risk categories, in this order: {', '.join(RISK_CATEGORIES)}. "
    "For each category, determine whether it is present in the document based "
    "ONLY on the text given — never guess or assume something is present or "
    "absent beyond what the text supports. For every category, write a short "
    "(1-2 sentence) explanation in simple, plain language a non-lawyer can "
    "understand, describing what you found (or didn't find) and, when present, "
    "why it could matter.\n\n"
    "Respond ONLY with a JSON object of this exact shape:\n"
    '{"risks": [{"risk": string, "present": boolean, "explanation": string}, ...]}\n\n'
    "Include exactly one entry per category listed above, in that order, using "
    "the category name verbatim as \"risk\"."
)


class ContractFileNotFoundError(Exception):
    pass


class ContractAnalysisNotConfiguredError(Exception):
    """Raised when no LLM provider is configured to run the analysis."""


class ContractAnalysisExtractionError(Exception):
    """Raised when the file's text can't be extracted or is empty."""


class ContractAnalysisProviderError(Exception):
    """Raised when the LLM call itself fails (unreachable, bad response, etc.)."""


class ContractRiskService:
    """Analyzes an indexed file's text for common contract risk patterns
    (missing signature, unlimited liability, auto-renewal, late fees,
    termination clause), explained in plain language, grounded strictly in
    the file's own text. Not persisted — generated fresh on each request."""

    def __init__(self, db, client: GroqClient | None = None) -> None:
        self.file_repo = FileRepository(db)
        self._client = client or get_groq_client()

    @property
    def enabled(self) -> bool:
        return self._client.configured

    def analyze(self, file_id: int) -> ContractRiskAnalysis:
        file = self.file_repo.get(file_id)
        if file is None:
            raise ContractFileNotFoundError(f"File {file_id} not found")

        if not self.enabled:
            raise ContractAnalysisNotConfiguredError("AI contract analysis is not configured on the server.")

        try:
            extractor = get_extractor(file.file_type)
            text = extractor.extract(Path(file.absolute_path))
        except Exception as exc:  # noqa: BLE001 - any extraction failure is an analysis failure
            raise ContractAnalysisExtractionError(f"Could not extract text from this file: {exc}") from exc

        if not text.strip():
            raise ContractAnalysisExtractionError("This file has no extractable text to analyze.")

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Contract text:\n\n{text[:MAX_DOCUMENT_CHARS]}"},
        ]

        try:
            parsed = self._client.chat_json(messages)
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            logger.warning("Groq contract risk analysis failed for file %s: %s", file_id, exc)
            raise ContractAnalysisProviderError("Contract analysis failed. Please retry.") from exc

        return ContractRiskAnalysis(file_id=file.id, filename=file.filename, risks=_clean_risks(parsed.get("risks")))


def _clean_risks(value: object) -> list[ContractRiskFlag]:
    by_category: dict[str, ContractRiskFlag] = {}
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            risk = str(item.get("risk") or "").strip()
            if not risk:
                continue
            by_category[risk] = ContractRiskFlag(
                risk=risk,
                present=bool(item.get("present", False)),
                explanation=str(item.get("explanation") or "").strip(),
            )

    return [
        by_category.get(
            category,
            ContractRiskFlag(risk=category, present=False, explanation="Not addressed in the document."),
        )
        for category in RISK_CATEGORIES
    ]
