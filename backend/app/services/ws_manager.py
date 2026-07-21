import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ScanConnectionManager:
    """Tracks websocket clients subscribed to a given scan_id's progress feed."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, scan_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(scan_id, []).append(websocket)

    async def disconnect(self, scan_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(scan_id)
            if connections and websocket in connections:
                connections.remove(websocket)
            if connections is not None and not connections:
                self._connections.pop(scan_id, None)

    async def broadcast(self, scan_id: str, message: dict) -> None:
        async with self._lock:
            connections = list(self._connections.get(scan_id, []))
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as exc:  # noqa: BLE001 - one dead socket must not break the rest
                logger.debug("Dropping scan websocket for %s: %s", scan_id, exc)


scan_manager = ScanConnectionManager()
