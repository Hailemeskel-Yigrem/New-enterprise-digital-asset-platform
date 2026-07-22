"""Identity aggregates and entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from vaultforge.domain.common import Entity
from vaultforge.domain.identity.enums import ROLE_PERMISSIONS, MembershipStatus, OrgRole, Permission


@dataclass(slots=True)
class Organization(Entity):
    name: str = ""
    slug: str = ""
    is_active: bool = True
    plan_code: str = "standard"
    max_storage_gb: int = 100


@dataclass(slots=True)
class User(Entity):
    email: str = ""
    full_name: str = ""
    password_hash: str = ""
    is_active: bool = True
    is_email_verified: bool = False
    last_login_at: datetime | None = None


@dataclass(slots=True)
class Membership(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
    role: OrgRole = OrgRole.VIEWER
    status: MembershipStatus = MembershipStatus.ACTIVE

    def has_permission(self, permission: Permission) -> bool:
        if self.status != MembershipStatus.ACTIVE:
            return False
        return permission in ROLE_PERMISSIONS.get(self.role, frozenset())


@dataclass(slots=True)
class Team(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    description: str = ""
    member_ids: list[uuid.UUID] = field(default_factory=list)
