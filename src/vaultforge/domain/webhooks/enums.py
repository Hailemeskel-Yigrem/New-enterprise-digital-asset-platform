"""Webhook enumerations."""

from __future__ import annotations

from enum import StrEnum


class WebhookStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    PAUSED = "paused"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class WebhookEvent(StrEnum):
    DOCUMENT_CREATED = "document.created"
    DOCUMENT_UPDATED = "document.updated"
    DOCUMENT_DELETED = "document.deleted"
    FOLDER_CREATED = "folder.created"
    METADATA_UPDATED = "metadata.updated"
    CLASSIFICATION_CHANGED = "classification.changed"
    HOLD_PLACED = "compliance.hold.placed"
    HOLD_RELEASED = "compliance.hold.released"
    EXPORT_COMPLETED = "compliance.export.completed"
    QUOTA_EXCEEDED = "billing.quota.exceeded"
    SHARE_CREATED = "share.created"

    @classmethod
    def all_values(cls) -> frozenset[str]:
        return frozenset(member.value for member in cls)
