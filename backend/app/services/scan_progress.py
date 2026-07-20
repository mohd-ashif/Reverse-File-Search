import asyncio
import time
from dataclasses import dataclass, field

from app.schemas.scan import IndexResult, ScanResult
from app.services.ws_manager import scan_manager


class ScanStage:
    FINDING_FILES = "finding_files"
    READING_METADATA = "reading_metadata"
    EXTRACTING_TEXT = "extracting_text"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    SAVING_TO_DATABASE = "saving_to_database"
    FINALIZING = "finalizing"


@dataclass
class FailedFileInfo:
    filename: str
    path: str
    error: str


@dataclass
class ScanProgressTracker:
    """Emits scan/index progress over the scan's websocket feed.

    Runs from a background thread (scanning + indexing are synchronous), so
    every broadcast is handed to the FastAPI event loop via
    `run_coroutine_threadsafe` rather than awaited directly.
    """

    scan_id: str
    folder_id: int
    loop: asyncio.AbstractEventLoop
    start_time: float = field(default_factory=time.monotonic)
    files_total: int = 0
    files_processed: int = 0
    succeeded_files: list[str] = field(default_factory=list)
    failed_files: list[FailedFileInfo] = field(default_factory=list)

    def _broadcast(self, message: dict) -> None:
        message.setdefault("scan_id", self.scan_id)
        message["elapsed_seconds"] = round(time.monotonic() - self.start_time, 1)
        asyncio.run_coroutine_threadsafe(scan_manager.broadcast(self.scan_id, message), self.loop)

    def set_total(self, total: int) -> None:
        self.files_total = total

    def stage(self, stage: str, current_file: str | None = None) -> None:
        remaining = max(self.files_total - self.files_processed, 0)
        elapsed = time.monotonic() - self.start_time
        estimated_remaining_seconds = None
        if self.files_processed > 0 and self.files_total > 0:
            seconds_per_file = elapsed / self.files_processed
            estimated_remaining_seconds = round(seconds_per_file * remaining, 1)

        self._broadcast(
            {
                "type": "progress",
                "stage": stage,
                "current_file": current_file,
                "files_processed": self.files_processed,
                "files_total": self.files_total,
                "files_remaining": remaining,
                "estimated_remaining_seconds": estimated_remaining_seconds,
            }
        )

    def file_succeeded(self, filename: str) -> None:
        self.files_processed += 1
        self.succeeded_files.append(filename)

    def file_failed(self, filename: str, path: str, error: str) -> None:
        self.files_processed += 1
        self.failed_files.append(FailedFileInfo(filename=filename, path=path, error=error))

    def summary(self, scan_result: ScanResult, index_result: IndexResult) -> None:
        self._broadcast(
            {
                "type": "summary",
                "scan": scan_result.model_dump(),
                "index": index_result.model_dump(),
                "succeeded_files": self.succeeded_files,
                "failed_files": [
                    {"filename": f.filename, "path": f.path, "error": f.error} for f in self.failed_files
                ],
            }
        )

    def error(self, message: str) -> None:
        self._broadcast({"type": "error", "message": message})
