from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.search import SearchQuery, SearchResponse
from app.services.search_service import SearchService
from app.services.search_stream_service import SearchStreamService

router = APIRouter()


@router.post("/", response_model=SearchResponse)
def search(payload: SearchQuery, db: Session = Depends(get_db)) -> SearchResponse:
    return SearchService(db).search(payload)


@router.post("/stream")
def search_stream(payload: SearchQuery, db: Session = Depends(get_db)) -> StreamingResponse:
    return StreamingResponse(
        SearchStreamService(db).stream(payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
