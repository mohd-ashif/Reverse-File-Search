from pathlib import Path

from sqlalchemy.orm import Session

from app.models.folder import MonitoredFolder
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.file_repository import FileRepository
from app.repositories.folder_repository import FolderRepository
from app.schemas.scan import FolderEstimate
from app.services.folder_access_guard import (
    FolderLockedError,
    FolderNetworkUnavailableError,
    FolderPathInvalidError,
    FolderPathMissingError,
    FolderPermissionDeniedError,
    verify_folder_access,
)
from app.services.folder_path_guard import TOO_BROAD_MESSAGE, is_folder_path_too_broad
from app.services.scanner_service import estimate_folder_scan
from app.services.vector_store import get_vector_store

__all__ = [
    "FolderAlreadyMonitoredError",
    "FolderNotFoundError",
    "InvalidFolderPathError",
    "FolderTooBroadError",
    "FolderPathMissingError",
    "FolderPermissionDeniedError",
    "FolderLockedError",
    "FolderNetworkUnavailableError",
    "FolderService",
]


class FolderAlreadyMonitoredError(Exception):
    pass


class FolderNotFoundError(Exception):
    pass


class InvalidFolderPathError(Exception):
    pass


class FolderTooBroadError(Exception):
    pass


class FolderService:
    def __init__(self, db: Session):
        self.db = db
        self.folder_repo = FolderRepository(db)
        self.file_repo = FileRepository(db)
        self.chunk_repo = ChunkRepository(db)
        self.vector_store = get_vector_store()

    def list_folders(self) -> list[MonitoredFolder]:
        return self.folder_repo.list_all()

    def get_folder(self, folder_id: int) -> MonitoredFolder:
        folder = self.folder_repo.get(folder_id)
        if folder is None:
            raise FolderNotFoundError(f"Folder {folder_id} not found")
        return folder

    def add_folder(self, path: str) -> MonitoredFolder:
        resolved = Path(path).expanduser().resolve()

        if is_folder_path_too_broad(path, str(resolved)):
            raise FolderTooBroadError(TOO_BROAD_MESSAGE)

        verify_folder_access(path, resolved)

        absolute_path = str(resolved)
        if self.folder_repo.get_by_path(absolute_path) is not None:
            raise FolderAlreadyMonitoredError(f"'{absolute_path}' is already monitored")

        return self.folder_repo.create(MonitoredFolder(path=absolute_path))

    def estimate_folder(self, path: str) -> FolderEstimate:
        resolved = Path(path).expanduser().resolve()

        if is_folder_path_too_broad(path, str(resolved)):
            raise FolderTooBroadError(TOO_BROAD_MESSAGE)

        verify_folder_access(path, resolved)

        return estimate_folder_scan(resolved)

    def remove_folder(self, folder_id: int) -> None:
        folder = self.folder_repo.get(folder_id)
        if folder is None:
            raise FolderNotFoundError(f"Folder {folder_id} not found")

        for file_record in self.file_repo.list_by_folder(folder_id):
            chroma_ids = self.chunk_repo.delete_by_file(file_record.id)
            self.vector_store.delete(chroma_ids)

        self.folder_repo.delete(folder)
