"""SQLAlchemy folder repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.domain.assets.entities import Folder
from vaultforge.domain.assets.enums import FolderKind
from vaultforge.domain.assets.repositories import FolderRepository
from vaultforge.infrastructure.persistence.models.folder import FolderModel


def _to_entity(model: FolderModel) -> Folder:
    return Folder(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        parent_id=model.parent_id,
        kind=FolderKind(model.kind),
        description=model.description,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_entity(model: FolderModel, folder: Folder) -> None:
    model.organization_id = folder.organization_id
    model.name = folder.name
    model.parent_id = folder.parent_id
    model.kind = folder.kind.value
    model.description = folder.description
    model.updated_at = folder.updated_at


class SqlAlchemyFolderRepository(FolderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, organization_id: uuid.UUID, folder_id: uuid.UUID) -> Folder | None:
        stmt = select(FolderModel).where(
            FolderModel.id == folder_id,
            FolderModel.organization_id == organization_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_name_and_parent(
        self,
        organization_id: uuid.UUID,
        name: str,
        parent_id: uuid.UUID | None,
    ) -> Folder | None:
        stmt = select(FolderModel).where(
            FolderModel.organization_id == organization_id,
            FolderModel.name == name,
            FolderModel.parent_id == parent_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def add(self, folder: Folder) -> Folder:
        model = FolderModel(
            id=folder.id,
            organization_id=folder.organization_id,
            name=folder.name,
            parent_id=folder.parent_id,
            kind=folder.kind.value,
            description=folder.description,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_entity(model)

    async def update(self, folder: Folder) -> Folder:
        model = await self._session.get(FolderModel, folder.id)
        if model is None:
            raise ValueError(f"Folder {folder.id} not found")
        _apply_entity(model, folder)
        await self._session.flush()
        return _to_entity(model)

    async def list_children(
        self,
        organization_id: uuid.UUID,
        parent_id: uuid.UUID | None,
    ) -> list[Folder]:
        stmt = (
            select(FolderModel)
            .where(
                FolderModel.organization_id == organization_id,
                FolderModel.parent_id == parent_id,
            )
            .order_by(FolderModel.name)
        )
        result = await self._session.execute(stmt)
        return [_to_entity(row) for row in result.scalars().all()]

    async def list_descendant_ids(
        self, organization_id: uuid.UUID, folder_id: uuid.UUID
    ) -> frozenset[uuid.UUID]:
        descendants: set[uuid.UUID] = set()
        frontier = [folder_id]
        while frontier:
            current = frontier.pop()
            stmt = select(FolderModel.id).where(
                FolderModel.organization_id == organization_id,
                FolderModel.parent_id == current,
            )
            result = await self._session.execute(stmt)
            child_ids = list(result.scalars().all())
            for child_id in child_ids:
                if child_id not in descendants:
                    descendants.add(child_id)
                    frontier.append(child_id)
        return frozenset(descendants)
