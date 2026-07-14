from sqlalchemy.orm import Session

from app.models.file import IndexedFile
from app.repositories.file_repository import FileRepository


class FileService:
    def __init__(self, db: Session):
        self.repository = FileRepository(db)

    def get_file(self, file_id: int) -> IndexedFile | None:
        return self.repository.get(file_id)

    def list_files(self, folder_id: int | None = None) -> list[IndexedFile]:
        return self.repository.list_all(folder_id)
