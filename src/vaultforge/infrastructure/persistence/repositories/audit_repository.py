"""SQLAlchemy audit and activity repositories."""

from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.domain.audit.entities import ActivityItem, AuditEvent
from vaultforge.domain.audit.repositories import (
    ActivityItemRepository,
    ActivityQueryCriteria,
    AuditEventRepository,
    AuditQueryCriteria,
)
from vaultforge.infrastructure.persistence.models.audit import ActivityItemModel, AuditEventModel


def _audit_to_entity(model: AuditEventModel) -> AuditEvent:
    return AuditEvent(
        id=model.id,
        organization_id=model.organization_id,
        actor_id=model.actor_id,
        action=model.action,
        resource_type=model.resource_type,
        resource_id=model.resource_id,
        metadata=dict(model.metadata_json or {}),
        ip_address=model.ip_address,
        user_agent=model.user_agent,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _activity_to_entity(model: ActivityItemModel) -> ActivityItem:
    return ActivityItem(
        id=model.id,
        organization_id=model.organization_id,
        user_id=model.user_id,
        activity_type=model.activity_type,
        summary=model.summary,
        resource_type=model.resource_type,
        resource_id=model.resource_id,
        audit_event_id=model.audit_event_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_audit_filters(
    stmt: Select[tuple[AuditEventModel]], criteria: AuditQueryCriteria
) -> Select[tuple[AuditEventModel]]:
    stmt = stmt.where(AuditEventModel.organization_id == criteria.organization_id)
    if criteria.resource_type is not None:
        stmt = stmt.where(AuditEventModel.resource_type == criteria.resource_type)
    if criteria.resource_id is not None:
        stmt = stmt.where(AuditEventModel.resource_id == criteria.resource_id)
    if criteria.actor_id is not None:
        stmt = stmt.where(AuditEventModel.actor_id == criteria.actor_id)
    if criteria.action is not None:
        stmt = stmt.where(AuditEventModel.action == criteria.action)
    if criteria.since is not None:
        stmt = stmt.where(AuditEventModel.created_at >= criteria.since)
    if criteria.until is not None:
        stmt = stmt.where(AuditEventModel.created_at <= criteria.until)
    return (
        stmt.order_by(AuditEventModel.created_at.desc())
        .limit(criteria.limit)
        .offset(criteria.offset)
    )


def _apply_activity_filters(
    stmt: Select[tuple[ActivityItemModel]], criteria: ActivityQueryCriteria
) -> Select[tuple[ActivityItemModel]]:
    stmt = stmt.where(ActivityItemModel.organization_id == criteria.organization_id)
    if criteria.user_id is not None:
        stmt = stmt.where(ActivityItemModel.user_id == criteria.user_id)
    if criteria.resource_type is not None:
        stmt = stmt.where(ActivityItemModel.resource_type == criteria.resource_type)
    if criteria.resource_id is not None:
        stmt = stmt.where(ActivityItemModel.resource_id == criteria.resource_id)
    if criteria.since is not None:
        stmt = stmt.where(ActivityItemModel.created_at >= criteria.since)
    if criteria.until is not None:
        stmt = stmt.where(ActivityItemModel.created_at <= criteria.until)
    return (
        stmt.order_by(ActivityItemModel.created_at.desc())
        .limit(criteria.limit)
        .offset(criteria.offset)
    )


class SqlAlchemyAuditEventRepository(AuditEventRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: AuditEvent) -> AuditEvent:
        model = AuditEventModel(
            id=event.id,
            organization_id=event.organization_id,
            actor_id=event.actor_id,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            metadata_json=dict(event.metadata),
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _audit_to_entity(model)

    async def query(self, criteria: AuditQueryCriteria) -> list[AuditEvent]:
        stmt = _apply_audit_filters(select(AuditEventModel), criteria)
        result = await self._session.execute(stmt)
        return [_audit_to_entity(model) for model in result.scalars().all()]


class SqlAlchemyActivityItemRepository(ActivityItemRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, item: ActivityItem) -> ActivityItem:
        model = ActivityItemModel(
            id=item.id,
            organization_id=item.organization_id,
            user_id=item.user_id,
            activity_type=item.activity_type,
            summary=item.summary,
            resource_type=item.resource_type,
            resource_id=item.resource_id,
            audit_event_id=item.audit_event_id,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _activity_to_entity(model)

    async def query(self, criteria: ActivityQueryCriteria) -> list[ActivityItem]:
        stmt = _apply_activity_filters(select(ActivityItemModel), criteria)
        result = await self._session.execute(stmt)
        return [_activity_to_entity(model) for model in result.scalars().all()]
