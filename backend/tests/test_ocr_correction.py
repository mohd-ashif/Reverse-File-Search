from unittest.mock import MagicMock

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.file import FileIndexStatus, FileType, IndexedFile
from app.models.folder import MonitoredFolder
from app.services.groq_client import GroqClient
from app.services.indexing_pipeline import IndexingPipeline
from app.services.ocr_correction_service import MAX_CHARS, OCRCorrectionService


def _get_or_create_folder(db_session: Session, tmp_path) -> MonitoredFolder:
    existing = db_session.query(MonitoredFolder).filter(MonitoredFolder.path == str(tmp_path)).first()
    if existing is not None:
        return existing
    folder = MonitoredFolder(path=str(tmp_path))
    db_session.add(folder)
    db_session.flush()
    return folder


def _create_file(db_session: Session, tmp_path, file_type: FileType, content: str = "hello world") -> IndexedFile:
    folder = _get_or_create_folder(db_session, tmp_path)

    target = tmp_path / f"sample-{file_type.value}.txt"
    target.write_text(content)

    file_record = IndexedFile(
        folder_id=folder.id,
        absolute_path=str(target),
        filename=target.name,
        extension=".txt",
        file_type=file_type,
        size_bytes=target.stat().st_size,
        checksum="deadbeef",
        mtime=target.stat().st_mtime,
        status=FileIndexStatus.PENDING,
    )
    db_session.add(file_record)
    db_session.flush()
    return file_record


class FakeGroqClient(GroqClient):
    def __init__(self, response: dict | None = None, configured: bool = True, error: Exception | None = None):
        super().__init__()
        self._response = response if response is not None else {"corrected_text": "Invoice total: GSTIN 123"}
        self._configured = configured
        self._error = error

    @property
    def configured(self) -> bool:
        return self._configured

    def chat_json(self, _messages: list[dict]) -> dict:
        if self._error is not None:
            raise self._error
        return self._response


# --- OCRCorrectionService (unit) ---


def test_correct_returns_unchanged_when_not_configured() -> None:
    service = OCRCorrectionService(client=FakeGroqClient(configured=False))
    assert service.correct("Inv0ice T0tal") == "Inv0ice T0tal"


def test_correct_returns_unchanged_for_blank_text() -> None:
    service = OCRCorrectionService(client=FakeGroqClient())
    assert service.correct("   ") == "   "


def test_correct_returns_corrected_text() -> None:
    service = OCRCorrectionService(
        client=FakeGroqClient(response={"corrected_text": "Invoice total: GSTIN 123"})
    )
    assert service.correct("Inv0ice t0tal: GSTlN 123") == "Invoice total: GSTIN 123"


def test_correct_falls_back_to_original_on_provider_failure() -> None:
    service = OCRCorrectionService(client=FakeGroqClient(error=httpx.HTTPError("boom")))
    assert service.correct("Inv0ice") == "Inv0ice"


def test_correct_falls_back_when_response_missing_field() -> None:
    service = OCRCorrectionService(client=FakeGroqClient(response={}))
    assert service.correct("Inv0ice") == "Inv0ice"


def test_correct_preserves_tail_beyond_max_chars() -> None:
    long_text = ("a" * MAX_CHARS) + "TAIL_MARKER"
    service = OCRCorrectionService(client=FakeGroqClient(response={"corrected_text": "corrected head"}))
    result = service.correct(long_text)
    assert result == "corrected head" + "TAIL_MARKER"


# --- IndexingPipeline integration (unit, via a fake extractor) ---


def test_pipeline_corrects_ocr_only_for_image_files(db_session: Session, tmp_path) -> None:
    image_file = _create_file(db_session, tmp_path, FileType.IMAGE, content="Inv0ice")
    txt_file = _create_file(db_session, tmp_path, FileType.TXT, content="Inv0ice")

    ocr_service = OCRCorrectionService(client=FakeGroqClient(response={"corrected_text": "Invoice"}))
    pipeline = IndexingPipeline(db_session, ocr_correction_service=ocr_service)

    corrected = pipeline._correct_ocr_safely(image_file, "Inv0ice")
    assert corrected == "Invoice"
    assert image_file.corrected_text == "Invoice"

    unchanged = pipeline._correct_ocr_safely(txt_file, "Inv0ice")
    assert unchanged == "Inv0ice"
    assert txt_file.corrected_text is None


def test_pipeline_ocr_correction_failure_keeps_original_text(db_session: Session, tmp_path) -> None:
    image_file = _create_file(db_session, tmp_path, FileType.IMAGE, content="Inv0ice")

    broken_service = MagicMock(spec=OCRCorrectionService)
    broken_service.correct.side_effect = RuntimeError("boom")
    pipeline = IndexingPipeline(db_session, ocr_correction_service=broken_service)

    result = pipeline._correct_ocr_safely(image_file, "Inv0ice")
    assert result == "Inv0ice"
    assert image_file.corrected_text is None


# --- GET /files/{id}/extracted-text ---


def test_get_extracted_text_404_when_missing(client: TestClient) -> None:
    response = client.get("/api/v1/files/999999/extracted-text")
    assert response.status_code == 404


def test_get_extracted_text_defaults_when_never_corrected(client: TestClient, db_session: Session, tmp_path) -> None:
    file_record = _create_file(db_session, tmp_path, FileType.TXT)

    response = client.get(f"/api/v1/files/{file_record.id}/extracted-text")
    assert response.status_code == 200
    body = response.json()
    assert body["corrected_text"] is None
    assert body["was_corrected"] is False


def test_get_extracted_text_returns_stored_correction(client: TestClient, db_session: Session, tmp_path) -> None:
    file_record = _create_file(db_session, tmp_path, FileType.IMAGE)
    file_record.corrected_text = "Invoice total: GSTIN 123"
    db_session.flush()

    response = client.get(f"/api/v1/files/{file_record.id}/extracted-text")
    assert response.status_code == 200
    body = response.json()
    assert body["corrected_text"] == "Invoice total: GSTIN 123"
    assert body["was_corrected"] is True
