"""Usage report generation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.analytics.schemas import (
    ReportDimension,
    ReportRow,
    UsageReportRequest,
    UsageReportResponse,
)
from vaultforge.domain.assets.enums import DocumentStatus
from vaultforge.infrastructure.persistence.models.document import (
    DocumentModel,
    DocumentVersionModel,
)
from vaultforge.infrastructure.persistence.models.folder import FolderModel


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def generate_usage_report(
        self,
        organization_id: uuid.UUID,
        payload: UsageReportRequest,
    ) -> UsageReportResponse:
        if payload.dimension == ReportDimension.USER:
            rows = await self._by_user(organization_id, payload.limit)
        elif payload.dimension == ReportDimension.FOLDER:
            rows = await self._by_folder(organization_id, payload.limit)
        else:
            rows = await self._by_sensitivity(organization_id, payload.limit)

        return UsageReportResponse(
            organization_id=organization_id,
            dimension=payload.dimension,
            rows=rows,
            generated_at=datetime.now(tz=UTC),
        )

    async def _by_user(self, organization_id: uuid.UUID, limit: int) -> list[ReportRow]:
        stmt = (
            select(
                DocumentModel.created_by,
                func.count(DocumentModel.id),
                func.coalesce(func.sum(DocumentVersionModel.size_bytes), 0),
            )
            .outerjoin(
                DocumentVersionModel,
                DocumentVersionModel.id == DocumentModel.current_version_id,
            )
            .where(
                DocumentModel.organization_id == organization_id,
                DocumentModel.status != DocumentStatus.DELETED.value,
            )
            .group_by(DocumentModel.created_by)
            .order_by(func.count(DocumentModel.id).desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [
            ReportRow(
                key=str(user_id),
                label=str(user_id),
                document_count=int(doc_count),
                storage_bytes=int(storage),
            )
            for user_id, doc_count, storage in result.all()
        ]

    async def _by_folder(self, organization_id: uuid.UUID, limit: int) -> list[ReportRow]:
        folder_names = {
            row.id: row.name
            for row in (
                await self._session.execute(
                    select(FolderModel).where(FolderModel.organization_id == organization_id)
                )
            )
            .scalars()
            .all()
        }
        stmt = (
            select(
                DocumentModel.folder_id,
                func.count(DocumentModel.id),
                func.coalesce(func.sum(DocumentVersionModel.size_bytes), 0),
            )
            .outerjoin(
                DocumentVersionModel,
                DocumentVersionModel.id == DocumentModel.current_version_id,
            )
            .where(
                DocumentModel.organization_id == organization_id,
                DocumentModel.status != DocumentStatus.DELETED.value,
            )
            .group_by(DocumentModel.folder_id)
            .order_by(func.count(DocumentModel.id).desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows: list[ReportRow] = []
        for folder_id, doc_count, storage in result.all():
            rows.append(
                ReportRow(
                    key=str(folder_id),
                    label=folder_names.get(folder_id, str(folder_id)),
                    document_count=int(doc_count),
                    storage_bytes=int(storage),
                )
            )
        return rows

    async def _by_sensitivity(self, organization_id: uuid.UUID, limit: int) -> list[ReportRow]:
        stmt = (
            select(
                DocumentModel.sensitivity,
                func.count(DocumentModel.id),
                func.coalesce(func.sum(DocumentVersionModel.size_bytes), 0),
            )
            .outerjoin(
                DocumentVersionModel,
                DocumentVersionModel.id == DocumentModel.current_version_id,
            )
            .where(
                DocumentModel.organization_id == organization_id,
                DocumentModel.status != DocumentStatus.DELETED.value,
            )
            .group_by(DocumentModel.sensitivity)
            .order_by(func.count(DocumentModel.id).desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [
            ReportRow(
                key=sensitivity,
                label=sensitivity,
                document_count=int(doc_count),
                storage_bytes=int(storage),
            )
            for sensitivity, doc_count, storage in result.all()
        ]
