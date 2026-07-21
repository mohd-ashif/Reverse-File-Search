from sqlalchemy.orm import Session

from app.models.file import IndexedFile
from app.models.tag import FileTag


class TagRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_file(self, file_id: int) -> list[FileTag]:
        return self.db.query(FileTag).filter(FileTag.file_id == file_id).order_by(FileTag.tag).all()

    def replace_tags(self, file_id: int, tags: list[str]) -> list[FileTag]:
        """Overwrites a file's tags with the given set (regenerating replaces
        the previous tags, it doesn't merge with them)."""
        self.db.query(FileTag).filter(FileTag.file_id == file_id).delete()
        self.db.add_all([FileTag(file_id=file_id, tag=tag) for tag in tags])
        self.db.commit()
        return self.get_by_file(file_id)

    def list_grouped_by_file(self, folder_id: int | None = None) -> dict[int, list[str]]:
        """Returns {file_id: [tags]} for every file that has at least one tag,
        optionally scoped to a folder. Used to render tag badges in bulk
        without an N+1 query per file."""
        query = self.db.query(FileTag.file_id, FileTag.tag)
        if folder_id is not None:
            query = query.join(IndexedFile, IndexedFile.id == FileTag.file_id).filter(
                IndexedFile.folder_id == folder_id
            )
        grouped: dict[int, list[str]] = {}
        for file_id, tag in query.order_by(FileTag.tag).all():
            grouped.setdefault(file_id, []).append(tag)
        return grouped
