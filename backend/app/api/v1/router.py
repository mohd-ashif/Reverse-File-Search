from fastapi import APIRouter

from app.api.v1.endpoints import files, folders, health, search, ws

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(folders.router, prefix="/folders", tags=["folders"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(ws.router, prefix="/ws", tags=["ws"])
