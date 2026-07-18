"""Unit tests for event bus."""

from __future__ import annotations

import uuid

import pytest

from vaultforge.domain.events import document_created
from vaultforge.infrastructure.events.event_bus import InMemoryEventBus


@pytest.mark.asyncio
async def test_in_memory_publish_subscribe() -> None:
    bus = InMemoryEventBus()
    received: list[str] = []

    async def handler(event) -> None:
        received.append(event.event_type)

    await bus.subscribe("document.created", handler)
    await bus.publish(document_created(uuid.uuid4(), uuid.uuid4()))
    assert received == ["document.created"]


@pytest.mark.asyncio
async def test_wildcard_handler() -> None:
    bus = InMemoryEventBus()
    count = 0

    async def handler(event) -> None:
        nonlocal count
        count += 1

    await bus.subscribe("*", handler)
    await bus.publish(document_created(uuid.uuid4(), uuid.uuid4()))
    assert count == 1


@pytest.mark.asyncio
async def test_unsubscribe() -> None:
    bus = InMemoryEventBus()

    async def handler(event) -> None:
        pass

    await bus.subscribe("document.created", handler)
    await bus.unsubscribe("document.created", handler)
    await bus.publish(document_created(uuid.uuid4(), uuid.uuid4()))
    assert bus.published_events()
