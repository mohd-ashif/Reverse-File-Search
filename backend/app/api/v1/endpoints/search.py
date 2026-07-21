from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.search import SearchQuery, SearchResponse
from app.schemas.search_suggestions import SearchSuggestionsRead
from app.services.search_service import SearchService
from app.services.search_stream_service import SearchStreamService
from app.services.search_suggestion_service import SearchSuggestionService

router = APIRouter()


@router.get("/suggestions", response_model=SearchSuggestionsRead)
def get_search_suggestions(q: str = "", db: Session = Depends(get_db)) -> SearchSuggestionsRead:
    """Autocomplete data for the search box: recent/popular past searches
    plus AI-generated suggestions. Registered before POST "/" so the literal
    "suggestions" path isn't shadowed by any future dynamic route."""
    return SearchSuggestionService(db).get_suggestions(q)


@router.post("/", response_model=SearchResponse)
def search(payload: SearchQuery, db: Session = Depends(get_db)) -> SearchResponse:
    SearchSuggestionService(db).log_query(payload.query)
    return SearchService(db).search(payload)


@router.post("/stream")
def search_stream(payload: SearchQuery, db: Session = Depends(get_db)) -> StreamingResponse:
    SearchSuggestionService(db).log_query(payload.query)
    return StreamingResponse(
        SearchStreamService(db).stream(payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
