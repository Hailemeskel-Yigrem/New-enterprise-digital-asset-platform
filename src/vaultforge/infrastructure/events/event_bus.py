"""In-process and Redis pub/sub event bus."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from vaultforge.domain.events import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None]]


@runtime_checkable
class EventBus(Protocol):
    async def publish(self, event: DomainEvent) -> None: ...
    async def subscribe(self, event_type: str, handler: EventHandler) -> None: ...
    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None: ...


class RedisPubSubClient(Protocol):
    """Minimal surface of a redis-py client used by the event bus."""

    def publish(self, channel: str, message: str) -> Any: ...
    def pubsub(self) -> Any: ...


class InMemoryEventBus:
    """Process-local event bus for synchronous handler dispatch."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[DomainEvent] = []
        self._lock = asyncio.Lock()

    async def publish(self, event: DomainEvent) -> None:
        async with self._lock:
            self._history.append(event)
        handlers = list(self._handlers.get(event.event_type, []))
        handlers.extend(self._handlers.get("*", []))
        for handler in handlers:
            await handler(event)

    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def published_events(self) -> list[DomainEvent]:
        return list(self._history)


class RedisEventBus:
    """Redis pub/sub backed event bus with in-process handler registry."""

    CHANNEL_PREFIX = "vaultforge:events:"

    def __init__(
        self, redis_client: RedisPubSubClient, *, local_bus: InMemoryEventBus | None = None
    ) -> None:
        self._redis = redis_client
        self._local = local_bus or InMemoryEventBus()
        self._subscriber_task: asyncio.Task[None] | None = None

    async def publish(self, event: DomainEvent) -> None:
        await self._local.publish(event)
        channel = f"{self.CHANNEL_PREFIX}{event.event_type}"
        payload = json.dumps(event.to_dict())
        publish = getattr(self._redis, "publish", None)
        if publish is not None:
            result = publish(channel, payload)
            if asyncio.iscoroutine(result):
                await result

    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        await self._local.subscribe(event_type, handler)

    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        await self._local.unsubscribe(event_type, handler)

    async def start_subscriber(self) -> None:
        if self._subscriber_task is not None:
            return

        async def _loop() -> None:
            pubsub = self._redis.pubsub()
            await pubsub.psubscribe(f"{self.CHANNEL_PREFIX}*")
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "pmessage":
                    data = json.loads(message["data"])
                    event = DomainEvent.from_dict(data)
                    await self._local.publish(event)
                await asyncio.sleep(0.01)

        self._subscriber_task = asyncio.create_task(_loop())

    async def stop_subscriber(self) -> None:
        if self._subscriber_task is not None:
            self._subscriber_task.cancel()
            self._subscriber_task = None


class CompositeEventBus:
    """Fan-out to multiple buses."""

    def __init__(self, *buses: EventBus) -> None:
        self._buses = buses

    async def publish(self, event: DomainEvent) -> None:
        for bus in self._buses:
            await bus.publish(event)

    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        for bus in self._buses:
            await bus.subscribe(event_type, handler)

    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        for bus in self._buses:
            await bus.unsubscribe(event_type, handler)
