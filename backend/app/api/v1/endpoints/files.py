import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.action_items import ActionItemsResult
from app.schemas.compare import FileCompareRequest, FileCompareResult
from app.schemas.contract_risk import ContractRiskAnalysis
from app.schemas.entities import DocumentEntitiesRead
from app.schemas.extracted_text import ExtractedTextRead
from app.schemas.file import IndexedFileRead
from app.schemas.summary import FileSummaryRead
from app.schemas.tag import FileTagsRead
from app.services.action_item_service import (
    ActionItemExtractionError,
    ActionItemFileNotFoundError,
    ActionItemNotConfiguredError,
    ActionItemProviderError,
    ActionItemService,
)
from app.services.compare_service import (
    CompareExtractionError,
    CompareNotConfiguredError,
    CompareProviderError,
    FileCompareNotFoundError,
    FileCompareService,
)
from app.services.contract_risk_service import (
    ContractAnalysisExtractionError,
    ContractAnalysisNotConfiguredError,
    ContractAnalysisProviderError,
    ContractFileNotFoundError,
    ContractRiskService,
)
from app.services.file_service import FileService
from app.services.file_summary_service import FileSummaryService, IndexedFileNotFoundError
from app.services.summary_service import SummaryExtractionError, SummaryNotConfiguredError, SummaryProviderError

router = APIRouter()


@router.get("/", response_model=list[IndexedFileRead])
def list_files(folder_id: int | None = None, tag: str | None = None, db: Session = Depends(get_db)) -> list[IndexedFileRead]:
    return FileService(db).list_files(folder_id, tag)


@router.get("/tags", response_model=list[FileTagsRead])
def list_file_tags(folder_id: int | None = None, db: Session = Depends(get_db)) -> list[FileTagsRead]:
    """Tags for every file that has at least one, scoped to a folder if given.
    Registered before /{file_id} so the literal "tags" path isn't swallowed
    by that route."""
    return FileService(db).list_file_tags(folder_id)


@router.post("/compare", response_model=FileCompareResult)
def compare_files(payload: FileCompareRequest, db: Session = Depends(get_db)) -> FileCompareResult:
    """AI comparison of two indexed files: summary, differences, added/removed
    clauses, financial changes. Registered before /{file_id} so the literal
    "compare" path isn't swallowed by that route."""
    try:
        return FileCompareService(db).compare(payload.file_id_a, payload.file_id_b)
    except FileCompareNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CompareNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CompareExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except CompareProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{file_id}", response_model=IndexedFileRead)
def get_file(file_id: int, db: Session = Depends(get_db)) -> IndexedFileRead:
    file_record = FileService(db).get_file(file_id)
    if file_record is None:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found")
    return file_record


@router.get("/{file_id}/content")
def get_file_content(file_id: int, db: Session = Depends(get_db)) -> FileResponse:
    file_record = FileService(db).get_file(file_id)
    if file_record is None:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found")

    path = Path(file_record.absolute_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File is no longer available on disk")

    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=file_record.filename, content_disposition_type="inline")


@router.get("/{file_id}/tags", response_model=FileTagsRead)
def get_file_tags(file_id: int, db: Session = Depends(get_db)) -> FileTagsRead:
    tags = FileService(db).get_tags(file_id)
    if tags is None:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found")
    return tags


@router.get("/{file_id}/extracted-text", response_model=ExtractedTextRead)
def get_extracted_text(file_id: int, db: Session = Depends(get_db)) -> ExtractedTextRead:
    """The AI-corrected OCR text stored for this file (image files only —
    `corrected_text` is null and `was_corrected` is false for every other
    file type, since only OCR output goes through correction)."""
    result = FileService(db).get_extracted_text(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"File {file_id} not found")
    return result


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


@router.post("/{file_id}/contract-risks", response_model=ContractRiskAnalysis)
def analyze_contract_risks(file_id: int, db: Session = Depends(get_db)) -> ContractRiskAnalysis:
    """AI contract risk analysis: missing signature, unlimited liability,
    auto-renewal, late fees, termination clause — explained in plain language.
    Not persisted, generated fresh each call."""
    try:
        return ContractRiskService(db).analyze(file_id)
    except ContractFileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ContractAnalysisNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ContractAnalysisExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ContractAnalysisProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{file_id}/action-items", response_model=ActionItemsResult)
def extract_action_items(file_id: int, db: Session = Depends(get_db)) -> ActionItemsResult:
    """Extracts action items (person, task, deadline, priority) from a file's
    text — e.g. meeting notes. Not persisted, generated fresh each call."""
    try:
        return ActionItemService(db).extract(file_id)
    except ActionItemFileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ActionItemNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ActionItemExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ActionItemProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
