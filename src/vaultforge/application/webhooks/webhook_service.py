"""Outbound webhook delivery with HMAC signing."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

import httpx

from vaultforge.application.webhooks.schemas import (
    WebhookDeliveryResponse,
    WebhookEndpointCreateRequest,
    WebhookEndpointResponse,
)
from vaultforge.core.exceptions import NotFoundError
from vaultforge.domain.events import DomainEvent
from vaultforge.domain.webhooks.entities import (
    WebhookDelivery,
    WebhookEndpoint,
    WebhookSubscription,
)
from vaultforge.domain.webhooks.repositories import (
    WebhookDeliveryRepository,
    WebhookEndpointRepository,
    WebhookSubscriptionRepository,
)


@dataclass(slots=True)
class WebhookService:
    endpoints: WebhookEndpointRepository
    subscriptions: WebhookSubscriptionRepository
    deliveries: WebhookDeliveryRepository
    http_client: httpx.AsyncClient | None = None

    async def create_endpoint(
        self,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: WebhookEndpointCreateRequest,
    ) -> WebhookEndpointResponse:
        endpoint = WebhookEndpoint(
            organization_id=organization_id,
            name=payload.name,
            url=payload.url,
            description=payload.description,
            created_by=actor_id,
        )
        saved = await self.endpoints.add(endpoint)
        if payload.events:
            subscription = WebhookSubscription(
                organization_id=organization_id,
                endpoint_id=saved.id,
                events=payload.events,
            )
            await self.subscriptions.add(subscription)
        return WebhookEndpointResponse.model_validate(saved)

    async def list_endpoints(self, organization_id: uuid.UUID) -> list[WebhookEndpointResponse]:
        endpoints = await self.endpoints.list_for_organization(organization_id)
        return [WebhookEndpointResponse.model_validate(e) for e in endpoints]

    async def dispatch_event(self, event: DomainEvent) -> list[WebhookDeliveryResponse]:
        subscriptions = await self.subscriptions.list_matching_event(
            event.organization_id, event.event_type
        )
        results: list[WebhookDeliveryResponse] = []
        for subscription in subscriptions:
            if not subscription.matches_event(event.event_type, event.payload):
                continue
            endpoint = await self.endpoints.get_by_id(
                event.organization_id, subscription.endpoint_id
            )
            if endpoint is None or not endpoint.is_deliverable():
                continue
            delivery = WebhookDelivery(
                organization_id=event.organization_id,
                endpoint_id=endpoint.id,
                event_type=event.event_type,
                payload=event.payload,
            )
            saved = await self.deliveries.add(delivery)
            delivered = await self._deliver(endpoint, saved)
            updated = await self.deliveries.update(delivered)
            results.append(WebhookDeliveryResponse.model_validate(updated))
        return results

    async def _deliver(
        self, endpoint: WebhookEndpoint, delivery: WebhookDelivery
    ) -> WebhookDelivery:
        body = delivery.build_request_body()
        timestamp = int(time.time())
        signature = endpoint.sign_payload(body, timestamp)
        headers = {
            "Content-Type": "application/json",
            "X-VaultForge-Signature": signature,
            "X-VaultForge-Timestamp": str(timestamp),
            "X-VaultForge-Delivery-Id": str(delivery.id),
        }
        client = self.http_client or httpx.AsyncClient(timeout=endpoint.timeout_seconds)
        close_client = self.http_client is None
        try:
            started = time.perf_counter()
            response = await client.post(endpoint.url, content=body, headers=headers)
            duration_ms = int((time.perf_counter() - started) * 1000)
            if 200 <= response.status_code < 300:
                delivery.mark_success(response.status_code, response.text, duration_ms)
                endpoint.record_success()
            else:
                delivery.mark_failure(
                    f"HTTP {response.status_code}", status_code=response.status_code
                )
                endpoint.record_failure()
            await self.endpoints.update(endpoint)
            return delivery
        except httpx.HTTPError as exc:
            delivery.mark_failure(str(exc))
            endpoint.record_failure()
            await self.endpoints.update(endpoint)
            return delivery
        finally:
            if close_client:
                await client.aclose()

    async def get_delivery(
        self, organization_id: uuid.UUID, delivery_id: uuid.UUID
    ) -> WebhookDeliveryResponse:
        delivery = await self.deliveries.get_by_id(organization_id, delivery_id)
        if delivery is None:
            raise NotFoundError("Webhook delivery not found")
        return WebhookDeliveryResponse.model_validate(delivery)
