"""Audit and activity aggregates."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from vaultforge.core.exceptions import ValidationError
from vaultforge.domain.common import Entity


def _require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{field_name} cannot be empty")
    return cleaned


@dataclass(slots=True)
class AuditEvent(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    actor_id: uuid.UUID = field(default_factory=uuid.uuid4)
    action: str = ""
    resource_type: str = ""
    resource_id: uuid.UUID = field(default_factory=uuid.uuid4)
    metadata: dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None

    def __post_init__(self) -> None:
        self.action = _require_non_empty(self.action, "Action")
        self.resource_type = _require_non_empty(self.resource_type, "Resource type")


@dataclass(slots=True)
class ActivityItem(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
    activity_type: str = ""
    summary: str = ""
    resource_type: str = ""
    resource_id: uuid.UUID = field(default_factory=uuid.uuid4)
    audit_event_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        self.activity_type = _require_non_empty(self.activity_type, "Activity type")
        self.summary = _require_non_empty(self.summary, "Summary")
        self.resource_type = _require_non_empty(self.resource_type, "Resource type")
