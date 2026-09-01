"""Live integration coverage for persisted share-grant lifecycle transitions."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from datetime import timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from vaultforge.domain.common import utc_now
from vaultforge.domain.sharing.entities import ShareGrant
from vaultforge.domain.sharing.enums import (
    SharePermission,
    ShareResourceType,
    ShareStatus,
    ShareTargetType,
)
from vaultforge.infrastructure.persistence.base import Base
from vaultforge.infrastructure.persistence.models.share import ShareGrantModel  # noqa: F401
from vaultforge.infrastructure.persistence.repositories.share_repository import (
    SqlAlchemyShareGrantRepository,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_INTEGRATION") != "1",
    reason="Set RUN_LIVE_INTEGRATION=1 with Postgres available",
)


@pytest_asyncio.fixture
async def share_db_session() -> AsyncIterator[AsyncSession]:
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
async def test_share_grant_create_revoke_and_expiry_persist(
    share_db_session: AsyncSession,
) -> None:
    repository = SqlAlchemyShareGrantRepository(share_db_session)
    organization_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    target_id = uuid.uuid4()
    now = utc_now()

    created = await repository.add(
        ShareGrant(
            organization_id=organization_id,
            resource_type=ShareResourceType.DOCUMENT,
            resource_id=uuid.uuid4(),
            target_type=ShareTargetType.USER,
            target_id=target_id,
            permission=SharePermission.EDIT,
            granted_by=actor_id,
            expires_at=now + timedelta(days=7),
        )
    )
    await share_db_session.commit()

    persisted = await repository.get_by_id(organization_id, created.id)
    assert persisted is not None
    assert persisted.is_active(at=now)
    assert persisted.permission == SharePermission.EDIT

    revoker_id = uuid.uuid4()
    persisted.revoke(revoker_id)
    await repository.update(persisted)
    await share_db_session.commit()

    revoked = await repository.get_by_id(organization_id, created.id)
    assert revoked is not None
    assert revoked.status == ShareStatus.REVOKED
    assert revoked.revoked_by == revoker_id
    assert not revoked.is_active(at=now)

    expired = await repository.add(
        ShareGrant(
            organization_id=organization_id,
            resource_type=ShareResourceType.DOCUMENT,
            resource_id=uuid.uuid4(),
            target_type=ShareTargetType.USER,
            target_id=uuid.uuid4(),
            granted_by=actor_id,
            expires_at=now - timedelta(seconds=1),
        )
    )
    await share_db_session.commit()

    persisted_expired = await repository.get_by_id(organization_id, expired.id)
    assert persisted_expired is not None
    assert persisted_expired.status == ShareStatus.ACTIVE
    assert not persisted_expired.is_active(at=now)
