"""Notification application service."""

from __future__ import annotations

import uuid

from vaultforge.application.collaboration.schemas import NotificationListQuery, NotificationResponse
from vaultforge.core.exceptions import NotFoundError
from vaultforge.domain.collaboration.entities import Comment, Notification
from vaultforge.domain.collaboration.repositories import NotificationRepository


class NotificationService:
    def __init__(self, notification_repo: NotificationRepository) -> None:
        self._notifications = notification_repo

    async def notify_mentions(
        self,
        *,
        organization_id: uuid.UUID,
        author_id: uuid.UUID,
        comment: Comment,
        mentioned_user_ids: list[uuid.UUID],
    ) -> list[NotificationResponse]:
        notifications = [
            Notification(
                organization_id=organization_id,
                user_id=user_id,
                title="You were mentioned in a comment",
                body=comment.body[:500],
                notification_type="mention",
                resource_type=comment.resource_type,
                resource_id=comment.resource_id,
            )
            for user_id in mentioned_user_ids
            if user_id != author_id
        ]
        if not notifications:
            return []
        saved = list(await self._notifications.add_many(notifications))
        return [self._to_response(item) for item in saved]

    async def list_for_user(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        query: NotificationListQuery,
    ) -> list[NotificationResponse]:
        items = await self._notifications.list_for_user(
            organization_id,
            user_id,
            unread_only=query.unread_only,
            limit=query.limit,
            offset=query.offset,
        )
        return [self._to_response(item) for item in items]

    async def mark_read(
        self,
        organization_id: uuid.UUID,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> NotificationResponse:
        notification = await self._notifications.get_by_id(organization_id, notification_id)
        if notification is None:
            raise NotFoundError("Notification not found")
        if notification.user_id != user_id:
            from vaultforge.core.exceptions import AuthorizationError

            raise AuthorizationError("Notification belongs to another user")
        notification.mark_read()
        saved = await self._notifications.update(notification)
        return self._to_response(saved)

    async def mark_all_read(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> int:
        items = await self._notifications.list_for_user(
            organization_id, user_id, unread_only=True, limit=200, offset=0
        )
        count = 0
        for item in items:
            item.mark_read()
            await self._notifications.update(item)
            count += 1
        return count

    def _to_response(self, notification: Notification) -> NotificationResponse:
        return NotificationResponse(
            id=notification.id,
            organization_id=notification.organization_id,
            user_id=notification.user_id,
            title=notification.title,
            body=notification.body,
            notification_type=notification.notification_type,
            resource_type=notification.resource_type,
            resource_id=notification.resource_id,
            read_at=notification.read_at,
            is_read=notification.is_read,
            created_at=notification.created_at,
            updated_at=notification.updated_at,
        )
