from sqlalchemy.orm import Session

from app.models.document_entities import DocumentEntities
from app.models.file import IndexedFile
from app.repositories.entities_repository import EntitiesRepository
from app.repositories.file_repository import FileRepository
from app.repositories.tag_repository import TagRepository
from app.schemas.extracted_text import ExtractedTextRead
from app.schemas.tag import FileTagsRead


class FileService:
    def __init__(self, db: Session):
        self.repository = FileRepository(db)
        self.entities_repo = EntitiesRepository(db)
        self.tag_repo = TagRepository(db)

    def get_file(self, file_id: int) -> IndexedFile | None:
        return self.repository.get(file_id)

    def list_files(self, folder_id: int | None = None, tag: str | None = None) -> list[IndexedFile]:
        return self.repository.list_all(folder_id, tag)

    def get_entities(self, file_id: int) -> DocumentEntities | None:
        return self.entities_repo.get_by_file(file_id)

    def get_tags(self, file_id: int) -> FileTagsRead | None:
        if self.repository.get(file_id) is None:
            return None
        tags = [row.tag for row in self.tag_repo.get_by_file(file_id)]
        return FileTagsRead(file_id=file_id, tags=tags)

    def list_file_tags(self, folder_id: int | None = None) -> list[FileTagsRead]:
        grouped = self.tag_repo.list_grouped_by_file(folder_id)
        return [FileTagsRead(file_id=file_id, tags=tags) for file_id, tags in grouped.items()]

    def get_extracted_text(self, file_id: int) -> ExtractedTextRead | None:
        file_record = self.repository.get(file_id)
        if file_record is None:
            return None
        return ExtractedTextRead(
            file_id=file_record.id,
            filename=file_record.filename,
            corrected_text=file_record.corrected_text,
            was_corrected=file_record.corrected_text is not None,
        )
