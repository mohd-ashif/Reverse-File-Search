from sqlalchemy.orm import Session

from app.repositories.chunk_repository import ChunkRepository
from app.repositories.file_repository import FileRepository
from app.schemas.search import SearchQuery, SearchResponse, SearchResultItem
from app.services.answer_service import AnswerService
from app.services.embedding_service import get_embedding_service

from app.services.query_rewrite_service import QueryRewriteService
from app.services.vector_store import get_vector_store

# Bounds prompt size/cost when answering "using only this file" — full-file
# retrieval bypasses top_k similarity search, so it needs its own cap.
MAX_FULL_FILE_CHUNKS = 40
MAX_FULL_FILE_CHARS = 24_000


class SearchService:
    """Reverse file search: embeds the query and matches it against indexed chunks.

    Optionally rewrites the query via Groq before embedding it (QueryRewriteService)
    to improve retrieval on short or acronym-heavy queries, and optionally synthesizes
    a grounded AI answer on top of the retrieved chunks (AnswerService). Retrieval,
    rewriting, and answer synthesis are deliberately separate steps so search keeps
    working even if either Groq-backed step is disabled or fails.

    Retrieval can be scoped via `SearchQuery.folder_id` (only chunks from files in
    that folder) or `SearchQuery.file_id` (only that file's own chunks, in full —
    see `retrieve_file` — since single-file Q&A needs exact content rather than a
    similarity-searched subset).
    """

    def __init__(
        self,
        db: Session,
        answer_service: AnswerService | None = None,
        query_rewrite_service: QueryRewriteService | None = None,
        embedding_service=None,
        vector_store=None,
    ):
        self.db = db
        self.file_repo = FileRepository(db)
        self.chunk_repo = ChunkRepository(db)
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_store = vector_store or get_vector_store()
        self.answer_service = answer_service or AnswerService()
        self.query_rewrite_service = query_rewrite_service or QueryRewriteService()

    def retrieve(self, query_text: str, top_k: int, folder_id: int | None = None) -> list[SearchResultItem]:
        if not query_text.strip():
            return []

        query_embedding = self.embedding_service.embed([query_text])[0]
        where = {"folder_id": folder_id} if folder_id is not None else None
        raw = self.vector_store.query(query_embedding, top_k=top_k, where=where)

        ids = raw.get("ids", [[]])[0]
        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]

        results: list[SearchResultItem] = []
        for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            file_id = metadata.get("file_id")
            file_record = self.file_repo.get(file_id) if file_id is not None else None
            if file_record is None:
                continue
            results.append(
                SearchResultItem(
                    file_id=file_record.id,
                    filename=file_record.filename,
                    chunk_text=document,
                    score=1.0 - distance if distance is not None else None,
                )
            )
        return results

    def retrieve_file(self, file_id: int) -> list[SearchResultItem]:
        """Returns a single file's own chunks, in document order, instead of a
        similarity-searched subset — so questions like "explain clause 4" or
        "who signed?" aren't at the mercy of embedding similarity missing the
        relevant passage. No score, since nothing was ranked."""
        file_record = self.file_repo.get(file_id)
        if file_record is None:
            return []

        chunks = sorted(self.chunk_repo.list_by_file(file_id), key=lambda chunk: chunk.chunk_index)
        if not chunks:
            return []

        chroma_ids = [chunk.chroma_id for chunk in chunks][:MAX_FULL_FILE_CHUNKS]
        raw = self.vector_store.get_by_ids(chroma_ids)
        documents_by_id = dict(zip(raw.get("ids", []), raw.get("documents", [])))

        results: list[SearchResultItem] = []
        total_chars = 0
        for chunk in chunks:
            document = documents_by_id.get(chunk.chroma_id)
            if not document:
                continue
            if total_chars >= MAX_FULL_FILE_CHARS:
                break
            results.append(
                SearchResultItem(file_id=file_record.id, filename=file_record.filename, chunk_text=document)
            )
            total_chars += len(document)
        return results

    def rewrite_query(self, query: SearchQuery) -> str:
        """Returns the query text to embed for retrieval — rewritten via Groq for
        better recall unless the caller opted out or rewriting is unavailable."""
        return self.query_rewrite_service.rewrite(query.query) if query.rewrite_query else query.query

    def retrieve_for_query(self, query: SearchQuery) -> tuple[str, list[SearchResultItem]]:
        """Single entry point for both /search/ and /search/stream: resolves the
        query's scope (single file > folder > unscoped) and returns the query
        text actually used for retrieval alongside the matched chunks."""
        if query.file_id is not None:
            return query.query, self.retrieve_file(query.file_id)
        rewritten_query = self.rewrite_query(query)
        return rewritten_query, self.retrieve(rewritten_query, query.top_k, folder_id=query.folder_id)

    def search(self, query: SearchQuery) -> SearchResponse:
        rewritten_query, results = self.retrieve_for_query(query)
        answer = (
            self.answer_service.answer(query.query, results, query.history) if query.generate_answer else None
        )
        return SearchResponse(results=results, answer=answer, rewritten_query=rewritten_query)
