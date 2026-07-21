"""Webhook repository interfaces."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from vaultforge.domain.webhooks.entities import (
    WebhookDelivery,
    WebhookEndpoint,
    WebhookSubscription,
)
from vaultforge.domain.webhooks.enums import DeliveryStatus


@dataclass(frozen=True, slots=True)
class DeliveryQuery:
    organization_id: uuid.UUID
    endpoint_id: uuid.UUID | None = None
    status: DeliveryStatus | None = None
    limit: int = 50
    offset: int = 0


class WebhookEndpointRepository(ABC):
    @abstractmethod
    async def get_by_id(
        self, organization_id: uuid.UUID, endpoint_id: uuid.UUID
    ) -> WebhookEndpoint | None: ...

    @abstractmethod
    async def add(self, endpoint: WebhookEndpoint) -> WebhookEndpoint: ...

    @abstractmethod
    async def update(self, endpoint: WebhookEndpoint) -> WebhookEndpoint: ...

    @abstractmethod
    async def delete(self, organization_id: uuid.UUID, endpoint_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def list_for_organization(
        self, organization_id: uuid.UUID
    ) -> Sequence[WebhookEndpoint]: ...


class WebhookSubscriptionRepository(ABC):
    @abstractmethod
    async def add(self, subscription: WebhookSubscription) -> WebhookSubscription: ...

    @abstractmethod
    async def update(self, subscription: WebhookSubscription) -> WebhookSubscription: ...

    @abstractmethod
    async def list_for_endpoint(
        self, organization_id: uuid.UUID, endpoint_id: uuid.UUID
    ) -> Sequence[WebhookSubscription]: ...

    @abstractmethod
    async def list_matching_event(
        self, organization_id: uuid.UUID, event_type: str
    ) -> Sequence[WebhookSubscription]: ...


class WebhookDeliveryRepository(ABC):
    @abstractmethod
    async def add(self, delivery: WebhookDelivery) -> WebhookDelivery: ...

    @abstractmethod
    async def update(self, delivery: WebhookDelivery) -> WebhookDelivery: ...

    @abstractmethod
    async def get_by_id(
        self, organization_id: uuid.UUID, delivery_id: uuid.UUID
    ) -> WebhookDelivery | None: ...

    @abstractmethod
    async def list(self, query: DeliveryQuery) -> Sequence[WebhookDelivery]: ...

    @abstractmethod
    async def list_pending_retries(self, *, limit: int = 100) -> Sequence[WebhookDelivery]: ...
