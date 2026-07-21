"""Unit tests for webhook delivery service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from vaultforge.application.webhooks.schemas import WebhookEndpointCreateRequest
from vaultforge.application.webhooks.webhook_service import WebhookService
from vaultforge.domain.events import document_created


@pytest.fixture
def endpoint_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.add = AsyncMock(side_effect=lambda e: e)
    repo.update = AsyncMock(side_effect=lambda e: e)
    repo.list_for_organization = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def subscription_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.add = AsyncMock(side_effect=lambda s: s)
    repo.list_matching_event = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def delivery_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.add = AsyncMock(side_effect=lambda d: d)
    repo.update = AsyncMock(side_effect=lambda d: d)
    return repo


@pytest.mark.asyncio
async def test_create_endpoint(
    endpoint_repo: AsyncMock, subscription_repo: AsyncMock, delivery_repo: AsyncMock
) -> None:
    service = WebhookService(endpoint_repo, subscription_repo, delivery_repo)
    payload = WebhookEndpointCreateRequest(
        name="Notify",
        url="https://example.com/hook",
        events=["document.created"],
    )
    result = await service.create_endpoint(uuid.uuid4(), uuid.uuid4(), payload)
    assert result.name == "Notify"
    endpoint_repo.add.assert_awaited_once()
    subscription_repo.add.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_no_subscriptions(
    endpoint_repo: AsyncMock, subscription_repo: AsyncMock, delivery_repo: AsyncMock
) -> None:
    service = WebhookService(endpoint_repo, subscription_repo, delivery_repo)
    event = document_created(uuid.uuid4(), uuid.uuid4())
    results = await service.dispatch_event(event)
    assert results == []
