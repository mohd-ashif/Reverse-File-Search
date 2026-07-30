from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_org_id, get_db, require_permission
from app.auth.decorators import audit_action
from app.auth.permissions import PermissionCode
from app.models.user import User
from app.schemas.search import SearchQuery, SearchResponse
from app.schemas.search_suggestions import SearchSuggestionsRead
from app.services.search_service import SearchService
from app.services.search_stream_service import SearchStreamService
from app.services.search_suggestion_service import SearchSuggestionService

router = APIRouter()


@router.get("/suggestions", response_model=SearchSuggestionsRead)
def get_search_suggestions(
    q: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PermissionCode.SEARCH_EXECUTE)),
) -> SearchSuggestionsRead:
    """Autocomplete data for the search box: recent/popular past searches
    plus AI-generated suggestions. Registered before POST "/" so the literal
    "suggestions" path isn't shadowed by any future dynamic route."""
    return SearchSuggestionService(db).get_suggestions(q)


@router.post("/", response_model=SearchResponse)
@audit_action("search.execute", resource_type="search")
def search(
    payload: SearchQuery,
    request: Request,
    db: Session = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
    current_user: User = Depends(require_permission(PermissionCode.SEARCH_EXECUTE)),
) -> SearchResponse:
    SearchSuggestionService(db).log_query(payload.query)
    return SearchService(db, organization_id=org_id).search(payload)


@router.post("/stream")
def search_stream(
    payload: SearchQuery,
    db: Session = Depends(get_db),
    org_id: int | None = Depends(get_current_org_id),
    _: User = Depends(require_permission(PermissionCode.SEARCH_EXECUTE)),
) -> StreamingResponse:
    SearchSuggestionService(db).log_query(payload.query)
    return StreamingResponse(
        SearchStreamService(db, organization_id=org_id).stream(payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
