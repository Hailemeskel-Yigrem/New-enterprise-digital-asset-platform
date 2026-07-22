"""SQLAlchemy collaboration repositories."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vaultforge.domain.collaboration.entities import Comment, Mention, Notification
from vaultforge.domain.collaboration.repositories import (
    CommentRepository,
    MentionRepository,
    NotificationRepository,
)
from vaultforge.infrastructure.persistence.models.collaboration import (
    CommentModel,
    MentionModel,
    NotificationModel,
)


def _comment_to_entity(model: CommentModel) -> Comment:
    return Comment(
        id=model.id,
        organization_id=model.organization_id,
        resource_type=model.resource_type,
        resource_id=model.resource_id,
        author_id=model.author_id,
        body=model.body,
        parent_id=model.parent_id,
        edited_at=model.edited_at,
        deleted_at=model.deleted_at,
        mentions=[_mention_to_entity(mention) for mention in model.mentions],
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_comment(model: CommentModel, comment: Comment) -> None:
    model.body = comment.body
    model.edited_at = comment.edited_at
    model.deleted_at = comment.deleted_at
    model.updated_at = comment.updated_at


def _mention_to_entity(model: MentionModel) -> Mention:
    return Mention(
        id=model.id,
        comment_id=model.comment_id,
        user_id=model.user_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _notification_to_entity(model: NotificationModel) -> Notification:
    return Notification(
        id=model.id,
        organization_id=model.organization_id,
        user_id=model.user_id,
        title=model.title,
        body=model.body,
        notification_type=model.notification_type,
        resource_type=model.resource_type,
        resource_id=model.resource_id,
        read_at=model.read_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_notification(model: NotificationModel, notification: Notification) -> None:
    model.read_at = notification.read_at
    model.updated_at = notification.updated_at


class SqlAlchemyCommentRepository(CommentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, organization_id: uuid.UUID, comment_id: uuid.UUID) -> Comment | None:
        stmt = (
            select(CommentModel)
            .where(
                CommentModel.id == comment_id,
                CommentModel.organization_id == organization_id,
            )
            .options(selectinload(CommentModel.mentions))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _comment_to_entity(model) if model else None

    async def add(self, comment: Comment) -> Comment:
        model = CommentModel(
            id=comment.id,
            organization_id=comment.organization_id,
            resource_type=comment.resource_type,
            resource_id=comment.resource_id,
            author_id=comment.author_id,
            body=comment.body,
            parent_id=comment.parent_id,
            edited_at=comment.edited_at,
            deleted_at=comment.deleted_at,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _comment_to_entity(model)

    async def update(self, comment: Comment) -> Comment:
        model = await self._session.get(CommentModel, comment.id)
        if model is None:
            raise ValueError("Comment not found")
        _apply_comment(model, comment)
        await self._session.flush()
        return _comment_to_entity(model)

    async def list_for_resource(
        self,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
    ) -> list[Comment]:
        stmt = (
            select(CommentModel)
            .where(
                CommentModel.organization_id == organization_id,
                CommentModel.resource_type == resource_type,
                CommentModel.resource_id == resource_id,
            )
            .options(selectinload(CommentModel.mentions))
            .order_by(CommentModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return [_comment_to_entity(model) for model in result.scalars().all()]


class SqlAlchemyMentionRepository(MentionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_comment(self, comment_id: uuid.UUID) -> list[Mention]:
        stmt = select(MentionModel).where(MentionModel.comment_id == comment_id)
        result = await self._session.execute(stmt)
        return [_mention_to_entity(model) for model in result.scalars().all()]

    async def replace_for_comment(
        self, comment_id: uuid.UUID, mentions: Sequence[Mention]
    ) -> list[Mention]:
        await self._session.execute(
            delete(MentionModel).where(MentionModel.comment_id == comment_id)
        )
        models = [
            MentionModel(
                id=mention.id,
                comment_id=comment_id,
                user_id=mention.user_id,
                created_at=mention.created_at,
                updated_at=mention.updated_at,
            )
            for mention in mentions
        ]
        self._session.add_all(models)
        await self._session.flush()
        return [_mention_to_entity(model) for model in models]


class SqlAlchemyNotificationRepository(NotificationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, notification: Notification) -> Notification:
        saved = list(await self.add_many([notification]))
        return saved[0]

    async def add_many(self, notifications: Sequence[Notification]) -> list[Notification]:
        models = [
            NotificationModel(
                id=notification.id,
                organization_id=notification.organization_id,
                user_id=notification.user_id,
                title=notification.title,
                body=notification.body,
                notification_type=notification.notification_type,
                resource_type=notification.resource_type,
                resource_id=notification.resource_id,
                read_at=notification.read_at,
                created_at=notification.created_at,
                updated_at=notification.updated_at,
            )
            for notification in notifications
        ]
        self._session.add_all(models)
        await self._session.flush()
        return [_notification_to_entity(model) for model in models]

    async def get_by_id(
        self, organization_id: uuid.UUID, notification_id: uuid.UUID
    ) -> Notification | None:
        stmt = select(NotificationModel).where(
            NotificationModel.id == notification_id,
            NotificationModel.organization_id == organization_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _notification_to_entity(model) if model else None

    async def update(self, notification: Notification) -> Notification:
        model = await self._session.get(NotificationModel, notification.id)
        if model is None:
            raise ValueError("Notification not found")
        _apply_notification(model, notification)
        await self._session.flush()
        return _notification_to_entity(model)

    async def list_for_user(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        stmt = select(NotificationModel).where(
            NotificationModel.organization_id == organization_id,
            NotificationModel.user_id == user_id,
        )
        if unread_only:
            stmt = stmt.where(NotificationModel.read_at.is_(None))
        stmt = stmt.order_by(NotificationModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [_notification_to_entity(model) for model in result.scalars().all()]
