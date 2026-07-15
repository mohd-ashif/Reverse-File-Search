from sqlalchemy.orm import Session

from app.models.document_entities import DocumentEntities


class EntitiesRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_file(self, file_id: int) -> DocumentEntities | None:
        return self.db.query(DocumentEntities).filter(DocumentEntities.file_id == file_id).first()

    def upsert(self, file_id: int, data: dict) -> DocumentEntities:
        """Creates the file's extracted entities, or overwrites them in place if
        already present (re-indexing replaces the previous extraction)."""
        existing = self.get_by_file(file_id)
        if existing is None:
            existing = DocumentEntities(file_id=file_id, **data)
            self.db.add(existing)
        else:
            for key, value in data.items():
                setattr(existing, key, value)
        self.db.commit()
        self.db.refresh(existing)
        return existing
