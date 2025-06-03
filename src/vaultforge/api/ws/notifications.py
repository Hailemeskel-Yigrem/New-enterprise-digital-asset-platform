"""Live notification WebSocket endpoint."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from vaultforge.api.ws.manager import manager

router = APIRouter(prefix="/ws", tags=["websockets"])


@router.websocket("/organizations/{organization_id}/notifications")
async def organization_notifications(
    websocket: WebSocket,
    organization_id: uuid.UUID,
) -> None:
    await manager.connect(organization_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(organization_id, websocket)
