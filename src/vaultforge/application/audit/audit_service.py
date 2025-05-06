"""Audit and activity application service."""

from __future__ import annotations

import uuid
from typing import Any

from vaultforge.application.audit.schemas import (
    ActivityFeedQuery,
    ActivityFeedResponse,
    ActivityItemResponse,
    AuditEventCreateRequest,
    AuditEventResponse,
    AuditTimelineQuery,
    AuditTimelineResponse,
)
from vaultforge.domain.audit.entities import ActivityItem, AuditEvent
from vaultforge.domain.audit.repositories import (
    ActivityItemRepository,
    ActivityQueryCriteria,
    AuditEventRepository,
    AuditQueryCriteria,
)


class AuditService:
    def __init__(
        self,
        audit_repo: AuditEventRepository,
        activity_repo: ActivityItemRepository,
    ) -> None:
        self._audit = audit_repo
        self._activity = activity_repo

    async def record_event(
        self,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: AuditEventCreateRequest,
        *,
        activity_summary: str | None = None,
    ) -> AuditEventResponse:
        event = AuditEvent(
            organization_id=organization_id,
            actor_id=actor_id,
            action=payload.action.strip(),
            resource_type=payload.resource_type.strip(),
            resource_id=payload.resource_id,
            metadata=dict(payload.metadata),
            ip_address=payload.ip_address,
            user_agent=payload.user_agent,
        )
        saved_event = await self._audit.add(event)

        if activity_summary:
            activity = ActivityItem(
                organization_id=organization_id,
                user_id=actor_id,
                activity_type=payload.action.strip(),
                summary=activity_summary.strip(),
                resource_type=payload.resource_type.strip(),
                resource_id=payload.resource_id,
                audit_event_id=saved_event.id,
            )
            await self._activity.add(activity)

        return AuditEventResponse.model_validate(saved_event)

    async def record(
        self,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        *,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID,
        metadata: dict[str, Any] | None = None,
        activity_summary: str | None = None,
    ) -> AuditEventResponse:
        payload = AuditEventCreateRequest(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata or {},
        )
        return await self.record_event(
            organization_id,
            actor_id,
            payload,
            activity_summary=activity_summary,
        )

    async def query_timeline(
        self,
        organization_id: uuid.UUID,
        query: AuditTimelineQuery,
    ) -> AuditTimelineResponse:
        criteria = AuditQueryCriteria(
            organization_id=organization_id,
            resource_type=query.resource_type,
            resource_id=query.resource_id,
            actor_id=query.actor_id,
            action=query.action,
            since=query.since,
            until=query.until,
            limit=query.limit,
            offset=query.offset,
        )
        events = list(await self._audit.query(criteria))
        return AuditTimelineResponse(
            events=[AuditEventResponse.model_validate(event) for event in events],
            total=len(events),
        )

    async def query_activity_feed(
        self,
        organization_id: uuid.UUID,
        query: ActivityFeedQuery,
    ) -> ActivityFeedResponse:
        criteria = ActivityQueryCriteria(
            organization_id=organization_id,
            user_id=query.user_id,
            resource_type=query.resource_type,
            resource_id=query.resource_id,
            since=query.since,
            until=query.until,
            limit=query.limit,
            offset=query.offset,
        )
        items = list(await self._activity.query(criteria))
        return ActivityFeedResponse(
            items=[ActivityItemResponse.model_validate(item) for item in items],
            total=len(items),
        )
