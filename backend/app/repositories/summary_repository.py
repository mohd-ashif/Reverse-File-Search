from sqlalchemy.orm import Session

from app.models.summary import FileSummary


class SummaryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_file(self, file_id: int) -> FileSummary | None:
        return self.db.query(FileSummary).filter(FileSummary.file_id == file_id).first()

    def upsert(self, file_id: int, data: dict) -> FileSummary:
        """Creates the file's summary, or overwrites it in place if one already
        exists (regenerating replaces the previous summary, it doesn't version it)."""
        existing = self.get_by_file(file_id)
        if existing is None:
            existing = FileSummary(file_id=file_id, **data)
            self.db.add(existing)
        else:
            for key, value in data.items():
                setattr(existing, key, value)
        self.db.commit()
        self.db.refresh(existing)
        return existing
