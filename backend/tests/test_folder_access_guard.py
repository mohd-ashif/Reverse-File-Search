from pathlib import Path

import pytest

from app.services.folder_access_guard import (
    FolderLockedError,
    FolderNetworkUnavailableError,
    FolderPathInvalidError,
    FolderPathMissingError,
    FolderPermissionDeniedError,
    verify_folder_access,
)


def test_verify_folder_access_accepts_existing_readable_directory(tmp_path: Path) -> None:
    verify_folder_access(str(tmp_path), tmp_path)


def test_verify_folder_access_rejects_empty_path() -> None:
    with pytest.raises(FolderPathInvalidError):
        verify_folder_access("", Path())


def test_verify_folder_access_rejects_missing_directory(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"

    with pytest.raises(FolderPathMissingError, match="does not exist"):
        verify_folder_access(str(missing), missing)


def test_verify_folder_access_rejects_file_path(tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-folder.txt"
    file_path.write_text("hello")

    with pytest.raises(FolderPathInvalidError, match="not a folder"):
        verify_folder_access(str(file_path), file_path)


def test_verify_folder_access_rejects_permission_denied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "stat", lambda self: (_ for _ in ()).throw(PermissionError()))

    with pytest.raises(FolderPermissionDeniedError, match="Permission denied"):
        verify_folder_access(str(tmp_path), tmp_path)


def test_verify_folder_access_rejects_unreadable_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("os.access", lambda *_args, **_kwargs: False)

    with pytest.raises(FolderPermissionDeniedError, match="cannot read"):
        verify_folder_access(str(tmp_path), tmp_path)


def test_verify_folder_access_rejects_locked_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_locked(*_args: object, **_kwargs: object) -> None:
        exc = OSError("in use")
        exc.winerror = 32
        raise exc

    monkeypatch.setattr("os.scandir", _raise_locked)

    with pytest.raises(FolderLockedError, match="locked"):
        verify_folder_access(str(tmp_path), tmp_path)


def test_verify_folder_access_rejects_unreachable_network_path(monkeypatch: pytest.MonkeyPatch) -> None:
    network_path = Path("\\\\fileserver\\share\\reports")

    def _raise_network_error(self: Path) -> None:
        exc = OSError("network path not found")
        exc.winerror = 53
        raise exc

    monkeypatch.setattr(Path, "stat", _raise_network_error)

    with pytest.raises(FolderNetworkUnavailableError, match="unreachable"):
        verify_folder_access(str(network_path), network_path)
