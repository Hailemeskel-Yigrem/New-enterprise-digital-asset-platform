"""Webhook endpoint, subscription, and delivery entities."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from vaultforge.core.exceptions import ValidationError
from vaultforge.domain.common import Entity, utc_now
from vaultforge.domain.webhooks.enums import DeliveryStatus, WebhookEvent, WebhookStatus


def _validate_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned.startswith(("https://", "http://")):
        raise ValidationError("Webhook URL must use http or https")
    if len(cleaned) > 2048:
        raise ValidationError("Webhook URL too long")
    return cleaned


@dataclass(slots=True)
class WebhookEndpoint(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    url: str = ""
    secret: str = field(default_factory=lambda: secrets.token_hex(32))
    status: WebhookStatus = WebhookStatus.ACTIVE
    created_by: uuid.UUID = field(default_factory=uuid.uuid4)
    description: str = ""
    timeout_seconds: int = 30
    max_retries: int = 5
    consecutive_failures: int = 0
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("Webhook endpoint name is required")
        self.url = _validate_url(self.url)
        if self.timeout_seconds < 1 or self.timeout_seconds > 120:
            raise ValidationError("timeout_seconds must be between 1 and 120")

    def sign_payload(self, payload: bytes, timestamp: int) -> str:
        message = f"{timestamp}.".encode() + payload
        digest = hmac.new(self.secret.encode(), message, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    def disable(self) -> None:
        self.status = WebhookStatus.DISABLED
        self.touch()

    def pause(self) -> None:
        self.status = WebhookStatus.PAUSED
        self.touch()

    def activate(self) -> None:
        self.status = WebhookStatus.ACTIVE
        self.consecutive_failures = 0
        self.touch()

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.last_success_at = utc_now()
        self.touch()

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        self.last_failure_at = utc_now()
        if self.consecutive_failures >= self.max_retries:
            self.status = WebhookStatus.PAUSED
        self.touch()

    def is_deliverable(self) -> bool:
        return self.status == WebhookStatus.ACTIVE


@dataclass(slots=True)
class WebhookSubscription(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    endpoint_id: uuid.UUID = field(default_factory=uuid.uuid4)
    events: list[str] = field(default_factory=list)
    filter_expression: str = ""
    is_active: bool = True

    def __post_init__(self) -> None:
        allowed = WebhookEvent.all_values()
        for event in self.events:
            if event not in allowed:
                raise ValidationError(f"Unsupported webhook event: {event}")

    def matches_event(self, event_type: str, payload: dict[str, object]) -> bool:
        if not self.is_active:
            return False
        if event_type not in self.events:
            return False
        if not self.filter_expression:
            return True
        return _evaluate_filter(self.filter_expression, payload)


def _evaluate_filter(expression: str, payload: dict[str, object]) -> bool:
    parts = expression.split("=")
    if len(parts) != 2:
        return True
    key, expected = parts[0].strip(), parts[1].strip()
    actual = payload.get(key)
    return str(actual) == expected


@dataclass(slots=True)
class WebhookDelivery(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    endpoint_id: uuid.UUID = field(default_factory=uuid.uuid4)
    event_type: str = ""
    payload: dict[str, object] = field(default_factory=dict)
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempt_count: int = 0
    max_attempts: int = 5
    response_status: int | None = None
    response_body: str = ""
    error_message: str = ""
    next_retry_at: datetime | None = None
    delivered_at: datetime | None = None
    duration_ms: int | None = None

    def mark_success(self, status_code: int, body: str, duration_ms: int) -> None:
        self.status = DeliveryStatus.SUCCESS
        self.response_status = status_code
        self.response_body = body[:4000]
        self.duration_ms = duration_ms
        self.delivered_at = utc_now()
        self.error_message = ""
        self.touch()

    def mark_failure(self, error: str, *, status_code: int | None = None) -> None:
        self.attempt_count += 1
        self.error_message = error[:2000]
        self.response_status = status_code
        if self.attempt_count >= self.max_attempts:
            self.status = DeliveryStatus.FAILED
            self.next_retry_at = None
        else:
            self.status = DeliveryStatus.RETRYING
            backoff = min(3600, 2**self.attempt_count * 30)
            self.next_retry_at = utc_now() + timedelta(seconds=backoff)
        self.touch()

    def build_request_body(self) -> bytes:
        envelope = {
            "event_type": self.event_type,
            "delivery_id": str(self.id),
            "organization_id": str(self.organization_id),
            "payload": self.payload,
            "timestamp": utc_now().isoformat(),
        }
        return json.dumps(envelope, separators=(",", ":")).encode()

    def is_ready_for_retry(self, *, at: datetime | None = None) -> bool:
        if self.status not in (DeliveryStatus.PENDING, DeliveryStatus.RETRYING):
            return False
        if self.next_retry_at is None:
            return True
        return (at or utc_now()) >= self.next_retry_at
