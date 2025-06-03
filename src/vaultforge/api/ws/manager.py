"""WebSocket connection manager for organization channels."""

from __future__ import annotations

import uuid
from collections import defaultdict

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect


class ConnectionManager:
    """Track active WebSocket connections grouped by organization."""

    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, organization_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[organization_id].add(websocket)

    def disconnect(self, organization_id: uuid.UUID, websocket: WebSocket) -> None:
        connections = self._connections.get(organization_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(organization_id, None)

    async def broadcast(self, organization_id: uuid.UUID, message: dict) -> int:
        connections = list(self._connections.get(organization_id, set()))
        delivered = 0
        for websocket in connections:
            try:
                await websocket.send_json(message)
                delivered += 1
            except (WebSocketDisconnect, RuntimeError):
                self.disconnect(organization_id, websocket)
        return delivered

    def connection_count(self, organization_id: uuid.UUID | None = None) -> int:
        if organization_id is not None:
            return len(self._connections.get(organization_id, set()))
        return sum(len(items) for items in self._connections.values())


manager = ConnectionManager()
