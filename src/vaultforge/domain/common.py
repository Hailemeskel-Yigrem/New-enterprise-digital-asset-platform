"""Shared domain primitives."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import NewType

OrganizationId = NewType("OrganizationId", uuid.UUID)
UserId = NewType("UserId", uuid.UUID)


def new_id() -> uuid.UUID:
    return uuid.uuid4()


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class Entity:
    id: uuid.UUID = field(default_factory=new_id)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()
