from fastapi.testclient import TestClient

from app.services.folder_path_guard import TOO_BROAD_MESSAGE


def test_estimate_folder_counts_supported_and_unsupported_files(client: TestClient, tmp_path) -> None:
    target = tmp_path / "reports"
    target.mkdir()
    (target / "notes.txt").write_text("hello world")
    (target / "sheet.xlsx").write_bytes(b"fake-xlsx-bytes")
    (target / "archive.zip").write_bytes(b"fake-zip-bytes")

    sub = target / "nested"
    sub.mkdir()
    (sub / "readme.md").write_text("# nested")

    response = client.post("/api/v1/folders/estimate", json={"path": str(target)})

    assert response.status_code == 200
    body = response.json()
    assert body["estimated_files"] == 4
    assert body["estimated_supported_files"] == 3
    assert body["unsupported_files"] == 1
    assert body["estimated_storage_bytes"] > 0
    assert body["approx_scan_seconds"] >= 0
    assert body["large_files_detected"] == 0


def test_estimate_folder_rejects_high_risk_paths(client: TestClient) -> None:
    response = client.post("/api/v1/folders/estimate", json={"path": "C:\\"})

    assert response.status_code == 400
    assert response.json()["detail"] == TOO_BROAD_MESSAGE


def test_estimate_folder_rejects_nonexistent_directory(client: TestClient) -> None:
    response = client.post(
        "/api/v1/folders/estimate", json={"path": "C:\\Users\\ADMIN\\this-folder-does-not-exist-xyz"}
    )

    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_estimate_folder_does_not_persist_folder(client: TestClient, tmp_path) -> None:
    target = tmp_path / "invoices"
    target.mkdir()
    (target / "invoice.pdf").write_bytes(b"fake-pdf-bytes")

    client.post("/api/v1/folders/estimate", json={"path": str(target)})
    response = client.get("/api/v1/folders/")

    assert str(target.resolve()) not in [folder["path"] for folder in response.json()]
