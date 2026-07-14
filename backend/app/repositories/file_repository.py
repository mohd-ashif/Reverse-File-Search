from sqlalchemy.orm import Session

from app.models.file import FileIndexStatus, IndexedFile


class FileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, file_id: int) -> IndexedFile | None:
        return self.db.get(IndexedFile, file_id)

    def get_by_path(self, absolute_path: str) -> IndexedFile | None:
        return self.db.query(IndexedFile).filter(IndexedFile.absolute_path == absolute_path).first()

    def list_by_folder(self, folder_id: int) -> list[IndexedFile]:
        return self.db.query(IndexedFile).filter(IndexedFile.folder_id == folder_id).all()

    def list_by_status(self, status: FileIndexStatus, folder_id: int | None = None) -> list[IndexedFile]:
        query = self.db.query(IndexedFile).filter(IndexedFile.status == status)
        if folder_id is not None:
            query = query.filter(IndexedFile.folder_id == folder_id)
        return query.all()

    def list_all(self, folder_id: int | None = None) -> list[IndexedFile]:
        query = self.db.query(IndexedFile)
        if folder_id is not None:
            query = query.filter(IndexedFile.folder_id == folder_id)
        return query.order_by(IndexedFile.id).all()

    def create(self, file_record: IndexedFile) -> IndexedFile:
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
