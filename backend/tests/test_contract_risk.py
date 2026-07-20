from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.file import FileIndexStatus, FileType, IndexedFile
from app.models.folder import MonitoredFolder
from app.services.contract_risk_service import RISK_CATEGORIES
from app.services.groq_client import GroqClient


def _create_file(db_session: Session, tmp_path, content: str = "hello world") -> IndexedFile:
    folder = MonitoredFolder(path=str(tmp_path))
    db_session.add(folder)
    db_session.flush()

    target = tmp_path / "contract.txt"
    target.write_text(content)

    file_record = IndexedFile(
        folder_id=folder.id,
        absolute_path=str(target),
        filename="contract.txt",
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


FULL_RESPONSE = {
    "risks": [
        {"risk": "Missing Signature", "present": True, "explanation": "No signature block was found."},
        {"risk": "Unlimited Liability", "present": False, "explanation": "Liability is capped at contract value."},
        {"risk": "Auto-Renewal", "present": True, "explanation": "The contract renews automatically each year."},
        {"risk": "Late Fees", "present": False, "explanation": "No late fee terms are mentioned."},
        {"risk": "Termination Clause", "present": True, "explanation": "Either party may terminate with 30 days notice."},
    ]
}


class FakeGroqClient(GroqClient):
    def __init__(self, response: dict | None = None, configured: bool = True):
        super().__init__()
        self._response = response if response is not None else FULL_RESPONSE
        self._configured = configured

    @property
    def configured(self) -> bool:
        return self._configured

    def chat_json(self, messages: list[dict]) -> dict:
        return self._response


def test_analyze_404_when_file_missing(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr("app.services.contract_risk_service.get_groq_client", lambda: FakeGroqClient())
    response = client.post("/api/v1/files/999999/contract-risks")
    assert response.status_code == 404


def test_analyze_503_when_not_configured(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_record = _create_file(db_session, tmp_path)
    monkeypatch.setattr(
        "app.services.contract_risk_service.get_groq_client", lambda: FakeGroqClient(configured=False)
    )

    response = client.post(f"/api/v1/files/{file_record.id}/contract-risks")
    assert response.status_code == 503


def test_analyze_422_when_file_has_no_text(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_record = _create_file(db_session, tmp_path, content="")
    monkeypatch.setattr("app.services.contract_risk_service.get_groq_client", lambda: FakeGroqClient())

    response = client.post(f"/api/v1/files/{file_record.id}/contract-risks")
    assert response.status_code == 422


def test_analyze_returns_all_categories_in_order(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_record = _create_file(db_session, tmp_path, content="This agreement renews automatically each year.")
    monkeypatch.setattr("app.services.contract_risk_service.get_groq_client", lambda: FakeGroqClient())

    response = client.post(f"/api/v1/files/{file_record.id}/contract-risks")
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "contract.txt"
    assert [r["risk"] for r in body["risks"]] == RISK_CATEGORIES
    assert body["risks"][0]["present"] is True
    assert body["risks"][1]["present"] is False


def test_analyze_fills_missing_categories_defensively(client: TestClient, db_session: Session, tmp_path, monkeypatch) -> None:
    file_record = _create_file(db_session, tmp_path, content="Some contract text.")
    monkeypatch.setattr(
        "app.services.contract_risk_service.get_groq_client",
        lambda: FakeGroqClient(
            response={"risks": [{"risk": "Missing Signature", "present": True, "explanation": "No signature."}]}
        ),
    )

    response = client.post(f"/api/v1/files/{file_record.id}/contract-risks")
    assert response.status_code == 200
    body = response.json()
    assert [r["risk"] for r in body["risks"]] == RISK_CATEGORIES
    # Categories the model didn't return fall back to present=False with a note.
    unlimited_liability = next(r for r in body["risks"] if r["risk"] == "Unlimited Liability")
    assert unlimited_liability["present"] is False
    assert unlimited_liability["explanation"]
