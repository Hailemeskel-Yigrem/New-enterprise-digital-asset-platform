"""Unit tests for WebSocket connection manager."""

from __future__ import annotations

import uuid

import pytest
from starlette.websockets import WebSocketDisconnect

from vaultforge.api.ws.manager import ConnectionManager


class FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.messages: list[dict] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message: dict) -> None:
        self.messages.append(message)


@pytest.mark.asyncio
async def test_connect_and_broadcast() -> None:
    manager = ConnectionManager()
    organization_id = uuid.uuid4()
    socket = FakeWebSocket()

    await manager.connect(organization_id, socket)
    assert socket.accepted
    assert manager.connection_count(organization_id) == 1

    delivered = await manager.broadcast(organization_id, {"event": "document.updated"})
    assert delivered == 1
    assert socket.messages[0]["event"] == "document.updated"


@pytest.mark.asyncio
async def test_disconnect_removes_connection() -> None:
    manager = ConnectionManager()
    organization_id = uuid.uuid4()
    socket = FakeWebSocket()

    await manager.connect(organization_id, socket)
    manager.disconnect(organization_id, socket)
    assert manager.connection_count(organization_id) == 0


@pytest.mark.asyncio
async def test_broadcast_skips_failed_connections() -> None:
    manager = ConnectionManager()
    organization_id = uuid.uuid4()
    healthy = FakeWebSocket()

    class FailingWebSocket(FakeWebSocket):
        async def send_json(self, message: dict) -> None:
            raise WebSocketDisconnect()

    failing = FailingWebSocket()
    await manager.connect(organization_id, healthy)
    await manager.connect(organization_id, failing)

    delivered = await manager.broadcast(organization_id, {"event": "ping"})
    assert delivered == 1
    assert manager.connection_count(organization_id) == 1
