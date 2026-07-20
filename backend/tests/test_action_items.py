from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.file import FileIndexStatus, FileType, IndexedFile
from app.models.folder import MonitoredFolder
from app.services.groq_client import GroqClient


def _create_file(db_session: Session, tmp_path, content: str = "hello world") -> IndexedFile:
    folder = MonitoredFolder(path=str(tmp_path))
    db_session.add(folder)
    db_session.flush()

    target = tmp_path / "notes.txt"
    target.write_text(content)

    file_record = IndexedFile(
        folder_id=folder.id,
        absolute_path=str(target),
        filename="notes.txt",
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
            "action_items": [
                {"person": "Alice", "task": "Send the proposal", "deadline": "Friday", "priority": "High"},
                {"person": None, "task": "Review budget", "deadline": None, "priority": "bogus"},
            ]
        }
        self._configured = configured

    @property
    def configured(self) -> bool:
        return self._configured

    def chat_json(self, messages: list[dict]) -> dict:
        return self._response


def test_extract_404_when_file_missing(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.action_item_service.get_groq_client", lambda: FakeGroqClient())
    response = client.post("/api/v1/files/999999/action-items")
    assert response.status_code == 404


def test_extract_503_when_not_configured(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_record = _create_file(db_session, tmp_path)
    monkeypatch.setattr(
        "app.services.action_item_service.get_groq_client", lambda: FakeGroqClient(configured=False)
    )

    response = client.post(f"/api/v1/files/{file_record.id}/action-items")
    assert response.status_code == 503


def test_extract_422_when_file_has_no_text(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_record = _create_file(db_session, tmp_path, content="")
    monkeypatch.setattr("app.services.action_item_service.get_groq_client", lambda: FakeGroqClient())

    response = client.post(f"/api/v1/files/{file_record.id}/action-items")
    assert response.status_code == 422


def test_extract_returns_structured_items_and_normalizes_priority(
    client: TestClient, db_session: Session, tmp_path, monkeypatch
) -> None:
    file_record = _create_file(db_session, tmp_path, content="Alice will send the proposal by Friday.")
    monkeypatch.setattr("app.services.action_item_service.get_groq_client", lambda: FakeGroqClient())

    response = client.post(f"/api/v1/files/{file_record.id}/action-items")
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "notes.txt"
    items = body["action_items"]
    assert len(items) == 2
    assert items[0] == {"person": "Alice", "task": "Send the proposal", "deadline": "Friday", "priority": "High"}
    # An invalid priority from the model falls back to "Medium" rather than erroring.
    assert items[1]["priority"] == "Medium"
    assert items[1]["person"] is None
    assert items[1]["deadline"] is None


def test_extract_skips_items_with_no_task(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_record = _create_file(db_session, tmp_path, content="Some notes.")
    monkeypatch.setattr(
        "app.services.action_item_service.get_groq_client",
        lambda: FakeGroqClient(response={"action_items": [{"person": "Bob", "task": "", "priority": "Low"}]}),
    )

    response = client.post(f"/api/v1/files/{file_record.id}/action-items")
    assert response.status_code == 200
    assert response.json()["action_items"] == []
