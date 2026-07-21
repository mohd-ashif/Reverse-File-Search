from unittest.mock import MagicMock

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.file import FileIndexStatus, FileType, IndexedFile
from app.models.folder import MonitoredFolder
from app.services.entity_extraction_service import ENTITY_FIELDS, EntityExtractionService
from app.services.groq_client import GroqClient
from app.services.indexing_pipeline import IndexingPipeline


def _create_file(db_session: Session, tmp_path, content: str = "hello world") -> IndexedFile:
    folder = MonitoredFolder(path=str(tmp_path))
    db_session.add(folder)
    db_session.flush()

    target = tmp_path / "sample.txt"
    target.write_text(content)

    file_record = IndexedFile(
        folder_id=folder.id,
        absolute_path=str(target),
        filename="sample.txt",
        extension=".txt",
        file_type=FileType.TXT,
        size_bytes=target.stat().st_size,
        checksum="deadbeef",
        mtime=target.stat().st_mtime,
        status=FileIndexStatus.EMBEDDED,
    )
    db_session.add(file_record)
    db_session.flush()
    return file_record


class FakeGroqClient(GroqClient):
    def __init__(self, response: dict | None = None, configured: bool = True, error: Exception | None = None):
        super().__init__()
        self._response = response or {field: None for field in ENTITY_FIELDS}
        self._configured = configured
        self._error = error

    @property
    def configured(self) -> bool:
        return self._configured

    def chat_json(self, _messages: list[dict]) -> dict:
        if self._error is not None:
            raise self._error
        return self._response


FULL_RESPONSE = {
    "invoice_number": "INV-1001",
    "vendor": "Acme Supplies",
    "customer": "Globex Corp",
    "gst": "22AAAAA0000A1Z5",
    "pan": "AAAAA0000A",
    "amount": "12,500.00",
    "date": "2024-09-30",
    "email": "billing@acme.example",
    "phone": "+91-9876543210",
    "address": "123 Industrial Rd, Mumbai",
    "bank": "HDFC Bank",
    "po_number": "PO-77",
    "contract_number": "CN-42",
}


# --- EntityExtractionService (unit) ---


def test_extract_returns_none_when_not_configured() -> None:
    service = EntityExtractionService(client=FakeGroqClient(configured=False))
    assert service.extract("Some invoice text") is None


def test_extract_returns_none_for_blank_text() -> None:
    service = EntityExtractionService(client=FakeGroqClient())
    assert service.extract("   ") is None


def test_extract_returns_none_on_provider_failure() -> None:
    service = EntityExtractionService(client=FakeGroqClient(error=httpx.HTTPError("boom")))
    assert service.extract("Some invoice text") is None


def test_extract_returns_none_on_malformed_response() -> None:
    client = FakeGroqClient()
    client.chat_json = MagicMock(side_effect=ValueError("bad json"))
    service = EntityExtractionService(client=client)
    assert service.extract("Some invoice text") is None


def test_extract_normalizes_blank_and_missing_fields_to_none() -> None:
    response = {**FULL_RESPONSE, "gst": "  ", "pan": None}
    service = EntityExtractionService(client=FakeGroqClient(response=response))

    result = service.extract("Some invoice text")

    assert result["invoice_number"] == "INV-1001"
    assert result["gst"] is None
    assert result["pan"] is None


def test_extract_returns_all_requested_fields() -> None:
    service = EntityExtractionService(client=FakeGroqClient(response=FULL_RESPONSE))

    result = service.extract("Some invoice text")

    assert set(result.keys()) == set(ENTITY_FIELDS)
    for field, value in FULL_RESPONSE.items():
        assert result[field] == value


# --- IndexingPipeline never fails indexing on extraction errors ---


def test_pipeline_swallows_entity_extraction_failure(db_session: Session, tmp_path) -> None:
    file_record = _create_file(db_session, tmp_path)
    entity_service = EntityExtractionService(client=FakeGroqClient(error=RuntimeError("groq is down")))
    pipeline = IndexingPipeline(db_session, entity_extraction_service=entity_service)

    # Must not raise, even though extraction fails internally.
    pipeline._extract_entities_safely(file_record, "Invoice text")

    assert file_record.status == FileIndexStatus.EMBEDDED
    assert pipeline.entities_repo.get_by_file(file_record.id) is None


def test_pipeline_persists_extracted_entities(db_session: Session, tmp_path) -> None:
    file_record = _create_file(db_session, tmp_path)
    entity_service = EntityExtractionService(client=FakeGroqClient(response=FULL_RESPONSE))
    pipeline = IndexingPipeline(db_session, entity_extraction_service=entity_service)

    pipeline._extract_entities_safely(file_record, "Invoice text")

    stored = pipeline.entities_repo.get_by_file(file_record.id)
    assert stored is not None
    assert stored.invoice_number == "INV-1001"
    assert stored.gst == "22AAAAA0000A1Z5"


def test_pipeline_skips_persisting_when_extraction_disabled(db_session: Session, tmp_path) -> None:
    file_record = _create_file(db_session, tmp_path)
    entity_service = EntityExtractionService(client=FakeGroqClient(configured=False))
    pipeline = IndexingPipeline(db_session, entity_extraction_service=entity_service)

    pipeline._extract_entities_safely(file_record, "Invoice text")

    assert pipeline.entities_repo.get_by_file(file_record.id) is None


# --- API ---


def test_get_entities_404_when_file_missing(client: TestClient) -> None:
    response = client.get("/api/v1/files/999999/entities")
    assert response.status_code == 404


def test_get_entities_404_before_extraction(client: TestClient, db_session: Session, tmp_path) -> None:
    file_record = _create_file(db_session, tmp_path)

    response = client.get(f"/api/v1/files/{file_record.id}/entities")
    assert response.status_code == 404


def test_get_entities_returns_stored_data(client: TestClient, db_session: Session, tmp_path) -> None:
    file_record = _create_file(db_session, tmp_path)
    entity_service = EntityExtractionService(client=FakeGroqClient(response=FULL_RESPONSE))
    pipeline = IndexingPipeline(db_session, entity_extraction_service=entity_service)
    pipeline._extract_entities_safely(file_record, "Invoice text")

    response = client.get(f"/api/v1/files/{file_record.id}/entities")

    assert response.status_code == 200
    body = response.json()
    assert body["file_id"] == file_record.id
    assert body["invoice_number"] == "INV-1001"
    assert body["vendor"] == "Acme Supplies"
    assert body["po_number"] == "PO-77"
    assert body["contract_number"] == "CN-42"


def test_reextraction_overwrites_previous_entities(db_session: Session, tmp_path) -> None:
    file_record = _create_file(db_session, tmp_path)
    pipeline = IndexingPipeline(
        db_session, entity_extraction_service=EntityExtractionService(client=FakeGroqClient(response=FULL_RESPONSE))
    )
    pipeline._extract_entities_safely(file_record, "Invoice text")
    first = pipeline.entities_repo.get_by_file(file_record.id)
    assert first.invoice_number == "INV-1001"

    updated_response = {**FULL_RESPONSE, "invoice_number": "INV-2002"}
    pipeline.entity_extraction_service = EntityExtractionService(client=FakeGroqClient(response=updated_response))
    pipeline._extract_entities_safely(file_record, "Invoice text v2")

    second = pipeline.entities_repo.get_by_file(file_record.id)
    assert second.id == first.id
    assert second.invoice_number == "INV-2002"
