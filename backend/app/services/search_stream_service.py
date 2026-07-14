from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.schemas.search import SearchQuery
from app.services.answer_stream_service import AnswerStreamService
from app.services.search_service import SearchService
from app.services.sse import sse_event


class SearchStreamService:
    """Composes retrieval with streamed answer generation for the `/search/stream`
    endpoint: retrieves chunks once, emits them as a 'results' event so the UI can
    render the match list immediately, then streams the AI answer over the same
    connection (see AnswerStreamService for the 'meta'/'token'/'done'/'error' events).
    """

    def __init__(
        self,
        db: Session,
        search_service: SearchService | None = None,
        answer_stream_service: AnswerStreamService | None = None,
    ) -> None:
        self.search_service = search_service or SearchService(db)
        self.answer_stream_service = answer_stream_service or AnswerStreamService()

    def stream(self, query: SearchQuery) -> Iterator[str]:
        results = self.search_service.retrieve(query.query, query.top_k)
        yield sse_event({"type": "results", "results": [item.model_dump() for item in results]})
        yield from self.answer_stream_service.stream(query.query, results, query.history)
