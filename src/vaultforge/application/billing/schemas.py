"""Billing API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from vaultforge.domain.billing.enums import PlanTier, QuotaMetric, QuotaPolicy


class UsageSnapshotResponse(BaseModel):
    organization_id: uuid.UUID
    totals: dict[str, int]
    period_start: datetime
    period_end: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuotaStatusResponse(BaseModel):
    metric: QuotaMetric
    allocated: int
    consumed: int
    reserved: int
    available: int
    policy: QuotaPolicy


class QuotaCheckRequest(BaseModel):
    metric: QuotaMetric
    amount: int


class QuotaCheckResponse(BaseModel):
    allowed: bool
    metric: QuotaMetric
    requested: int
    available: int
    message: str = ""


class BillingPlanResponse(BaseModel):
    organization_id: uuid.UUID
    tier: PlanTier
    name: str
    seat_count: int
    is_active: bool

    model_config = {"from_attributes": True}
