from pathlib import Path

from sqlalchemy.orm import Session

from app.models.chunk import FileChunk
from app.models.file import FileIndexStatus, IndexedFile
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.file_repository import FileRepository
from app.schemas.scan import IndexResult
from app.services.chunking import chunk_text
from app.services.embedding_service import get_embedding_service
from app.services.extractors import get_extractor
from app.services.vector_store import get_vector_store


class IndexingPipeline:
    """Extracts text, chunks it, generates embeddings, and stores them in Chroma."""

    def __init__(self, db: Session):
        self.db = db
        self.file_repo = FileRepository(db)
        self.chunk_repo = ChunkRepository(db)
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()

    def process_file(self, file: IndexedFile) -> None:
        try:
            extractor = get_extractor(file.file_type)
            text = extractor.extract(Path(file.absolute_path))
        except Exception as exc:  # noqa: BLE001 - extraction failures must not crash the pipeline
            self._mark_failed(file, str(exc))
            return

        file.status = FileIndexStatus.EXTRACTED
        file.error_message = None
        self.file_repo.update(file)

        chunks = chunk_text(text)
        if not chunks:
            file.status = FileIndexStatus.EMBEDDED
            self.file_repo.update(file)
            return

        try:
            embeddings = self.embedding_service.embed(chunks)
        except Exception as exc:  # noqa: BLE001 - embedding failures must not crash the pipeline
            self._mark_failed(file, str(exc))
            return

        chroma_ids = [f"file-{file.id}-chunk-{index}" for index in range(len(chunks))]
        metadatas = [
            {"file_id": file.id, "absolute_path": file.absolute_path, "chunk_index": index}
            for index in range(len(chunks))
        ]
        self.vector_store.upsert(ids=chroma_ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)

        chunk_rows = [
            FileChunk(file_id=file.id, chunk_index=index, chroma_id=chroma_ids[index], char_count=len(chunks[index]))
            for index in range(len(chunks))
        ]
        self.chunk_repo.create_many(chunk_rows)

        file.status = FileIndexStatus.EMBEDDED
        self.file_repo.update(file)

    def process_pending(self, folder_id: int | None = None) -> IndexResult:
        result = IndexResult()
        for file in self.file_repo.list_by_status(FileIndexStatus.PENDING, folder_id=folder_id):
            self.process_file(file)
            if file.status == FileIndexStatus.EMBEDDED:
                result.extracted += 1
                result.embedded += 1
            elif file.status == FileIndexStatus.FAILED:
                result.failed += 1
        return result

    def _mark_failed(self, file: IndexedFile, error_message: str) -> None:
        file.status = FileIndexStatus.FAILED
        file.error_message = error_message
        self.file_repo.update(file)
