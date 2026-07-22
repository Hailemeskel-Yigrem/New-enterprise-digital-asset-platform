"""Dashboard metrics and recent activity."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.analytics.schemas import (
    ActivityKind,
    DashboardResponse,
    DashboardStatsResponse,
    RecentActivityItem,
)
from vaultforge.domain.assets.enums import DocumentStatus, VersionStatus
from vaultforge.infrastructure.persistence.models.document import (
    DocumentModel,
    DocumentVersionModel,
)
from vaultforge.infrastructure.persistence.models.folder import FolderModel
from vaultforge.infrastructure.persistence.models.organization import OrganizationModel


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_dashboard(self, organization_id: uuid.UUID) -> DashboardResponse:
        org = await self._session.get(OrganizationModel, organization_id)
        storage_limit_bytes = (org.max_storage_gb * 1024 * 1024 * 1024) if org else 0

        document_count = await self._scalar_count(
            select(func.count())
            .select_from(DocumentModel)
            .where(
                DocumentModel.organization_id == organization_id,
                DocumentModel.status != DocumentStatus.DELETED.value,
            )
        )
        folder_count = await self._scalar_count(
            select(func.count())
            .select_from(FolderModel)
            .where(FolderModel.organization_id == organization_id)
        )
        pending_approvals = await self._scalar_count(
            select(func.count())
            .select_from(DocumentVersionModel)
            .join(DocumentModel, DocumentVersionModel.document_id == DocumentModel.id)
            .where(
                DocumentModel.organization_id == organization_id,
                DocumentVersionModel.status == VersionStatus.PENDING.value,
            )
        )
        storage_used_bytes = await self._scalar_sum(
            select(func.coalesce(func.sum(DocumentVersionModel.size_bytes), 0))
            .select_from(DocumentVersionModel)
            .join(DocumentModel, DocumentVersionModel.document_id == DocumentModel.id)
            .where(
                DocumentModel.organization_id == organization_id,
                DocumentVersionModel.status == VersionStatus.CURRENT.value,
            )
        )

        recent_activity = await self._recent_activity(organization_id)
        stats = DashboardStatsResponse(
            document_count=document_count,
            folder_count=folder_count,
            pending_approvals=pending_approvals,
            storage_used_bytes=storage_used_bytes,
            storage_limit_bytes=storage_limit_bytes,
        )
        return DashboardResponse(stats=stats, recent_activity=recent_activity)

    async def _recent_activity(self, organization_id: uuid.UUID) -> list[RecentActivityItem]:
        doc_stmt = (
            select(DocumentModel)
            .where(
                DocumentModel.organization_id == organization_id,
                DocumentModel.status != DocumentStatus.DELETED.value,
            )
            .order_by(DocumentModel.updated_at.desc())
            .limit(10)
        )
        doc_result = await self._session.execute(doc_stmt)
        documents = list(doc_result.scalars().all())

        folder_stmt = (
            select(FolderModel)
            .where(FolderModel.organization_id == organization_id)
            .order_by(FolderModel.updated_at.desc())
            .limit(5)
        )
        folder_result = await self._session.execute(folder_stmt)
        folders = list(folder_result.scalars().all())

        items: list[RecentActivityItem] = []
        for document in documents:
            items.append(
                RecentActivityItem(
                    kind=ActivityKind.DOCUMENT_UPDATED,
                    resource_id=document.id,
                    resource_name=document.name,
                    actor_id=document.created_by,
                    occurred_at=document.updated_at,
                )
            )
        for folder in folders:
            items.append(
                RecentActivityItem(
                    kind=ActivityKind.FOLDER_CREATED,
                    resource_id=folder.id,
                    resource_name=folder.name,
                    actor_id=None,
                    occurred_at=folder.updated_at,
                )
            )
        items.sort(key=lambda item: item.occurred_at, reverse=True)
        return items[:15]

    async def _scalar_count(self, stmt: Select[tuple[int]]) -> int:
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def _scalar_sum(self, stmt: Select[tuple[int]]) -> int:
        result = await self._session.execute(stmt)
        return int(result.scalar_one())
