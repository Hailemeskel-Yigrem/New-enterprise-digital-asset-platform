"""SQLAlchemy webhook repositories."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.domain.webhooks.entities import (
    WebhookDelivery,
    WebhookEndpoint,
    WebhookSubscription,
)
from vaultforge.domain.webhooks.enums import DeliveryStatus, WebhookStatus
from vaultforge.domain.webhooks.repositories import (
    DeliveryQuery,
    WebhookDeliveryRepository,
    WebhookEndpointRepository,
    WebhookSubscriptionRepository,
)
from vaultforge.infrastructure.persistence.models.webhook import (
    WebhookDeliveryModel,
    WebhookEndpointModel,
    WebhookSubscriptionModel,
)


class SqlAlchemyWebhookEndpointRepository(WebhookEndpointRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: WebhookEndpointModel) -> WebhookEndpoint:
        return WebhookEndpoint(
            id=model.id,
            organization_id=model.organization_id,
            name=model.name,
            url=model.url,
            secret=model.secret,
            status=WebhookStatus(model.status),
            created_by=model.created_by,
            description=model.description,
            timeout_seconds=model.timeout_seconds,
            max_retries=model.max_retries,
            consecutive_failures=model.consecutive_failures,
            last_success_at=model.last_success_at,
            last_failure_at=model.last_failure_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_by_id(
        self, organization_id: uuid.UUID, endpoint_id: uuid.UUID
    ) -> WebhookEndpoint | None:
        model = await self._session.get(WebhookEndpointModel, endpoint_id)
        if model is None or model.organization_id != organization_id:
            return None
        return self._to_entity(model)

    async def add(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        model = WebhookEndpointModel(
            id=endpoint.id,
            organization_id=endpoint.organization_id,
            name=endpoint.name,
            url=endpoint.url,
            secret=endpoint.secret,
            status=endpoint.status.value,
            created_by=endpoint.created_by,
            description=endpoint.description,
            timeout_seconds=endpoint.timeout_seconds,
            max_retries=endpoint.max_retries,
            consecutive_failures=endpoint.consecutive_failures,
            last_success_at=endpoint.last_success_at,
            last_failure_at=endpoint.last_failure_at,
            created_at=endpoint.created_at,
            updated_at=endpoint.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return endpoint

    async def update(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        model = await self._session.get(WebhookEndpointModel, endpoint.id)
        if model is None:
            raise ValueError("Endpoint not found")
        model.status = endpoint.status.value
        model.consecutive_failures = endpoint.consecutive_failures
        model.last_success_at = endpoint.last_success_at
        model.last_failure_at = endpoint.last_failure_at
        model.updated_at = endpoint.updated_at
        await self._session.flush()
        return endpoint

    async def delete(self, organization_id: uuid.UUID, endpoint_id: uuid.UUID) -> None:
        model = await self._session.get(WebhookEndpointModel, endpoint_id)
        if model is not None and model.organization_id == organization_id:
            await self._session.delete(model)

    async def list_for_organization(self, organization_id: uuid.UUID) -> Sequence[WebhookEndpoint]:
        stmt = select(WebhookEndpointModel).where(
            WebhookEndpointModel.organization_id == organization_id
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]


class SqlAlchemyWebhookSubscriptionRepository(WebhookSubscriptionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, subscription: WebhookSubscription) -> WebhookSubscription:
        model = WebhookSubscriptionModel(
            id=subscription.id,
            organization_id=subscription.organization_id,
            endpoint_id=subscription.endpoint_id,
            events_json=subscription.events,
            filter_expression=subscription.filter_expression,
            is_active=subscription.is_active,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return subscription

    async def update(self, subscription: WebhookSubscription) -> WebhookSubscription:
        model = await self._session.get(WebhookSubscriptionModel, subscription.id)
        if model is None:
            raise ValueError("Subscription not found")
        model.events_json = subscription.events
        model.filter_expression = subscription.filter_expression
        model.is_active = subscription.is_active
        model.updated_at = subscription.updated_at
        await self._session.flush()
        return subscription

    async def list_for_endpoint(
        self, organization_id: uuid.UUID, endpoint_id: uuid.UUID
    ) -> Sequence[WebhookSubscription]:
        stmt = select(WebhookSubscriptionModel).where(
            WebhookSubscriptionModel.organization_id == organization_id,
            WebhookSubscriptionModel.endpoint_id == endpoint_id,
        )
        result = await self._session.execute(stmt)
        return [
            WebhookSubscription(
                id=m.id,
                organization_id=m.organization_id,
                endpoint_id=m.endpoint_id,
                events=list(m.events_json),
                filter_expression=m.filter_expression,
                is_active=m.is_active,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in result.scalars()
        ]

    async def list_matching_event(
        self, organization_id: uuid.UUID, event_type: str
    ) -> Sequence[WebhookSubscription]:
        stmt = select(WebhookSubscriptionModel).where(
            WebhookSubscriptionModel.organization_id == organization_id,
            WebhookSubscriptionModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        subs: list[WebhookSubscription] = []
        for m in result.scalars():
            events = list(m.events_json)
            if event_type in events:
                subs.append(
                    WebhookSubscription(
                        id=m.id,
                        organization_id=m.organization_id,
                        endpoint_id=m.endpoint_id,
                        events=events,
                        filter_expression=m.filter_expression,
                        is_active=m.is_active,
                        created_at=m.created_at,
                        updated_at=m.updated_at,
                    )
                )
        return subs


class SqlAlchemyWebhookDeliveryRepository(WebhookDeliveryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: WebhookDeliveryModel) -> WebhookDelivery:
        return WebhookDelivery(
            id=model.id,
            organization_id=model.organization_id,
            endpoint_id=model.endpoint_id,
            event_type=model.event_type,
            payload=dict(model.payload_json),
            status=DeliveryStatus(model.status),
            attempt_count=model.attempt_count,
            max_attempts=model.max_attempts,
            response_status=model.response_status,
            response_body=model.response_body,
            error_message=model.error_message,
            next_retry_at=model.next_retry_at,
            delivered_at=model.delivered_at,
            duration_ms=model.duration_ms,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def add(self, delivery: WebhookDelivery) -> WebhookDelivery:
        model = WebhookDeliveryModel(
            id=delivery.id,
            organization_id=delivery.organization_id,
            endpoint_id=delivery.endpoint_id,
            event_type=delivery.event_type,
            payload_json=delivery.payload,
            status=delivery.status.value,
            attempt_count=delivery.attempt_count,
            max_attempts=delivery.max_attempts,
            response_status=delivery.response_status,
            response_body=delivery.response_body,
            error_message=delivery.error_message,
            next_retry_at=delivery.next_retry_at,
            delivered_at=delivery.delivered_at,
            duration_ms=delivery.duration_ms,
            created_at=delivery.created_at,
            updated_at=delivery.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return delivery

    async def update(self, delivery: WebhookDelivery) -> WebhookDelivery:
        model = await self._session.get(WebhookDeliveryModel, delivery.id)
        if model is None:
            raise ValueError("Delivery not found")
        model.status = delivery.status.value
        model.attempt_count = delivery.attempt_count
        model.response_status = delivery.response_status
        model.response_body = delivery.response_body
        model.error_message = delivery.error_message
        model.next_retry_at = delivery.next_retry_at
        model.delivered_at = delivery.delivered_at
        model.duration_ms = delivery.duration_ms
        model.updated_at = delivery.updated_at
        await self._session.flush()
        return delivery

    async def get_by_id(
        self, organization_id: uuid.UUID, delivery_id: uuid.UUID
    ) -> WebhookDelivery | None:
        model = await self._session.get(WebhookDeliveryModel, delivery_id)
        if model is None or model.organization_id != organization_id:
            return None
        return self._to_entity(model)

    async def list(self, query: DeliveryQuery) -> Sequence[WebhookDelivery]:
        stmt = select(WebhookDeliveryModel).where(
            WebhookDeliveryModel.organization_id == query.organization_id
        )
        if query.endpoint_id is not None:
            stmt = stmt.where(WebhookDeliveryModel.endpoint_id == query.endpoint_id)
        if query.status is not None:
            stmt = stmt.where(WebhookDeliveryModel.status == query.status.value)
        stmt = stmt.limit(query.limit).offset(query.offset)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def list_pending_retries(self, *, limit: int = 100) -> Sequence[WebhookDelivery]:
        stmt = (
            select(WebhookDeliveryModel)
            .where(WebhookDeliveryModel.status.in_(["pending", "retrying"]))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]
