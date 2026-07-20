import logging
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models.chunk import FileChunk
from app.models.file import FileIndexStatus, FileType, IndexedFile
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.entities_repository import EntitiesRepository
from app.repositories.file_repository import FileRepository
from app.repositories.tag_repository import TagRepository
from app.schemas.scan import IndexResult
from app.services.chunking import chunk_text
from app.services.embedding_service import get_embedding_service
from app.services.entity_extraction_service import EntityExtractionService
from app.services.extractors import get_extractor
from app.services.ocr_correction_service import OCRCorrectionService
from app.services.scan_progress import ScanStage
from app.services.tag_extraction_service import TagExtractionService
from app.services.vector_store import get_vector_store

if TYPE_CHECKING:
    from app.services.scan_progress import ScanProgressTracker

logger = logging.getLogger(__name__)


class IndexingPipeline:
    """Extracts text, chunks it, generates embeddings, and stores them in Chroma.

    Also triggers best-effort structured entity extraction (invoice number,
    vendor, GST, PAN, etc.) and AI category tagging (Invoice, HR, Medical,
    etc.) once a file finishes embedding — see `_extract_entities_safely` and
    `_generate_tags_safely`, neither of which ever lets a failure affect the
    file's indexing status. For image files, OCR text is also passed through
    best-effort mistake correction (see `_correct_ocr_safely`) before
    chunking/embedding/entity/tag extraction all run on the corrected text.
    """

    def __init__(
        self,
        db: Session,
        entity_extraction_service: EntityExtractionService | None = None,
        tag_extraction_service: TagExtractionService | None = None,
        ocr_correction_service: OCRCorrectionService | None = None,
    ):
        self.db = db
        self.file_repo = FileRepository(db)
        self.chunk_repo = ChunkRepository(db)
        self.entities_repo = EntitiesRepository(db)
        self.tag_repo = TagRepository(db)
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
        self.entity_extraction_service = entity_extraction_service or EntityExtractionService()
        self.tag_extraction_service = tag_extraction_service or TagExtractionService()
        self.ocr_correction_service = ocr_correction_service or OCRCorrectionService()

    def process_file(self, file: IndexedFile, progress: "ScanProgressTracker | None" = None) -> None:
        if progress:
            progress.stage(ScanStage.READING_METADATA, file.filename)

        try:
            if progress:
                progress.stage(ScanStage.EXTRACTING_TEXT, file.filename)
            extractor = get_extractor(file.file_type)
            text = extractor.extract(Path(file.absolute_path))
        except Exception as exc:  # noqa: BLE001 - extraction failures must not crash the pipeline
            self._mark_failed(file, str(exc))
            if progress:
                progress.file_failed(file.filename, file.absolute_path, str(exc))
            return

        text = self._correct_ocr_safely(file, text)

        file.status = FileIndexStatus.EXTRACTED
        file.error_message = None
        self.file_repo.update(file)

        chunks = chunk_text(text)
        if not chunks:
            if progress:
                progress.stage(ScanStage.SAVING_TO_DATABASE, file.filename)
            file.status = FileIndexStatus.EMBEDDED
            self.file_repo.update(file)
            self._extract_entities_safely(file, text)
            self._generate_tags_safely(file, text)
            if progress:
                progress.file_succeeded(file.filename)
            return

        try:
            if progress:
                progress.stage(ScanStage.GENERATING_EMBEDDINGS, file.filename)
            embeddings = self.embedding_service.embed(chunks)
        except Exception as exc:  # noqa: BLE001 - embedding failures must not crash the pipeline
            self._mark_failed(file, str(exc))
            if progress:
                progress.file_failed(file.filename, file.absolute_path, str(exc))
            return

        if progress:
            progress.stage(ScanStage.SAVING_TO_DATABASE, file.filename)

        chroma_ids = [f"file-{file.id}-chunk-{index}" for index in range(len(chunks))]
        metadatas = [
            {
                "file_id": file.id,
                "folder_id": file.folder_id,
                "absolute_path": file.absolute_path,
                "chunk_index": index,
            }
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
        self._extract_entities_safely(file, text)
        self._generate_tags_safely(file, text)
        if progress:
            progress.file_succeeded(file.filename)

    def process_pending(
        self, folder_id: int | None = None, progress: "ScanProgressTracker | None" = None
    ) -> IndexResult:
        result = IndexResult()
        pending_files = list(self.file_repo.list_by_status(FileIndexStatus.PENDING, folder_id=folder_id))
        if progress:
            progress.set_total(len(pending_files))

        for file in pending_files:
            self.process_file(file, progress=progress)
            if file.status == FileIndexStatus.EMBEDDED:
                result.extracted += 1
                result.embedded += 1
            elif file.status == FileIndexStatus.FAILED:
                result.failed += 1

        if progress:
            progress.stage(ScanStage.FINALIZING)
        return result

    def _correct_ocr_safely(self, file: IndexedFile, text: str) -> str:
        """Best-effort OCR mistake correction (e.g. "Inv0ice" -> "Invoice"),
        applied only to image files since other file types aren't OCR'd. The
        corrected text becomes what's chunked/embedded/entity-and-tag-extracted,
        and is also persisted on the file record. Any failure here just keeps
        the original OCR text as-is — it must never fail indexing."""
        if file.file_type != FileType.IMAGE:
            file.corrected_text = None
            return text
        try:
            corrected = self.ocr_correction_service.correct(text)
        except Exception as exc:  # noqa: BLE001 - must never fail indexing
            logger.warning("OCR correction failed for file %s: %s", file.id, exc)
            file.corrected_text = None
            return text
        file.corrected_text = corrected
        return corrected

    def _mark_failed(self, file: IndexedFile, error_message: str) -> None:
        file.status = FileIndexStatus.FAILED
        file.error_message = error_message
        self.file_repo.update(file)

    def _extract_entities_safely(self, file: IndexedFile, text: str) -> None:
        """Best-effort structured entity extraction. Indexing has already
        succeeded by the time this runs; any failure here (Groq unreachable,
        unexpected response shape, etc.) is logged and swallowed so it can
        never turn a successfully indexed file into a failed one."""
        try:
            data = self.entity_extraction_service.extract(text)
            if data is not None:
                self.entities_repo.upsert(file.id, data)
        except Exception as exc:  # noqa: BLE001 - must never fail indexing
            logger.warning("Entity extraction failed for file %s: %s", file.id, exc)

    def _generate_tags_safely(self, file: IndexedFile, text: str) -> None:
        """Best-effort AI category tagging (Invoice, HR, Medical, etc.).
        Indexing has already succeeded by the time this runs; any failure
        here is logged and swallowed so it can never turn a successfully
        indexed file into a failed one."""
        try:
            tags = self.tag_extraction_service.extract(text)
            if tags is not None:
                self.tag_repo.replace_tags(file.id, tags)
        except Exception as exc:  # noqa: BLE001 - must never fail indexing
            logger.warning("Tag generation failed for file %s: %s", file.id, exc)
