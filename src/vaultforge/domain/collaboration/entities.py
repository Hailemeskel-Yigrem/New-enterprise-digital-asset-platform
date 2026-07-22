"""Comment, mention, and notification aggregates."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from vaultforge.core.exceptions import ValidationError
from vaultforge.domain.common import Entity, utc_now

MENTION_PATTERN = re.compile(r"@\[([^\]]+)\]\(([0-9a-fA-F-]{36})\)")


def extract_mention_user_ids(body: str) -> list[uuid.UUID]:
    """Parse mention tokens like @[Jane Doe](uuid) from comment body."""
    seen: set[uuid.UUID] = set()
    ordered: list[uuid.UUID] = []
    for match in MENTION_PATTERN.finditer(body):
        user_id = uuid.UUID(match.group(2))
        if user_id not in seen:
            seen.add(user_id)
            ordered.append(user_id)
    return ordered


def _require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{field_name} cannot be empty")
    return cleaned


@dataclass(slots=True)
class Mention(Entity):
    comment_id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(slots=True)
class Comment(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    resource_type: str = ""
    resource_id: uuid.UUID = field(default_factory=uuid.uuid4)
    author_id: uuid.UUID = field(default_factory=uuid.uuid4)
    body: str = ""
    parent_id: uuid.UUID | None = None
    edited_at: datetime | None = None
    deleted_at: datetime | None = None
    mentions: list[Mention] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.resource_type = _require_non_empty(self.resource_type, "Resource type")
        self.body = _require_non_empty(self.body, "Comment body")

    def edit(self, new_body: str) -> list[uuid.UUID]:
        self.body = _require_non_empty(new_body, "Comment body")
        self.edited_at = utc_now()
        self.touch()
        return extract_mention_user_ids(self.body)

    def soft_delete(self) -> None:
        if self.deleted_at is not None:
            return
        self.deleted_at = utc_now()
        self.touch()

    def sync_mentions(self, user_ids: list[uuid.UUID]) -> list[Mention]:
        self.mentions = [Mention(comment_id=self.id, user_id=user_id) for user_id in user_ids]
        self.touch()
        return self.mentions


@dataclass(slots=True)
class Notification(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
    title: str = ""
    body: str = ""
    notification_type: str = "info"
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    read_at: datetime | None = None

    def __post_init__(self) -> None:
        self.title = _require_non_empty(self.title, "Title")
        self.body = _require_non_empty(self.body, "Body")

    def mark_read(self) -> None:
        if self.read_at is None:
            self.read_at = utc_now()
            self.touch()

    @property
    def is_read(self) -> bool:
        return self.read_at is not None
