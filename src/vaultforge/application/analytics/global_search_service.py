"""Cross-entity search across documents and folders."""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.analytics.schemas import (
    GlobalSearchRequest,
    GlobalSearchResponse,
    SearchDocumentHit,
    SearchFolderHit,
)
from vaultforge.domain.assets.enums import DocumentStatus, SensitivityLabel
from vaultforge.infrastructure.persistence.models.document import DocumentModel
from vaultforge.infrastructure.persistence.models.folder import FolderModel


class GlobalSearchService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self,
        organization_id: uuid.UUID,
        payload: GlobalSearchRequest,
    ) -> GlobalSearchResponse:
        pattern = f"%{payload.query.strip()}%"
        doc_stmt = (
            select(DocumentModel)
            .where(
                DocumentModel.organization_id == organization_id,
                DocumentModel.status != DocumentStatus.DELETED.value,
                or_(
                    DocumentModel.name.ilike(pattern),
                    DocumentModel.tags.any(payload.query.strip().lower()),
                ),
            )
            .order_by(DocumentModel.updated_at.desc())
            .limit(payload.limit)
        )
        folder_stmt = (
            select(FolderModel)
            .where(
                FolderModel.organization_id == organization_id,
                FolderModel.name.ilike(pattern),
            )
            .order_by(FolderModel.updated_at.desc())
            .limit(payload.limit)
        )

        documents = list((await self._session.execute(doc_stmt)).scalars().all())
        folders = list((await self._session.execute(folder_stmt)).scalars().all())

        doc_hits = [
            SearchDocumentHit(
                id=document.id,
                name=document.name,
                folder_id=document.folder_id,
                status=DocumentStatus(document.status),
                sensitivity=SensitivityLabel(document.sensitivity),
                updated_at=document.updated_at,
            )
            for document in documents
        ]
        folder_hits = [
            SearchFolderHit(
                id=folder.id,
                name=folder.name,
                parent_id=folder.parent_id,
                updated_at=folder.updated_at,
            )
            for folder in folders
        ]
        return GlobalSearchResponse(
            query=payload.query,
            documents=doc_hits,
            folders=folder_hits,
            total_hits=len(doc_hits) + len(folder_hits),
        )

def rank_score(*, name_hit: bool, tag_hit: bool, recency_days: int) -> float:
    """Lightweight ranking heuristic for global search results."""
    score = 0.0
    if name_hit:
        score += 5.0
    if tag_hit:
        score += 2.5
    score += max(0.0, 2.0 - (recency_days / 30.0))
    return score
