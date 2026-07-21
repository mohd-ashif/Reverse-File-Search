from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.file import FileIndexStatus, FileType, IndexedFile
from app.models.folder import MonitoredFolder
from app.services.groq_client import GroqClient


def _get_or_create_folder(db_session: Session, tmp_path) -> MonitoredFolder:
    existing = db_session.query(MonitoredFolder).filter(MonitoredFolder.path == str(tmp_path)).first()
    if existing is not None:
        return existing
    folder = MonitoredFolder(path=str(tmp_path))
    db_session.add(folder)
    db_session.flush()
    return folder


def _create_file(db_session: Session, tmp_path, name: str, content: str = "hello world") -> IndexedFile:
    folder = _get_or_create_folder(db_session, tmp_path)

    target = tmp_path / name
    target.write_text(content)

    file_record = IndexedFile(
        folder_id=folder.id,
        absolute_path=str(target),
        filename=name,
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
    def __init__(self, response: dict | None = None, configured: bool = True):
        super().__init__()
        self._response = response or {
            "summary": "Document B raises the total and adds a penalty clause.",
            "differences": ["Total changed", "New clause added"],
            "added_clauses": ["Late payment penalty clause"],
            "removed_clauses": ["Force majeure clause"],
            "financial_changes": ["Total changed from $1,200 to $1,450"],
        }
        self._configured = configured

    @property
    def configured(self) -> bool:
        return self._configured

    def chat_json(self, messages: list[dict]) -> dict:
        return self._response


def test_compare_404_when_file_a_missing(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_b = _create_file(db_session, tmp_path, "b.txt")
    monkeypatch.setattr("app.services.compare_service.get_groq_client", lambda: FakeGroqClient())

    response = client.post("/api/v1/files/compare", json={"file_id_a": 999999, "file_id_b": file_b.id})
    assert response.status_code == 404


def test_compare_404_when_file_b_missing(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_a = _create_file(db_session, tmp_path, "a.txt")
    monkeypatch.setattr("app.services.compare_service.get_groq_client", lambda: FakeGroqClient())

    response = client.post("/api/v1/files/compare", json={"file_id_a": file_a.id, "file_id_b": 999999})
    assert response.status_code == 404


def test_compare_503_when_not_configured(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_a = _create_file(db_session, tmp_path, "a.txt")
    file_b = _create_file(db_session, tmp_path, "b.txt")
    monkeypatch.setattr(
        "app.services.compare_service.get_groq_client", lambda: FakeGroqClient(configured=False)
    )

    response = client.post("/api/v1/files/compare", json={"file_id_a": file_a.id, "file_id_b": file_b.id})
    assert response.status_code == 503


def test_compare_422_when_a_file_has_no_text(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_a = _create_file(db_session, tmp_path, "a.txt", content="")
    file_b = _create_file(db_session, tmp_path, "b.txt")
    monkeypatch.setattr("app.services.compare_service.get_groq_client", lambda: FakeGroqClient())

    response = client.post("/api/v1/files/compare", json={"file_id_a": file_a.id, "file_id_b": file_b.id})
    assert response.status_code == 422


def test_compare_returns_structured_result(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_a = _create_file(db_session, tmp_path, "a.txt", content="Contract total: $1,200. Force majeure clause included.")
    file_b = _create_file(db_session, tmp_path, "b.txt", content="Contract total: $1,450. Late payment penalty clause included.")
    monkeypatch.setattr("app.services.compare_service.get_groq_client", lambda: FakeGroqClient())

    response = client.post("/api/v1/files/compare", json={"file_id_a": file_a.id, "file_id_b": file_b.id})
    assert response.status_code == 200
    body = response.json()
    assert body["file_a"] == "a.txt"
    assert body["file_b"] == "b.txt"
    assert body["summary"] == "Document B raises the total and adds a penalty clause."
    assert body["differences"] == ["Total changed", "New clause added"]
    assert body["added_clauses"] == ["Late payment penalty clause"]
    assert body["removed_clauses"] == ["Force majeure clause"]
    assert body["financial_changes"] == ["Total changed from $1,200 to $1,450"]
