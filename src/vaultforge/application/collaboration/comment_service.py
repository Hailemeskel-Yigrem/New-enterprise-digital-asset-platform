"""Comment application service."""

from __future__ import annotations

import uuid

from vaultforge.application.collaboration.notification_service import NotificationService
from vaultforge.application.collaboration.schemas import (
    CommentCreateRequest,
    CommentResponse,
    CommentUpdateRequest,
    MentionResponse,
)
from vaultforge.core.exceptions import NotFoundError
from vaultforge.domain.collaboration.entities import Comment, extract_mention_user_ids
from vaultforge.domain.collaboration.repositories import CommentRepository, MentionRepository


class CommentService:
    def __init__(
        self,
        comment_repo: CommentRepository,
        mention_repo: MentionRepository,
        notification_service: NotificationService,
    ) -> None:
        self._comments = comment_repo
        self._mentions = mention_repo
        self._notifications = notification_service

    async def create_comment(
        self,
        organization_id: uuid.UUID,
        author_id: uuid.UUID,
        payload: CommentCreateRequest,
    ) -> CommentResponse:
        comment = Comment(
            organization_id=organization_id,
            resource_type=payload.resource_type.strip(),
            resource_id=payload.resource_id,
            author_id=author_id,
            body=payload.body.strip(),
            parent_id=payload.parent_id,
        )
        saved_comment = await self._comments.add(comment)

        mention_ids = extract_mention_user_ids(saved_comment.body)
        mentions = saved_comment.sync_mentions(mention_ids)
        if mentions:
            await self._mentions.replace_for_comment(saved_comment.id, mentions)
            await self._notifications.notify_mentions(
                organization_id=organization_id,
                author_id=author_id,
                comment=saved_comment,
                mentioned_user_ids=mention_ids,
            )

        saved_comment.mentions = list(await self._mentions.list_for_comment(saved_comment.id))
        return self._to_response(saved_comment)

    async def update_comment(
        self,
        organization_id: uuid.UUID,
        comment_id: uuid.UUID,
        author_id: uuid.UUID,
        payload: CommentUpdateRequest,
    ) -> CommentResponse:
        comment = await self._require_comment(organization_id, comment_id)
        if comment.author_id != author_id:
            from vaultforge.core.exceptions import AuthorizationError

            raise AuthorizationError("Only the author may edit this comment")
        if comment.deleted_at is not None:
            from vaultforge.core.exceptions import ConflictError

            raise ConflictError("Comment has been deleted")

        mention_ids = comment.edit(payload.body.strip())
        mentions = comment.sync_mentions(mention_ids)
        await self._comments.update(comment)
        await self._mentions.replace_for_comment(comment.id, mentions)

        comment.mentions = list(await self._mentions.list_for_comment(comment.id))
        return self._to_response(comment)

    async def delete_comment(
        self,
        organization_id: uuid.UUID,
        comment_id: uuid.UUID,
        author_id: uuid.UUID,
    ) -> CommentResponse:
        comment = await self._require_comment(organization_id, comment_id)
        if comment.author_id != author_id:
            from vaultforge.core.exceptions import AuthorizationError

            raise AuthorizationError("Only the author may delete this comment")
        comment.soft_delete()
        saved = await self._comments.update(comment)
        saved.mentions = list(await self._mentions.list_for_comment(saved.id))
        return self._to_response(saved)

    async def list_comments(
        self,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
    ) -> list[CommentResponse]:
        comments = await self._comments.list_for_resource(
            organization_id, resource_type.strip(), resource_id
        )
        responses: list[CommentResponse] = []
        for comment in comments:
            if comment.deleted_at is not None:
                continue
            comment.mentions = list(await self._mentions.list_for_comment(comment.id))
            responses.append(self._to_response(comment))
        return responses

    async def _require_comment(self, organization_id: uuid.UUID, comment_id: uuid.UUID) -> Comment:
        comment = await self._comments.get_by_id(organization_id, comment_id)
        if comment is None:
            raise NotFoundError("Comment not found")
        comment.mentions = list(await self._mentions.list_for_comment(comment.id))
        return comment

    def _to_response(self, comment: Comment) -> CommentResponse:
        return CommentResponse(
            id=comment.id,
            organization_id=comment.organization_id,
            resource_type=comment.resource_type,
            resource_id=comment.resource_id,
            author_id=comment.author_id,
            body=comment.body,
            parent_id=comment.parent_id,
            edited_at=comment.edited_at,
            deleted_at=comment.deleted_at,
            mentions=[MentionResponse.model_validate(mention) for mention in comment.mentions],
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )
