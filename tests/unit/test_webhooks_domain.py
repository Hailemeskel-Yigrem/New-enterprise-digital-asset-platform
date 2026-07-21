"""Unit tests for webhook domain entities."""

from __future__ import annotations

import pytest

from vaultforge.core.exceptions import ValidationError
from vaultforge.domain.webhooks.entities import (
    WebhookDelivery,
    WebhookEndpoint,
    WebhookSubscription,
)
from vaultforge.domain.webhooks.enums import DeliveryStatus, WebhookStatus


def test_endpoint_sign_payload() -> None:
    endpoint = WebhookEndpoint(name="E", url="https://example.com/hook", secret="test-secret")
    body = b'{"test": true}'
    sig = endpoint.sign_payload(body, 1234567890)
    assert sig.startswith("sha256=")


def test_endpoint_invalid_url() -> None:
    with pytest.raises(ValidationError):
        WebhookEndpoint(name="E", url="not-a-url")


def test_endpoint_pause_on_failures() -> None:
    endpoint = WebhookEndpoint(name="E", url="https://example.com/hook", max_retries=2)
    endpoint.record_failure()
    endpoint.record_failure()
    assert endpoint.status == WebhookStatus.PAUSED


def test_subscription_matches_event() -> None:
    sub = WebhookSubscription(events=["document.created"])
    assert sub.matches_event("document.created", {"id": "1"})
    assert not sub.matches_event("document.deleted", {})


def test_delivery_retry_backoff() -> None:
    delivery = WebhookDelivery(event_type="test", max_attempts=5)
    delivery.mark_failure("error")
    assert delivery.status == DeliveryStatus.RETRYING
    assert delivery.next_retry_at is not None
