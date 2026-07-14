from sqlalchemy.orm import Session

from app.repositories.file_repository import FileRepository
from app.schemas.search import SearchQuery, SearchResponse, SearchResultItem
from app.services.answer_service import AnswerService
from app.services.embedding_service import get_embedding_service

from app.services.query_rewrite_service import QueryRewriteService
from app.services.vector_store import get_vector_store


class SearchService:
    """Reverse file search: embeds the query and matches it against indexed chunks.

    Optionally rewrites the query via Groq before embedding it (QueryRewriteService)
    to improve retrieval on short or acronym-heavy queries, and optionally synthesizes
    a grounded AI answer on top of the retrieved chunks (AnswerService). Retrieval,
    rewriting, and answer synthesis are deliberately separate steps so search keeps
    working even if either Groq-backed step is disabled or fails.
    """

    def __init__(
        self,
        db: Session,
        answer_service: AnswerService | None = None,
        query_rewrite_service: QueryRewriteService | None = None,
    ):
        self.db = db
        self.file_repo = FileRepository(db)
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
        self.answer_service = answer_service or AnswerService()
        self.query_rewrite_service = query_rewrite_service or QueryRewriteService()

    def retrieve(self, query_text: str, top_k: int) -> list[SearchResultItem]:
        if not query_text.strip():
            return []

        query_embedding = self.embedding_service.embed([query_text])[0]
        raw = self.vector_store.query(query_embedding, top_k=top_k)

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

    def rewrite_query(self, query: SearchQuery) -> str:
        """Returns the query text to embed for retrieval — rewritten via Groq for
        better recall unless the caller opted out or rewriting is unavailable."""
        return self.query_rewrite_service.rewrite(query.query) if query.rewrite_query else query.query

    def search(self, query: SearchQuery) -> SearchResponse:
        rewritten_query = self.rewrite_query(query)
        results = self.retrieve(rewritten_query, query.top_k)
        answer = (
            self.answer_service.answer(query.query, results, query.history) if query.generate_answer else None
        )
        return SearchResponse(results=results, answer=answer, rewritten_query=rewritten_query)
