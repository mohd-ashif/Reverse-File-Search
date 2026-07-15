from sqlalchemy.orm import Session

from app.models.document_entities import DocumentEntities
from app.models.file import IndexedFile
from app.repositories.entities_repository import EntitiesRepository
from app.repositories.file_repository import FileRepository


class FileService:
    def __init__(self, db: Session):
        self.repository = FileRepository(db)
        self.entities_repo = EntitiesRepository(db)

    def get_file(self, file_id: int) -> IndexedFile | None:
        return self.repository.get(file_id)

    def list_files(self, folder_id: int | None = None) -> list[IndexedFile]:
        return self.repository.list_all(folder_id)

    def get_entities(self, file_id: int) -> DocumentEntities | None:
        return self.entities_repo.get_by_file(file_id)
