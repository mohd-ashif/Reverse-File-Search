from sqlalchemy.orm import Session

from app.models.chunk import FileChunk


class ChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_file(self, file_id: int) -> list[FileChunk]:
        return self.db.query(FileChunk).filter(FileChunk.file_id == file_id).all()

    def create_many(self, chunks: list[FileChunk]) -> list[FileChunk]:
        self.db.add_all(chunks)
        self.db.commit()
        for chunk in chunks:
            self.db.refresh(chunk)
        return chunks

    def delete_by_file(self, file_id: int) -> list[str]:
        chunks = self.list_by_file(file_id)
        chroma_ids = [chunk.chroma_id for chunk in chunks]
        for chunk in chunks:
            self.db.delete(chunk)
        self.db.commit()
        return chroma_ids
