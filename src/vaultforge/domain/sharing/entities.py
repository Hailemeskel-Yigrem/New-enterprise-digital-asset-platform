"""Share grants, links, and ACL domain entities."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from vaultforge.core.exceptions import AuthorizationError, ValidationError
from vaultforge.domain.common import Entity, utc_now
from vaultforge.domain.sharing.enums import (
    AclEffect,
    SharePermission,
    ShareResourceType,
    ShareStatus,
    ShareTargetType,
    permission_includes,
)


def _require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{field_name} cannot be empty")
    return cleaned


@dataclass(slots=True)
class ShareGrant(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    resource_type: ShareResourceType = ShareResourceType.DOCUMENT
    resource_id: uuid.UUID = field(default_factory=uuid.uuid4)
    target_type: ShareTargetType = ShareTargetType.USER
    target_id: uuid.UUID | None = None
    target_email: str | None = None
    permission: SharePermission = SharePermission.VIEW
    granted_by: uuid.UUID = field(default_factory=uuid.uuid4)
    status: ShareStatus = ShareStatus.ACTIVE
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    revoked_by: uuid.UUID | None = None
    message: str = ""

    def __post_init__(self) -> None:
        if self.target_type == ShareTargetType.EXTERNAL_EMAIL:
            if not self.target_email:
                raise ValidationError("External email share requires target_email")
            self.target_email = self.target_email.lower().strip()
        elif self.target_type != ShareTargetType.PUBLIC_LINK and self.target_id is None:
            raise ValidationError("Share target requires target_id")

    def is_active(self, *, at: datetime | None = None) -> bool:
        if self.status != ShareStatus.ACTIVE:
            return False
        return not (self.expires_at is not None and (at or utc_now()) >= self.expires_at)

    def allows(self, required: SharePermission) -> bool:
        return self.is_active() and permission_includes(self.permission, required)

    def revoke(self, actor_id: uuid.UUID) -> None:
        if self.status == ShareStatus.REVOKED:
            return
        self.status = ShareStatus.REVOKED
        self.revoked_at = utc_now()
        self.revoked_by = actor_id
        self.touch()

    def extend_expiry(self, days: int) -> None:
        if days < 1:
            raise ValidationError("Extension days must be positive")
        base = self.expires_at or utc_now()
        self.expires_at = base + timedelta(days=days)
        if self.status == ShareStatus.EXPIRED:
            self.status = ShareStatus.ACTIVE
        self.touch()


@dataclass(slots=True)
class ShareLink(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    resource_type: ShareResourceType = ShareResourceType.DOCUMENT
    resource_id: uuid.UUID = field(default_factory=uuid.uuid4)
    token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    permission: SharePermission = SharePermission.VIEW
    created_by: uuid.UUID = field(default_factory=uuid.uuid4)
    status: ShareStatus = ShareStatus.ACTIVE
    password_hash: str | None = None
    max_uses: int | None = None
    use_count: int = 0
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        self.token = _require_non_empty(self.token, "Token")

    def is_usable(self, *, at: datetime | None = None) -> bool:
        if self.status != ShareStatus.ACTIVE:
            return False
        if self.expires_at is not None and (at or utc_now()) >= self.expires_at:
            return False
        return not (self.max_uses is not None and self.use_count >= self.max_uses)

    def record_use(self) -> None:
        if not self.is_usable():
            raise AuthorizationError("Share link is not usable")
        self.use_count += 1
        if self.max_uses is not None and self.use_count >= self.max_uses:
            self.status = ShareStatus.EXPIRED
        self.touch()

    def revoke(self) -> None:
        self.status = ShareStatus.REVOKED
        self.touch()


@dataclass(slots=True)
class ShareInvitation(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    resource_type: ShareResourceType = ShareResourceType.DOCUMENT
    resource_id: uuid.UUID = field(default_factory=uuid.uuid4)
    email: str = ""
    permission: SharePermission = SharePermission.VIEW
    invited_by: uuid.UUID = field(default_factory=uuid.uuid4)
    status: ShareStatus = ShareStatus.PENDING
    token: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    accepted_by: uuid.UUID | None = None
    accepted_at: datetime | None = None
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        self.email = _require_non_empty(self.email, "Email").lower()

    def accept(self, user_id: uuid.UUID) -> None:
        if self.status != ShareStatus.PENDING:
            raise ValidationError("Invitation is not pending")
        if self.expires_at is not None and utc_now() >= self.expires_at:
            self.status = ShareStatus.EXPIRED
            raise ValidationError("Invitation has expired")
        self.status = ShareStatus.ACTIVE
        self.accepted_by = user_id
        self.accepted_at = utc_now()
        self.touch()


@dataclass(slots=True)
class AccessControlEntry(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    resource_type: ShareResourceType = ShareResourceType.DOCUMENT
    resource_id: uuid.UUID = field(default_factory=uuid.uuid4)
    principal_type: ShareTargetType = ShareTargetType.USER
    principal_id: uuid.UUID = field(default_factory=uuid.uuid4)
    permission: SharePermission = SharePermission.VIEW
    effect: AclEffect = AclEffect.ALLOW
    inherited: bool = False
    source_folder_id: uuid.UUID | None = None

    def evaluate(self, required: SharePermission) -> bool | None:
        if not permission_includes(self.permission, required):
            return None
        return self.effect == AclEffect.ALLOW


def merge_acl_entries(
    entries: list[AccessControlEntry],
    required: SharePermission,
) -> bool:
    allow = False
    for entry in entries:
        result = entry.evaluate(required)
        if result is None:
            continue
        if not result:
            return False
        allow = True
    return allow
