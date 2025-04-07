"""Asset domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class VersionStatus(StrEnum):
    PENDING = "pending"
    CURRENT = "current"
    SUPERSEDED = "superseded"


class SensitivityLabel(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class FolderKind(StrEnum):
    ROOT = "root"
    STANDARD = "standard"
    SHARED = "shared"
    ARCHIVE = "archive"
