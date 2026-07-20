"""Compliance enumerations."""

from __future__ import annotations

from enum import StrEnum


class ClassificationLevel(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"


class ComplianceHoldStatus(StrEnum):
    ACTIVE = "active"
    RELEASED = "released"
    PENDING = "pending"


class ExportFormat(StrEnum):
    ZIP = "zip"
    JSON = "json"
    CSV = "csv"
    EDISCOVERY = "ediscovery"


class ExportStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DataSubjectRequestType(StrEnum):
    ACCESS = "access"
    ERASURE = "erasure"
    PORTABILITY = "portability"
    RECTIFICATION = "rectification"


class DataSubjectRequestStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    FULFILLED = "fulfilled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
