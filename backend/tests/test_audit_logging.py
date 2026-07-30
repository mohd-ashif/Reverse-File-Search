"""Login history + audit log rows written by the auth flows and by the
@audit_action-decorated folder/file endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.repository import UserRepository
from app.auth.security import hash_password
from app.models.audit import AuditLog, LoginHistory
from app.models.file import FileIndexStatus, FileType, IndexedFile
from app.models.folder import MonitoredFolder
from app.models.organization import Organization

EMAIL = "audit-login@example.com"
PASSWORD = "Str0ng!Passw0rd"


@pytest.fixture(autouse=True)
def _patch_mailer(monkeypatch) -> None:
    async def _noop(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr("app.auth.service.send_login_alert_email", _noop)
    monkeypatch.setattr("app.auth.service.send_verification_email", _noop)
    monkeypatch.setattr("app.auth.service.send_password_reset_email", _noop)


def _create_verified_user(db_session: Session, email: str = EMAIL):
    user = UserRepository(db_session).create(
        email=email, hashed_password=hash_password(PASSWORD), full_name="Audit Login Test"
    )
    user.is_active = True
    user.is_verified = True
    db_session.commit()
    db_session.refresh(user)
    return user


def _get_or_create_org(db_session: Session) -> Organization:
    org = db_session.query(Organization).filter(Organization.slug == "test-org").first()
    if org is None:
        org = Organization(name="Test Org", slug="test-org")
        db_session.add(org)
        db_session.flush()
    return org


def _create_indexed_file(db_session: Session, tmp_path, content: str = "hello world") -> IndexedFile:
    folder = MonitoredFolder(path=str(tmp_path), organization_id=_get_or_create_org(db_session).id)
    db_session.add(folder)
    db_session.flush()

    target = tmp_path / "sample.txt"
    target.write_text(content)

    file_record = IndexedFile(
        folder_id=folder.id,
        organization_id=folder.organization_id,
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


def test_successful_login_writes_login_history_and_audit_log(client: TestClient, db_session: Session) -> None:
    user = _create_verified_user(db_session)

    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 200

    login_rows = (
        db_session.query(LoginHistory)
        .filter(LoginHistory.email_attempted == EMAIL, LoginHistory.success.is_(True))
        .all()
    )
    assert len(login_rows) == 1

    # Scoped to this test's own user: `action == "login"` alone can match
    # historical rows already present in a shared (non-ephemeral) database.
    audit_rows = db_session.query(AuditLog).filter(AuditLog.action == "login", AuditLog.user_id == user.id).all()
    assert len(audit_rows) == 1
    assert audit_rows[0].user_id is not None


def test_failed_login_writes_login_history_with_failure_reason(client: TestClient, db_session: Session) -> None:
    _create_verified_user(db_session)

    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": "WrongPassword!1"})
    assert response.status_code == 401

    login_rows = (
        db_session.query(LoginHistory)
        .filter(LoginHistory.email_attempted == EMAIL, LoginHistory.success.is_(False))
        .all()
    )
    assert len(login_rows) == 1
    assert login_rows[0].failure_reason == "bad_password"


def test_folder_created_writes_audit_log_row(auth_client: TestClient, db_session: Session, tmp_path) -> None:
    response = auth_client.post("/api/v1/folders/", json={"path": str(tmp_path)})
    assert response.status_code == 201
    folder_id = response.json()["id"]

    audit_rows = db_session.query(AuditLog).filter(AuditLog.action == "folder.created").all()
    assert len(audit_rows) == 1
    # The generic @audit_action decorator captures resource_id from the
    # endpoint's own kwargs (folder_id/file_id/id) at call time; the folder
    # create endpoint's path has no such kwarg (the id is only known once the
    # service call returns), so it falls back to reading `.id` off the
    # endpoint's return value (a `FolderRead`).
    assert audit_rows[0].resource_id == str(folder_id)
    assert audit_rows[0].resource_type == "folder"


def test_folder_deleted_writes_audit_log_row_tied_to_folder_id(
    auth_client: TestClient, db_session: Session, tmp_path
) -> None:
    create_response = auth_client.post("/api/v1/folders/", json={"path": str(tmp_path)})
    assert create_response.status_code == 201
    folder_id = create_response.json()["id"]

    delete_response = auth_client.delete(f"/api/v1/folders/{folder_id}")
    assert delete_response.status_code == 204

    audit_rows = db_session.query(AuditLog).filter(AuditLog.action == "folder.deleted").all()
    assert len(audit_rows) == 1
    assert audit_rows[0].resource_id == str(folder_id)
    assert audit_rows[0].resource_type == "folder"


def test_file_download_writes_audit_log_row(auth_client: TestClient, db_session: Session, tmp_path) -> None:
    file_record = _create_indexed_file(db_session, tmp_path)

    response = auth_client.get(f"/api/v1/files/{file_record.id}/content")
    assert response.status_code == 200

    audit_rows = db_session.query(AuditLog).filter(AuditLog.action == "file.download").all()
    assert len(audit_rows) == 1
    assert audit_rows[0].resource_id == str(file_record.id)
    assert audit_rows[0].resource_type == "file"
