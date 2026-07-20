"""Billing and quota enumerations."""

from __future__ import annotations

from enum import StrEnum


class PlanTier(StrEnum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class BillingCycle(StrEnum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class QuotaMetric(StrEnum):
    STORAGE_BYTES = "storage_bytes"
    SEATS = "seats"
    DOCUMENTS = "documents"
    API_REQUESTS = "api_requests"
    WEBHOOK_DELIVERIES = "webhook_deliveries"
    EXPORT_PACKAGES = "export_packages"


class QuotaPolicy(StrEnum):
    HARD = "hard"
    SOFT = "soft"
    OVERAGE_BILLING = "overage_billing"


class UsageEventType(StrEnum):
    STORAGE_DELTA = "storage_delta"
    SEAT_ASSIGNED = "seat_assigned"
    SEAT_RELEASED = "seat_released"
    DOCUMENT_CREATED = "document_created"
    DOCUMENT_DELETED = "document_deleted"
    API_CALL = "api_call"
    WEBHOOK_SENT = "webhook_sent"
    EXPORT_CREATED = "export_created"
