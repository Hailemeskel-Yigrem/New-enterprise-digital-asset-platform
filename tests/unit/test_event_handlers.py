"""Unit tests for default event handlers."""

from __future__ import annotations

import uuid

import pytest

from vaultforge.domain.events import EventTypes, quota_exceeded, webhook_failed
from vaultforge.infrastructure.events.event_bus import InMemoryEventBus
from vaultforge.infrastructure.events.handlers import register_default_handlers


@pytest.mark.asyncio
async def test_register_default_handlers() -> None:
    bus = InMemoryEventBus()
    await register_default_handlers(bus)
    await bus.publish(quota_exceeded(uuid.uuid4(), "seats", 10, 5))
    assert len(bus.published_events()) == 1


@pytest.mark.asyncio
async def test_webhook_failure_handler_does_not_raise() -> None:
    bus = InMemoryEventBus()
    await register_default_handlers(bus)
    event = webhook_failed(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "timeout")
    await bus.publish(event)
    assert event.event_type == EventTypes.WEBHOOK_FAILED
