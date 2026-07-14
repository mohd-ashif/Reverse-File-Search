from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services.folder_path_guard import TOO_BROAD_MESSAGE

BLOCKED_PATHS = [
    "C:\\",
    "C:\\Windows",
    "C:\\Users",
    "C:\\Users\\ADMIN",
    "C:\\Users\\ADMIN\\AppData",
    "C:\\Users\\ADMIN\\OneDrive",
    "/",
    "/etc",
    "/home",
    "/Users",
]


@pytest.mark.parametrize("path", BLOCKED_PATHS)
def test_add_folder_rejects_high_risk_paths(client: TestClient, path: str) -> None:
    response = client.post("/api/v1/folders/", json={"path": path})

    assert response.status_code == 400
    assert response.json()["detail"] == TOO_BROAD_MESSAGE


@pytest.mark.parametrize("child", ["Desktop", "Downloads", "Documents", "Pictures"])
def test_add_folder_allows_medium_risk_path_if_it_exists(client: TestClient, child: str) -> None:
    target = Path.home() / child
    if not target.is_dir():
        pytest.skip(f"No {child} folder on this machine to exercise the medium-risk path")

    response = client.post("/api/v1/folders/", json={"path": str(target)})

    assert response.status_code == 201


def test_add_folder_rejects_nonexistent_directory(client: TestClient) -> None:
    response = client.post(
        "/api/v1/folders/", json={"path": "C:\\Users\\ADMIN\\this-folder-does-not-exist-xyz"}
    )

    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_add_folder_accepts_valid_subfolder(client: TestClient, tmp_path) -> None:
    target = tmp_path / "reports"
    target.mkdir()

    response = client.post("/api/v1/folders/", json={"path": str(target)})

    assert response.status_code == 201
    body = response.json()
    assert body["path"] == str(target.resolve())
    assert body["is_active"] is True


def test_add_folder_rejects_duplicate(client: TestClient, tmp_path) -> None:
    target = tmp_path / "reports"
    target.mkdir()

    first = client.post("/api/v1/folders/", json={"path": str(target)})
    assert first.status_code == 201

    second = client.post("/api/v1/folders/", json={"path": str(target)})
    assert second.status_code == 409


def test_list_folders_includes_created_folder(client: TestClient, tmp_path) -> None:
    target = tmp_path / "invoices"
    target.mkdir()

    client.post("/api/v1/folders/", json={"path": str(target)})
    response = client.get("/api/v1/folders/")

    assert response.status_code == 200
    paths = [folder["path"] for folder in response.json()]
    assert str(target.resolve()) in paths
