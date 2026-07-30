from sqlalchemy.orm import Session

from app.models.summary import FileSummary
from app.repositories.file_repository import FileRepository
from app.repositories.summary_repository import SummaryRepository
from app.services.summary_service import SummaryService


class IndexedFileNotFoundError(Exception):
    pass


class FileSummaryService:
    """Orchestrates summary generation for an indexed file: looks up the file,
    delegates text extraction + LLM summarization to SummaryService, and
    persists the result via SummaryRepository."""

    def __init__(self, db: Session, organization_id: int | None = None, summary_service: SummaryService | None = None):
        self.file_repo = FileRepository(db, organization_id=organization_id)
        self.summary_repo = SummaryRepository(db)
        self.summary_service = summary_service or SummaryService()

    def get_summary(self, file_id: int) -> FileSummary | None:
        if self.file_repo.get(file_id) is None:
            return None
        return self.summary_repo.get_by_file(file_id)

    def generate_summary(self, file_id: int) -> FileSummary:
        file = self.file_repo.get(file_id)
        if file is None:
            raise IndexedFileNotFoundError(f"File {file_id} not found")

        data = self.summary_service.generate(file)
        return self.summary_repo.upsert(file_id, data, organization_id=file.organization_id)
