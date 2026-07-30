from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_ws
from app.auth.permissions import PermissionCode
from app.db.session import get_db
from app.services.ws_manager import scan_manager

router = APIRouter()


@router.websocket("/scan/{scan_id}")
async def scan_progress_ws(websocket: WebSocket, scan_id: str, db: Session = Depends(get_db)) -> None:
    user = await get_current_user_ws(websocket, db)
    if user is None:
        return  # get_current_user_ws already closed the socket with 4401

    payload = getattr(websocket.state, "token_payload", {}) or {}
    if not user.is_superadmin and PermissionCode.FOLDER_SCAN not in payload.get("perms", []):
        await websocket.close(code=4403)
        return

    await websocket.accept()
    await scan_manager.connect(scan_id, websocket)
    try:
        while True:
            # Clients don't send anything meaningful; this just keeps the
            # connection open until they disconnect.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await scan_manager.disconnect(scan_id, websocket)
