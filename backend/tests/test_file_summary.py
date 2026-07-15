from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.file import FileIndexStatus, FileType, IndexedFile
from app.models.folder import MonitoredFolder
from app.services.groq_client import GroqClient


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
    def __init__(self, response: dict | None = None, configured: bool = True):
        super().__init__()
        self._response = response or {
            "executive_summary": "A short summary of the document.",
            "key_points": ["Point one", "Point two"],
            "important_dates": ["2024-09-30 — deadline"],
            "people": ["Jane Doe"],
            "organizations": ["Acme Corp"],
            "risks": ["Late penalty risk"],
            "action_items": ["Confirm receipt"],
        }
        self._configured = configured

    @property
    def configured(self) -> bool:
        return self._configured

    def chat_json(self, messages: list[dict]) -> dict:
        return self._response


def test_get_summary_404_when_file_missing(client: TestClient) -> None:
    response = client.get("/api/v1/files/999999/summary")
    assert response.status_code == 404


def test_get_summary_404_before_generation(client: TestClient, db_session: Session, tmp_path) -> None:
    file_record = _create_file(db_session, tmp_path)

    response = client.get(f"/api/v1/files/{file_record.id}/summary")
    assert response.status_code == 404


def test_generate_summary_404_when_file_missing(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.summary_service.get_groq_client", lambda: FakeGroqClient()
    )
    response = client.post("/api/v1/files/999999/summary")
    assert response.status_code == 404


def test_generate_summary_503_when_not_configured(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_record = _create_file(db_session, tmp_path)
    monkeypatch.setattr(
        "app.services.summary_service.get_groq_client", lambda: FakeGroqClient(configured=False)
    )

    response = client.post(f"/api/v1/files/{file_record.id}/summary")
    assert response.status_code == 503


def test_generate_summary_422_when_file_has_no_text(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_record = _create_file(db_session, tmp_path, content="")
    monkeypatch.setattr(
        "app.services.summary_service.get_groq_client", lambda: FakeGroqClient()
    )

    response = client.post(f"/api/v1/files/{file_record.id}/summary")
    assert response.status_code == 422


def test_generate_and_fetch_summary(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_record = _create_file(db_session, tmp_path, content="Acme Corp invoice due 2024-09-30.")
    monkeypatch.setattr(
        "app.services.summary_service.get_groq_client", lambda: FakeGroqClient()
    )

    generate_response = client.post(f"/api/v1/files/{file_record.id}/summary")
    assert generate_response.status_code == 201
    body = generate_response.json()
    assert body["file_id"] == file_record.id
    assert body["executive_summary"] == "A short summary of the document."
    assert body["key_points"] == ["Point one", "Point two"]
    assert body["important_dates"] == ["2024-09-30 — deadline"]
    assert body["people"] == ["Jane Doe"]
    assert body["organizations"] == ["Acme Corp"]
    assert body["risks"] == ["Late penalty risk"]
    assert body["action_items"] == ["Confirm receipt"]
    assert body["model"]

    fetch_response = client.get(f"/api/v1/files/{file_record.id}/summary")
    assert fetch_response.status_code == 200
    assert fetch_response.json()["executive_summary"] == "A short summary of the document."


def test_regenerate_summary_overwrites_previous(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_record = _create_file(db_session, tmp_path)

    monkeypatch.setattr(
        "app.services.summary_service.get_groq_client",
        lambda: FakeGroqClient(response={
            "executive_summary": "First version.",
            "key_points": [],
            "important_dates": [],
            "people": [],
            "organizations": [],
            "risks": [],
            "action_items": [],
        }),
    )
    first = client.post(f"/api/v1/files/{file_record.id}/summary")
    assert first.status_code == 201
    assert first.json()["executive_summary"] == "First version."

    monkeypatch.setattr(
        "app.services.summary_service.get_groq_client",
        lambda: FakeGroqClient(response={
            "executive_summary": "Second version.",
            "key_points": [],
            "important_dates": [],
            "people": [],
            "organizations": [],
            "risks": [],
            "action_items": [],
        }),
    )
    second = client.post(f"/api/v1/files/{file_record.id}/summary")
    assert second.status_code == 201
    assert second.json()["executive_summary"] == "Second version."
    assert second.json()["id"] == first.json()["id"]
