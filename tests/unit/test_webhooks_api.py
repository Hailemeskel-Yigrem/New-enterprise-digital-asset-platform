"""API tests for webhook routes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from vaultforge.application.webhooks.schemas import WebhookEndpointResponse
from vaultforge.application.webhooks.webhook_service import WebhookService
from vaultforge.domain.webhooks.enums import WebhookStatus


def _endpoint_response(org_id: uuid.UUID) -> WebhookEndpointResponse:
    now = datetime.now(UTC)
    return WebhookEndpointResponse(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Order Sync",
        url="https://example.com/hooks",
        status=WebhookStatus.ACTIVE,
        secret="whsec_test",
        description="",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def webhooks_client(client):
    from vaultforge.api.v1 import webhooks as webhooks_module

    mock_service = AsyncMock(spec=WebhookService)
    client.app.dependency_overrides[webhooks_module.get_webhook_service] = lambda: mock_service
    yield client, mock_service
    client.app.dependency_overrides.clear()


def test_list_webhook_endpoints(webhooks_client) -> None:
    client, mock_service = webhooks_client
    org_id = uuid.uuid4()
    mock_service.list_endpoints = AsyncMock(return_value=[_endpoint_response(org_id)])

    response = client.get(f"/api/v1/organizations/{org_id}/webhooks/endpoints")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Order Sync"


def test_create_webhook_endpoint_validation(webhooks_client) -> None:
    client, mock_service = webhooks_client
    org_id = uuid.uuid4()
    mock_service.create_endpoint = AsyncMock(return_value=_endpoint_response(org_id))

    response = client.post(
        f"/api/v1/organizations/{org_id}/webhooks/endpoints",
        json={"name": "Hook", "url": "not-valid"},
        headers={"X-User-Id": str(uuid.uuid4())},
    )

    assert response.status_code == 201
    mock_service.create_endpoint.assert_awaited()
