"""Live integration: document upload + versioning against Postgres.

Requires RUN_LIVE_INTEGRATION=1 and a reachable DATABASE_URL (CI starts
postgres/redis via docker compose).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from vaultforge.application.assets.document_service import DocumentService
from vaultforge.application.assets.schemas import (
    DocumentUploadRequest,
    DocumentVersionCreateRequest,
)
from vaultforge.domain.assets.entities import Folder
from vaultforge.domain.assets.enums import FolderKind, SensitivityLabel, VersionStatus
from vaultforge.infrastructure.persistence.base import Base
from vaultforge.infrastructure.persistence.models.document import (
    DocumentModel,
    DocumentVersionModel,
)
from vaultforge.infrastructure.persistence.models.folder import FolderModel  # noqa: F401
from vaultforge.infrastructure.persistence.models.organization import (  # noqa: F401
    OrganizationModel,
)
from vaultforge.infrastructure.persistence.repositories.document_repository import (
    SqlAlchemyDocumentLockRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyDocumentVersionRepository,
)
from vaultforge.infrastructure.persistence.repositories.folder_repository import (
    SqlAlchemyFolderRepository,
)
from vaultforge.infrastructure.storage.local import LocalFilesystemStorage

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_INTEGRATION") != "1",
    reason="Set RUN_LIVE_INTEGRATION=1 with Postgres available",
)


@pytest_asyncio.fixture
async def db_session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://vaultforge:vaultforge@localhost:5432/vaultforge",
    )
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_document_upload_and_version_persists(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()

    folder_repo = SqlAlchemyFolderRepository(db_session)
    folder = await folder_repo.add(
        Folder(
            organization_id=org_id,
            name="Contracts",
            kind=FolderKind.STANDARD,
            description="integration",
        )
    )
    await db_session.flush()

    storage = LocalFilesystemStorage(tmp_path / "storage")
    service = DocumentService(
        document_repo=SqlAlchemyDocumentRepository(db_session),
        version_repo=SqlAlchemyDocumentVersionRepository(db_session),
        lock_repo=SqlAlchemyDocumentLockRepository(db_session),
        folder_repo=folder_repo,
        storage=storage,
    )

    uploaded = await service.upload_document(
        org_id,
        user_id,
        DocumentUploadRequest(
            folder_id=folder.id,
            name="MSA.pdf",
            sensitivity=SensitivityLabel.CONFIDENTIAL,
            tags=["legal"],
            comment="v1",
        ),
        content=b"%PDF-1.4 demo content",
        content_type="application/pdf",
    )
    await db_session.commit()

    assert uploaded.name == "MSA.pdf"
    assert uploaded.current_version is not None
    assert uploaded.current_version.version_number == 1
    assert uploaded.current_version.status == VersionStatus.CURRENT

    versioned = await service.create_version(
        org_id,
        uploaded.id,
        user_id,
        DocumentVersionCreateRequest(comment="v2 revision"),
        content=b"%PDF-1.4 revised content",
        content_type="application/pdf",
    )
    await db_session.commit()

    assert versioned.current_version is not None
    assert versioned.current_version.version_number == 2
    assert versioned.current_version.status == VersionStatus.CURRENT

    reloaded = await service.get_document(org_id, uploaded.id)
    assert reloaded.current_version is not None
    assert reloaded.current_version.version_number == 2
    assert reloaded.current_version_id == versioned.current_version.id

    persisted_document = await db_session.scalar(
        select(DocumentModel).where(DocumentModel.id == uploaded.id)
    )
    persisted_version_count = await db_session.scalar(
        select(func.count())
        .select_from(DocumentVersionModel)
        .where(DocumentVersionModel.document_id == uploaded.id)
    )
    assert persisted_document is not None
    assert persisted_document.current_version_id == versioned.current_version.id
    assert persisted_version_count == 2

    stored_files = [path for path in (tmp_path / "storage").rglob("*") if path.is_file()]
    assert len(stored_files) >= 2
