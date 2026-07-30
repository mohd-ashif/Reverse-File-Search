from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.file import FileIndexStatus, IndexedFile
from app.models.tag import FileTag


class FileRepository:
    """`organization_id=None` (superadmin/legacy tokens) applies no tenant
    filter - see `app.auth.dependencies.get_current_org_id`. Any real org
    member's id scopes every query to their own organization's files."""

    def __init__(self, db: Session, organization_id: int | None = None):
        self.db = db
        self.organization_id = organization_id

    def _scoped(self, query):
        if self.organization_id is not None:
            query = query.filter(IndexedFile.organization_id == self.organization_id)
        return query

    def get(self, file_id: int) -> IndexedFile | None:
        return self._scoped(self.db.query(IndexedFile).filter(IndexedFile.id == file_id)).first()

    def get_by_path(self, absolute_path: str) -> IndexedFile | None:
        return self._scoped(
            self.db.query(IndexedFile).filter(IndexedFile.absolute_path == absolute_path)
        ).first()

    def list_by_folder(self, folder_id: int) -> list[IndexedFile]:
        return self._scoped(self.db.query(IndexedFile).filter(IndexedFile.folder_id == folder_id)).all()

    def list_by_status(self, status: FileIndexStatus, folder_id: int | None = None) -> list[IndexedFile]:
        query = self._scoped(self.db.query(IndexedFile).filter(IndexedFile.status == status))
        if folder_id is not None:
            query = query.filter(IndexedFile.folder_id == folder_id)
        return query.all()

    def list_all(self, folder_id: int | None = None, tag: str | None = None) -> list[IndexedFile]:
        query = self._scoped(self.db.query(IndexedFile))
        if folder_id is not None:
            query = query.filter(IndexedFile.folder_id == folder_id)
        if tag is not None:
            query = query.join(FileTag, FileTag.file_id == IndexedFile.id).filter(
                func.lower(FileTag.tag) == tag.lower()
            )
        return query.order_by(IndexedFile.id).all()

    def create(self, file_record: IndexedFile) -> IndexedFile:
        if self.organization_id is not None and file_record.organization_id is None:
            file_record.organization_id = self.organization_id
        self.db.add(file_record)
        self.db.commit()
        self.db.refresh(file_record)
        return file_record

    def update(self, file_record: IndexedFile) -> IndexedFile:
        self.db.commit()
        self.db.refresh(file_record)
        return file_record

    def delete(self, file_record: IndexedFile) -> None:
        self.db.delete(file_record)
        self.db.commit()
