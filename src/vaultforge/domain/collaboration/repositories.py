"""Repository interfaces for collaboration."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Sequence

from vaultforge.domain.collaboration.entities import Comment, Mention, Notification


class CommentRepository(ABC):
    @abstractmethod
    async def get_by_id(
        self, organization_id: uuid.UUID, comment_id: uuid.UUID
    ) -> Comment | None: ...

    @abstractmethod
    async def add(self, comment: Comment) -> Comment: ...

    @abstractmethod
    async def update(self, comment: Comment) -> Comment: ...

    @abstractmethod
    async def list_for_resource(
        self,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
    ) -> Sequence[Comment]: ...


class MentionRepository(ABC):
    @abstractmethod
    async def list_for_comment(self, comment_id: uuid.UUID) -> Sequence[Mention]: ...

    @abstractmethod
    async def replace_for_comment(
        self, comment_id: uuid.UUID, mentions: Sequence[Mention]
    ) -> Sequence[Mention]: ...


class NotificationRepository(ABC):
    @abstractmethod
    async def add(self, notification: Notification) -> Notification: ...

    @abstractmethod
    async def add_many(self, notifications: Sequence[Notification]) -> Sequence[Notification]: ...

    @abstractmethod
    async def get_by_id(
        self, organization_id: uuid.UUID, notification_id: uuid.UUID
    ) -> Notification | None: ...

    @abstractmethod
    async def update(self, notification: Notification) -> Notification: ...

    @abstractmethod
    async def list_for_user(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Notification]: ...
