"""Unit tests for audit service."""

from __future__ import annotations

import uuid
from typing import Sequence

import pytest

from vaultforge.application.audit.audit_service import AuditService
from vaultforge.application.audit.schemas import AuditEventCreateRequest, AuditTimelineQuery
from vaultforge.domain.audit.entities import ActivityItem, AuditEvent
from vaultforge.domain.audit.repositories import (
    ActivityItemRepository,
    ActivityQueryCriteria,
    AuditEventRepository,
    AuditQueryCriteria,
)


class InMemoryAuditRepository(AuditEventRepository):
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def add(self, event: AuditEvent) -> AuditEvent:
        self.events.append(event)
        return event

    async def query(self, criteria: AuditQueryCriteria) -> Sequence[AuditEvent]:
        filtered = [
            event
            for event in self.events
            if event.organization_id == criteria.organization_id
            and (criteria.resource_type is None or event.resource_type == criteria.resource_type)
            and (criteria.resource_id is None or event.resource_id == criteria.resource_id)
        ]
        return filtered[criteria.offset : criteria.offset + criteria.limit]


class InMemoryActivityRepository(ActivityItemRepository):
    def __init__(self) -> None:
        self.items: list[ActivityItem] = []

    async def add(self, item: ActivityItem) -> ActivityItem:
        self.items.append(item)
        return item

    async def query(self, criteria: ActivityQueryCriteria) -> Sequence[ActivityItem]:
        filtered = [
            item
            for item in self.items
            if item.organization_id == criteria.organization_id
        ]
        return filtered[criteria.offset : criteria.offset + criteria.limit]


@pytest.fixture
def audit_service() -> AuditService:
    return AuditService(InMemoryAuditRepository(), InMemoryActivityRepository())


@pytest.mark.asyncio
async def test_record_event_persists_audit(audit_service: AuditService) -> None:
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    resource_id = uuid.uuid4()

    response = await audit_service.record_event(
        org_id,
        actor_id,
        AuditEventCreateRequest(
            action="document.uploaded",
            resource_type="document",
            resource_id=resource_id,
            metadata={"filename": "policy.pdf"},
        ),
    )

    assert response.action == "document.uploaded"
    assert response.resource_id == resource_id
    assert response.metadata["filename"] == "policy.pdf"


@pytest.mark.asyncio
async def test_record_with_activity_summary_creates_activity_item(
    audit_service: AuditService,
) -> None:
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    resource_id = uuid.uuid4()
    activity_repo = audit_service._activity  # noqa: SLF001
    assert isinstance(activity_repo, InMemoryActivityRepository)

    await audit_service.record(
        org_id,
        actor_id,
        action="document.shared",
        resource_type="document",
        resource_id=resource_id,
        activity_summary="Shared policy.pdf with legal team",
    )

    assert len(activity_repo.items) == 1
    assert activity_repo.items[0].summary == "Shared policy.pdf with legal team"


@pytest.mark.asyncio
async def test_query_timeline_filters_by_resource(audit_service: AuditService) -> None:
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    target_resource = uuid.uuid4()
    other_resource = uuid.uuid4()

    await audit_service.record(
        org_id,
        actor_id,
        action="document.viewed",
        resource_type="document",
        resource_id=target_resource,
    )
    await audit_service.record(
        org_id,
        actor_id,
        action="document.viewed",
        resource_type="document",
        resource_id=other_resource,
    )

    timeline = await audit_service.query_timeline(
        org_id,
        AuditTimelineQuery(resource_type="document", resource_id=target_resource),
    )
    assert timeline.total == 1
    assert timeline.events[0].resource_id == target_resource
