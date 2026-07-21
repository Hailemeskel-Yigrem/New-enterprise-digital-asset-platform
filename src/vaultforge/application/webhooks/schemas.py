"""Webhook API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from vaultforge.domain.webhooks.enums import DeliveryStatus, WebhookStatus


class WebhookEndpointCreateRequest(BaseModel):
    name: str
    url: str
    description: str = ""
    events: list[str] = Field(default_factory=list)


class WebhookEndpointResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    url: str
    status: WebhookStatus
    secret: str
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebhookDeliveryResponse(BaseModel):
    id: uuid.UUID
    endpoint_id: uuid.UUID
    event_type: str
    status: DeliveryStatus
    attempt_count: int
    response_status: int | None
    error_message: str
    created_at: datetime

    model_config = {"from_attributes": True}
