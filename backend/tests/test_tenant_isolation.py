"""Cross-tenant isolation: a member of org A must never be able to read,
list, or delete org B's folders/files via the API, even by guessing IDs."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.auth.permissions import ALL_PERMISSIONS
from app.auth.repository import UserRepository
from app.auth.security import hash_password
from app.models.file import FileIndexStatus, FileType, IndexedFile
from app.models.folder import MonitoredFolder
from app.models.organization import Organization


def _make_org_with_admin_client(client: TestClient, db_session: Session, name: str) -> tuple[Organization, TestClient]:
    org = Organization(name=name, slug=name.lower().replace(" ", "-"))
    db_session.add(org)
    db_session.flush()

    user = UserRepository(db_session).create(
        email=f"user@{org.slug}.test", hashed_password=hash_password("Str0ng!Passw0rd")
    )
    user.is_active = True
    user.is_verified = True
    user.organization_id = org.id
    db_session.commit()
    db_session.refresh(user)

    perms = [code for code, _ in ALL_PERMISSIONS]
    token = create_access_token(user.id, org.id, perms, ["Organization Admin"])

    scoped_client = TestClient(client.app)
    scoped_client.headers.update({"Authorization": f"Bearer {token}"})
    return org, scoped_client


def _make_folder_with_file(db_session: Session, org: Organization, tmp_path: Path) -> tuple[MonitoredFolder, IndexedFile]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    folder = MonitoredFolder(path=str(tmp_path), organization_id=org.id)
    db_session.add(folder)
    db_session.flush()

    target = tmp_path / "secret.txt"
    target.write_text("confidential")
    file_record = IndexedFile(
        folder_id=folder.id,
        organization_id=org.id,
        absolute_path=str(target),
        filename="secret.txt",
        extension=".txt",
        file_type=FileType.TXT,
        size_bytes=target.stat().st_size,
        checksum="deadbeef",
        mtime=target.stat().st_mtime,
        status=FileIndexStatus.EMBEDDED,
    )
    db_session.add(file_record)
    db_session.flush()
    return folder, file_record


def test_list_folders_excludes_other_organizations(client: TestClient, db_session: Session, tmp_path) -> None:
    org_a, client_a = _make_org_with_admin_client(client, db_session, "Org A")
    org_b, client_b = _make_org_with_admin_client(client, db_session, "Org B")
    folder_a, _file_a = _make_folder_with_file(db_session, org_a, tmp_path / "a")
    folder_b, _file_b = _make_folder_with_file(db_session, org_b, tmp_path / "b")

    response_a = client_a.get("/api/v1/folders/")
    ids_visible_to_a = {row["id"] for row in response_a.json()}
    assert folder_a.id in ids_visible_to_a
    assert folder_b.id not in ids_visible_to_a

    response_b = client_b.get("/api/v1/folders/")
    ids_visible_to_b = {row["id"] for row in response_b.json()}
    assert folder_b.id in ids_visible_to_b
    assert folder_a.id not in ids_visible_to_b


def test_cannot_delete_another_organizations_folder(client: TestClient, db_session: Session, tmp_path) -> None:
    org_a, client_a = _make_org_with_admin_client(client, db_session, "Org C")
    org_b, client_b = _make_org_with_admin_client(client, db_session, "Org D")
    _folder_a, _file_a = _make_folder_with_file(db_session, org_a, tmp_path / "c")
    folder_b, _file_b = _make_folder_with_file(db_session, org_b, tmp_path / "d")

    response = client_a.delete(f"/api/v1/folders/{folder_b.id}")

    assert response.status_code == 404


def test_cannot_read_another_organizations_file(client: TestClient, db_session: Session, tmp_path) -> None:
    org_a, client_a = _make_org_with_admin_client(client, db_session, "Org E")
    org_b, _client_b = _make_org_with_admin_client(client, db_session, "Org F")
    _folder_a, _file_a = _make_folder_with_file(db_session, org_a, tmp_path / "e")
    _folder_b, file_b = _make_folder_with_file(db_session, org_b, tmp_path / "f")

    response = client_a.get(f"/api/v1/files/{file_b.id}")

    assert response.status_code == 404


def test_cannot_read_another_organizations_file_summary(client: TestClient, db_session: Session, tmp_path) -> None:
    org_a, client_a = _make_org_with_admin_client(client, db_session, "Org G")
    org_b, _client_b = _make_org_with_admin_client(client, db_session, "Org H")
    _folder_a, _file_a = _make_folder_with_file(db_session, org_a, tmp_path / "g")
    _folder_b, file_b = _make_folder_with_file(db_session, org_b, tmp_path / "h")

    response = client_a.get(f"/api/v1/files/{file_b.id}/summary")

    assert response.status_code == 404
