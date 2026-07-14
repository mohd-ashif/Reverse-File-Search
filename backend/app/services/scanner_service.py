import os
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.file import IndexedFile
from app.models.folder import MonitoredFolder
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.file_repository import FileRepository
from app.schemas.scan import FolderEstimate, ScanResult
from app.services.file_type_detector import detect_file_type, is_supported
from app.services.sensitive_file_detector import is_sensitive_file
from app.services.vector_store import get_vector_store
from app.utils.file_utils import compute_checksum

MAX_SENSITIVE_SAMPLES = 10


def estimate_folder_scan(root: Path) -> FolderEstimate:
    """Walks a folder read-only to size up a scan before committing to it.

    Mirrors the directory/file filtering in ``FileScannerService.scan_folder``
    but never touches the database or computes checksums, so it stays cheap
    enough to run synchronously ahead of an actual scan.
    """
    total_files = 0
    supported_files = 0
    total_bytes = 0
    large_files = 0
    sensitive_files = 0
    sensitive_samples: list[str] = []

    for current_root, dirs, filenames in os.walk(root, topdown=True):
        current_path = Path(current_root)
        dirs[:] = [
            d
            for d in dirs
            if not _is_hidden_or_system(current_path / d) and d not in settings.SCAN_IGNORE_DIR_NAMES
        ]

        for filename in filenames:
            file_path = current_path / filename

            # Checked ahead of the hidden-file filter so dotfiles like `.env`
            # are still surfaced as sensitive rather than silently vanishing.
            if is_sensitive_file(file_path):
                sensitive_files += 1
                if len(sensitive_samples) < MAX_SENSITIVE_SAMPLES:
                    sensitive_samples.append(str(file_path.relative_to(root)))
                continue

            if _is_hidden_or_system(file_path):
                continue

            try:
                size_bytes = file_path.stat().st_size
            except OSError:
                continue

            total_files += 1
            if is_supported(file_path):
                supported_files += 1
                total_bytes += size_bytes
                if size_bytes >= settings.LARGE_FILE_THRESHOLD_BYTES:
                    large_files += 1

    approx_scan_seconds = 0.0
    if supported_files:
        approx_scan_seconds = max(
            supported_files / settings.ESTIMATE_FILES_PER_SECOND,
            total_bytes / settings.ESTIMATE_BYTES_PER_SECOND,
        )

    return FolderEstimate(
        path=str(root),
        estimated_files=total_files,
        estimated_supported_files=supported_files,
        unsupported_files=total_files - supported_files,
        approx_scan_seconds=round(approx_scan_seconds, 1),
        estimated_storage_bytes=total_bytes,
        large_files_detected=large_files,
        large_file_threshold_bytes=settings.LARGE_FILE_THRESHOLD_BYTES,
        sensitive_files_detected=sensitive_files,
        sensitive_file_samples=sensitive_samples,
    )


def _is_hidden_or_system(path: Path) -> bool:
    if path.name.startswith("."):
        return True
    try:
        attributes = path.stat().st_file_attributes
    except AttributeError:
        return False
    file_attribute_hidden = 0x2
    file_attribute_system = 0x4
    return bool(attributes & (file_attribute_hidden | file_attribute_system))


class FileScannerService:
    """Recursively scans a monitored folder and reconciles indexed_files with disk state."""

    def __init__(self, db: Session):
        self.db = db
        self.file_repo = FileRepository(db)
        self.chunk_repo = ChunkRepository(db)
        self.vector_store = get_vector_store()

    def scan_folder(self, folder: MonitoredFolder, skip_sensitive: bool = True) -> ScanResult:
        result = ScanResult(folder_id=folder.id)
        seen_paths: set[str] = set()

        for root, dirs, filenames in os.walk(folder.path, topdown=True):
            root_path = Path(root)
            dirs[:] = [
                d
                for d in dirs
                if not _is_hidden_or_system(root_path / d) and d not in settings.SCAN_IGNORE_DIR_NAMES
            ]

            for filename in filenames:
                file_path = root_path / filename

                if skip_sensitive and is_sensitive_file(file_path):
                    # Not added to seen_paths, so a previously-indexed sensitive
                    # file also gets reconciled away by _remove_missing below.
                    result.skipped_sensitive += 1
                    continue

                if _is_hidden_or_system(file_path) or not is_supported(file_path):
                    continue

                try:
                    stat = file_path.stat()
                except OSError:
                    continue

                absolute_path = str(file_path.resolve())
                seen_paths.add(absolute_path)

                existing = self.file_repo.get_by_path(absolute_path)
                if existing is None:
                    self._add_file(folder, file_path, absolute_path, stat.st_size, stat.st_mtime)
                    result.added += 1
                elif stat.st_mtime != existing.mtime:
                    if self._update_file(existing, file_path, stat.st_size, stat.st_mtime):
                        result.modified += 1
                    else:
                        result.skipped += 1
                else:
                    result.skipped += 1

        result.deleted = self._remove_missing(folder.id, seen_paths)
        return result

    def _add_file(self, folder: MonitoredFolder, file_path: Path, absolute_path: str, size_bytes: int, mtime: float) -> None:
        checksum = compute_checksum(file_path)
        file_record = IndexedFile(
            folder_id=folder.id,
            absolute_path=absolute_path,
            filename=file_path.name,
            extension=file_path.suffix.lower(),
            file_type=detect_file_type(file_path),
            size_bytes=size_bytes,
            checksum=checksum,
            mtime=mtime,
        )
        self.file_repo.create(file_record)

    def _update_file(self, existing: IndexedFile, file_path: Path, size_bytes: int, mtime: float) -> bool:
        checksum = compute_checksum(file_path)
        if checksum == existing.checksum:
            existing.mtime = mtime
            self.file_repo.update(existing)
            return False

        chroma_ids = self.chunk_repo.delete_by_file(existing.id)
        self.vector_store.delete(chroma_ids)

        existing.checksum = checksum
        existing.size_bytes = size_bytes
        existing.mtime = mtime
        existing.file_type = detect_file_type(file_path)
        existing.status = existing.status.PENDING
        existing.error_message = None
        self.file_repo.update(existing)
        return True

    def _remove_missing(self, folder_id: int, seen_paths: set[str]) -> int:
        deleted = 0
        for file_record in self.file_repo.list_by_folder(folder_id):
            if file_record.absolute_path in seen_paths:
                continue
            chroma_ids = self.chunk_repo.delete_by_file(file_record.id)
            self.vector_store.delete(chroma_ids)
            self.file_repo.delete(file_record)
            deleted += 1
        return deleted
