from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.folder import FolderCreate, FolderRead
from app.schemas.scan import FolderEstimate, IndexResult, ScanResult
from app.services.folder_access_guard import (
    FolderLockedError,
    FolderNetworkUnavailableError,
    FolderPathInvalidError,
    FolderPathMissingError,
    FolderPermissionDeniedError,
)
from app.services.folder_service import (
    FolderAlreadyMonitoredError,
    FolderNotFoundError,
    FolderService,
    FolderTooBroadError,
    InvalidFolderPathError,
)
from app.services.indexing_pipeline import IndexingPipeline
from app.services.scanner_service import FileScannerService

router = APIRouter()


def _raise_for_folder_access_error(exc: Exception) -> None:
    """Maps folder existence/access failures to a descriptive HTTP response."""
    if isinstance(exc, (FolderTooBroadError, InvalidFolderPathError, FolderPathInvalidError)):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, FolderPathMissingError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, FolderPermissionDeniedError):
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if isinstance(exc, FolderLockedError):
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    if isinstance(exc, FolderNetworkUnavailableError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    raise exc


@router.get("/", response_model=list[FolderRead])
def list_folders(db: Session = Depends(get_db)) -> list[FolderRead]:
    return FolderService(db).list_folders()


@router.post("/", response_model=FolderRead, status_code=201)
def add_folder(payload: FolderCreate, db: Session = Depends(get_db)) -> FolderRead:
    try:
        return FolderService(db).add_folder(payload.path)
    except FolderAlreadyMonitoredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (
        FolderTooBroadError,
        InvalidFolderPathError,
        FolderPathInvalidError,
        FolderPathMissingError,
        FolderPermissionDeniedError,
        FolderLockedError,
        FolderNetworkUnavailableError,
    ) as exc:
        _raise_for_folder_access_error(exc)
        raise  # unreachable, keeps type checkers happy


@router.post("/estimate", response_model=FolderEstimate)
def estimate_folder(payload: FolderCreate, db: Session = Depends(get_db)) -> FolderEstimate:
    try:
        return FolderService(db).estimate_folder(payload.path)
    except (
        FolderTooBroadError,
        InvalidFolderPathError,
        FolderPathInvalidError,
        FolderPathMissingError,
        FolderPermissionDeniedError,
        FolderLockedError,
        FolderNetworkUnavailableError,
    ) as exc:
        _raise_for_folder_access_error(exc)
        raise  # unreachable, keeps type checkers happy


@router.delete("/{folder_id}", status_code=204)
def remove_folder(folder_id: int, db: Session = Depends(get_db)) -> None:
    try:
        FolderService(db).remove_folder(folder_id)
    except FolderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{folder_id}/scan")
def scan_folder(
    folder_id: int, skip_sensitive: bool = True, db: Session = Depends(get_db)
) -> dict[str, ScanResult | IndexResult]:
    try:
        folder = FolderService(db).get_folder(folder_id)
    except FolderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    scan_result = FileScannerService(db).scan_folder(folder, skip_sensitive=skip_sensitive)
    index_result = IndexingPipeline(db).process_pending(folder_id=folder_id)
    return {"scan": scan_result, "index": index_result}
