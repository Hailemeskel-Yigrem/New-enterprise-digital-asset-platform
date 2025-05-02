"""Digital signature domain enumerations."""

from __future__ import annotations

from enum import Enum


class SignatureRequestStatus(str, Enum):
    PENDING = "pending"
    PARTIALLY_SIGNED = "partially_signed"
    COMPLETED = "completed"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class SignerStatus(str, Enum):
    PENDING = "pending"
    SIGNED = "signed"
    DECLINED = "declined"
