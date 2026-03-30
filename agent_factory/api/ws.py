from __future__ import annotations

from fastapi import WebSocket


class WSManager:
    def __init__(self):
        self._clients: dict[str, list[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.setdefault(session_id, []).append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        clients = self._clients.get(session_id, [])
        if websocket in clients:
            clients.remove(websocket)

    async def publish(self, session_id: str, event: dict) -> None:
        for ws in list(self._clients.get(session_id, [])):
            await ws.send_json(event)


ws_manager = WSManager()
