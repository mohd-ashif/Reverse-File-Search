from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.entities import DocumentEntitiesRead
from app.schemas.file import IndexedFileRead
from app.schemas.summary import FileSummaryRead
from app.services.file_service import FileService
from app.services.file_summary_service import FileSummaryService, IndexedFileNotFoundError
from app.services.summary_service import SummaryExtractionError, SummaryNotConfiguredError, SummaryProviderError

router = APIRouter()


@router.get("/", response_model=list[IndexedFileRead])
def list_files(folder_id: int | None = None, db: Session = Depends(get_db)) -> list[IndexedFileRead]:
    return FileService(db).list_files(folder_id)


@router.get("/{file_id}", response_model=IndexedFileRead)
def get_file(file_id: int, db: Session = Depends(get_db)) -> IndexedFileRead:
    file_record = FileService(db).get_file(file_id)
    if file_record is None:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found")
    return file_record


@router.get("/{file_id}/entities", response_model=DocumentEntitiesRead)
def get_entities(file_id: int, db: Session = Depends(get_db)) -> DocumentEntitiesRead:
    entities = FileService(db).get_entities(file_id)
    if entities is None:
        raise HTTPException(status_code=404, detail=f"No extracted entities for file {file_id}")
    return entities


@router.get("/{file_id}/summary", response_model=FileSummaryRead)
def get_summary(file_id: int, db: Session = Depends(get_db)) -> FileSummaryRead:
    summary = FileSummaryService(db).get_summary(file_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No summary generated yet for file {file_id}")
    return summary


@router.post("/{file_id}/summary", response_model=FileSummaryRead, status_code=201)
def generate_summary(file_id: int, db: Session = Depends(get_db)) -> FileSummaryRead:
    try:
        return FileSummaryService(db).generate_summary(file_id)
    except IndexedFileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SummaryNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SummaryExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SummaryProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
