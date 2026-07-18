"""Default domain event handlers."""

from __future__ import annotations

import structlog

from vaultforge.domain.events import DomainEvent, EventTypes
from vaultforge.infrastructure.events.event_bus import EventBus, InMemoryEventBus

logger = structlog.get_logger(__name__)


async def log_event_handler(event: DomainEvent) -> None:
    logger.info(
        "domain_event",
        event_type=event.event_type,
        organization_id=str(event.organization_id),
        event_id=str(event.event_id),
    )


async def quota_alert_handler(event: DomainEvent) -> None:
    if event.event_type != EventTypes.QUOTA_EXCEEDED:
        return
    logger.warning(
        "quota_exceeded",
        organization_id=str(event.organization_id),
        metric=event.payload.get("metric"),
        consumed=event.payload.get("consumed"),
        limit=event.payload.get("limit"),
    )


async def webhook_failure_handler(event: DomainEvent) -> None:
    if event.event_type != EventTypes.WEBHOOK_FAILED:
        return
    logger.error(
        "webhook_delivery_failed",
        endpoint_id=event.payload.get("endpoint_id"),
        delivery_id=event.payload.get("delivery_id"),
        error=event.payload.get("error"),
    )


async def metadata_audit_handler(event: DomainEvent) -> None:
    if event.event_type != EventTypes.METADATA_UPDATED:
        return
    logger.info(
        "metadata_updated",
        resource_id=event.payload.get("resource_id"),
        schema_id=event.payload.get("schema_id"),
        actor_id=str(event.actor_id) if event.actor_id else None,
    )


async def register_default_handlers(bus: EventBus) -> None:
    await bus.subscribe("*", log_event_handler)
    await bus.subscribe(EventTypes.QUOTA_EXCEEDED, quota_alert_handler)
    await bus.subscribe(EventTypes.WEBHOOK_FAILED, webhook_failure_handler)
    await bus.subscribe(EventTypes.METADATA_UPDATED, metadata_audit_handler)


def create_default_event_bus() -> InMemoryEventBus:
    return InMemoryEventBus()
