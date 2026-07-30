import asyncio
import logging
import threading
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_org_id, get_db, require_permission
from app.auth.decorators import audit_action
from app.auth.permissions import PermissionCode
from app.db.session import SessionLocal
from app.models.user import User
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
from app.services.scan_progress import ScanProgressTracker
from app.services.scanner_service import FileScannerService

logger = logging.getLogger(__name__)

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
def list_folders(
    db: Session = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
    _: User = Depends(require_permission(PermissionCode.FOLDER_READ)),
) -> list[FolderRead]:
    return FolderService(db, organization_id=org_id).list_folders()


@router.post("/", response_model=FolderRead, status_code=201)
@audit_action("folder.created", resource_type="folder")
def add_folder(
    payload: FolderCreate,
    request: Request,
    db: Session = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
    current_user: User = Depends(require_permission(PermissionCode.FOLDER_CREATE)),
) -> FolderRead:
    try:
        return FolderService(db, organization_id=org_id).add_folder(payload.path)
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
def estimate_folder(
    payload: FolderCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PermissionCode.FOLDER_READ)),
) -> FolderEstimate:
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
@audit_action("folder.deleted", resource_type="folder")
def remove_folder(
    folder_id: int,
    request: Request,
    db: Session = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
    current_user: User = Depends(require_permission(PermissionCode.FOLDER_DELETE)),
) -> None:
    try:
        FolderService(db, organization_id=org_id).remove_folder(folder_id)
    except FolderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{folder_id}/scan")
def scan_folder(
    folder_id: int,
    skip_sensitive: bool = True,
    db: Session = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
    _: User = Depends(require_permission(PermissionCode.FOLDER_SCAN)),
) -> dict[str, ScanResult | IndexResult]:
    try:
        folder = FolderService(db, organization_id=org_id).get_folder(folder_id)
    except FolderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    scan_result = FileScannerService(db).scan_folder(folder, skip_sensitive=skip_sensitive)
    index_result = IndexingPipeline(db, organization_id=org_id).process_pending(folder_id=folder_id)
    return {"scan": scan_result, "index": index_result}


@router.post("/{folder_id}/scan/start")
async def start_folder_scan(
    folder_id: int,
    skip_sensitive: bool = True,
    db: Session = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
    _: User = Depends(require_permission(PermissionCode.FOLDER_SCAN)),
) -> dict[str, str]:
    """Kicks off a scan + index run in the background and returns a scan_id.

    Connect to `/api/v1/ws/scan/{scan_id}` immediately after to receive live
    stage-by-stage progress; the run finishes with a `summary` (or `error`)
    event over that same socket.
    """
    try:
        FolderService(db, organization_id=org_id).get_folder(folder_id)
    except FolderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    scan_id = uuid.uuid4().hex
    loop = asyncio.get_running_loop()

    def run() -> None:
        session = SessionLocal()
        tracker = ScanProgressTracker(scan_id=scan_id, folder_id=folder_id, loop=loop)
        try:
            folder = FolderService(session, organization_id=org_id).get_folder(folder_id)
            scan_result = FileScannerService(session).scan_folder(
                folder, skip_sensitive=skip_sensitive, progress=tracker
            )
            index_result = IndexingPipeline(session, organization_id=org_id).process_pending(
                folder_id=folder_id, progress=tracker
            )
            tracker.summary(scan_result, index_result)
        except Exception as exc:  # noqa: BLE001 - must reach the client as an error event, not crash a thread silently
            logger.exception("Background scan %s for folder %s failed", scan_id, folder_id)
            tracker.error(str(exc))
        finally:
            session.close()

    threading.Thread(target=run, name=f"scan-{scan_id}", daemon=True).start()
    return {"scan_id": scan_id}
