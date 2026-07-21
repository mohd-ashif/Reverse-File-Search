from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.ws_manager import scan_manager

router = APIRouter()


@router.websocket("/scan/{scan_id}")
async def scan_progress_ws(websocket: WebSocket, scan_id: str) -> None:
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
