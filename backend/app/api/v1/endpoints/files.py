from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.file import IndexedFileRead
from app.services.file_service import FileService

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
