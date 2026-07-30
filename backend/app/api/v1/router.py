from fastapi import APIRouter

from app.api.v1.endpoints import auth, files, folders, health, invitations, me, members, organizations, search, ws

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(me.router, prefix="/me", tags=["me"])
api_router.include_router(folders.router, prefix="/folders", tags=["folders"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(ws.router, prefix="/ws", tags=["ws"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(members.router, prefix="/members", tags=["members"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["invitations"])
