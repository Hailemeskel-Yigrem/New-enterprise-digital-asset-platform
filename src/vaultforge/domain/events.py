"""Domain event types and envelopes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from vaultforge.domain.common import utc_now


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_type: str
    organization_id: uuid.UUID
    payload: dict[str, Any]
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=utc_now)
    actor_id: uuid.UUID | None = None
    correlation_id: str | None = None
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "organization_id": str(self.organization_id),
            "payload": self.payload,
            "occurred_at": self.occurred_at.isoformat(),
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "correlation_id": self.correlation_id,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DomainEvent:
        return cls(
            event_id=uuid.UUID(data["event_id"]),
            event_type=data["event_type"],
            organization_id=uuid.UUID(data["organization_id"]),
            payload=data.get("payload", {}),
            occurred_at=datetime.fromisoformat(data["occurred_at"]),
            actor_id=uuid.UUID(data["actor_id"]) if data.get("actor_id") else None,
            correlation_id=data.get("correlation_id"),
            version=int(data.get("version", 1)),
        )


class EventTypes:
    DOCUMENT_CREATED = "document.created"
    DOCUMENT_UPDATED = "document.updated"
    DOCUMENT_DELETED = "document.deleted"
    DOCUMENT_MOVED = "document.moved"
    FOLDER_CREATED = "folder.created"
    FOLDER_DELETED = "folder.deleted"
    METADATA_UPDATED = "metadata.updated"
    CLASSIFICATION_CHANGED = "classification.changed"
    HOLD_PLACED = "compliance.hold.placed"
    HOLD_RELEASED = "compliance.hold.released"
    EXPORT_COMPLETED = "compliance.export.completed"
    QUOTA_EXCEEDED = "billing.quota.exceeded"
    WEBHOOK_DELIVERED = "webhook.delivered"
    WEBHOOK_FAILED = "webhook.failed"
    USER_INVITED = "user.invited"
    SHARE_CREATED = "share.created"


def document_created(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None = None,
    folder_id: uuid.UUID | None = None,
    name: str = "",
) -> DomainEvent:
    return DomainEvent(
        event_type=EventTypes.DOCUMENT_CREATED,
        organization_id=organization_id,
        actor_id=actor_id,
        payload={
            "document_id": str(document_id),
            "folder_id": str(folder_id) if folder_id else None,
            "name": name,
        },
    )


def metadata_updated(
    organization_id: uuid.UUID,
    resource_id: uuid.UUID,
    schema_id: uuid.UUID,
    *,
    actor_id: uuid.UUID | None = None,
) -> DomainEvent:
    return DomainEvent(
        event_type=EventTypes.METADATA_UPDATED,
        organization_id=organization_id,
        actor_id=actor_id,
        payload={
            "resource_id": str(resource_id),
            "schema_id": str(schema_id),
        },
    )


def quota_exceeded(
    organization_id: uuid.UUID,
    metric: str,
    consumed: int,
    limit: int,
) -> DomainEvent:
    return DomainEvent(
        event_type=EventTypes.QUOTA_EXCEEDED,
        organization_id=organization_id,
        payload={"metric": metric, "consumed": consumed, "limit": limit},
    )


def webhook_failed(
    organization_id: uuid.UUID,
    endpoint_id: uuid.UUID,
    delivery_id: uuid.UUID,
    error: str,
) -> DomainEvent:
    return DomainEvent(
        event_type=EventTypes.WEBHOOK_FAILED,
        organization_id=organization_id,
        payload={
            "endpoint_id": str(endpoint_id),
            "delivery_id": str(delivery_id),
            "error": error[:500],
        },
    )
