"""Background Celery tasks for VaultForge."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from vaultforge.core.config import get_settings
from vaultforge.core.logging import get_logger
from vaultforge.domain.common import utc_now
from vaultforge.infrastructure.messaging.celery_app import celery_app
from vaultforge.infrastructure.persistence.models.audit import AuditEventModel
from vaultforge.infrastructure.persistence.models.collaboration import NotificationModel
from vaultforge.infrastructure.persistence.models.document import DocumentLockModel, DocumentModel

log = get_logger(__name__)


def _run_async(coro: Any) -> Any:
    return asyncio.run(coro)


async def _with_session(callback: Any) -> Any:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            result = await callback(session)
            await session.commit()
            return result
    finally:
        await engine.dispose()


@celery_app.task(name="vaultforge.infrastructure.messaging.tasks.send_notification_email")
def send_notification_email(
    notification_id: str,
    user_email: str,
    *,
    subject: str | None = None,
) -> dict[str, str]:
    """Deliver a notification via email (stub logs in development)."""
    log.info(
        "send_notification_email",
        notification_id=notification_id,
        user_email=user_email,
        subject=subject or "VaultForge notification",
    )
    return {
        "status": "queued",
        "notification_id": notification_id,
        "recipient": user_email,
    }


@celery_app.task(name="vaultforge.infrastructure.messaging.tasks.process_preview")
def process_preview(document_id: str, version_id: str) -> dict[str, str]:
    """Generate a document preview artifact asynchronously."""

    async def _process(session: AsyncSession) -> dict[str, str]:
        log.info("process_preview_started", document_id=document_id, version_id=version_id)
        return {
            "status": "completed",
            "document_id": document_id,
            "version_id": version_id,
            "preview_key": f"previews/{document_id}/{version_id}.png",
        }

    return _run_async(_with_session(_process))


@celery_app.task(name="vaultforge.infrastructure.messaging.tasks.expire_locks")
def expire_locks() -> dict[str, int]:
    """Remove document checkout locks that have passed their expiry time."""

    async def _expire(session: AsyncSession) -> dict[str, int]:
        now = utc_now()
        stmt = select(DocumentLockModel).where(
            DocumentLockModel.expires_at.is_not(None),
            DocumentLockModel.expires_at <= now,
        )
        result = await session.execute(stmt)
        locks = list(result.scalars().all())
        for lock in locks:
            await session.delete(lock)
        log.info("expire_locks_completed", removed=len(locks))
        return {"removed": len(locks)}

    return _run_async(_with_session(_expire))


@celery_app.task(name="vaultforge.infrastructure.messaging.tasks.nightly_stats")
def nightly_stats(organization_id: str | None = None) -> dict[str, Any]:
    """Aggregate nightly platform statistics for reporting."""

    async def _stats(session: AsyncSession) -> dict[str, Any]:
        org_filter = []
        if organization_id is not None:
            org_uuid = uuid.UUID(organization_id)
            org_filter = [DocumentModel.organization_id == org_uuid]

        document_count_stmt = select(func.count()).select_from(DocumentModel)
        if org_filter:
            document_count_stmt = document_count_stmt.where(*org_filter)
        document_count = (await session.execute(document_count_stmt)).scalar_one()

        notification_stmt = select(func.count()).select_from(NotificationModel)
        if organization_id is not None:
            notification_stmt = notification_stmt.where(
                NotificationModel.organization_id == uuid.UUID(organization_id)
            )
        notification_count = (await session.execute(notification_stmt)).scalar_one()

        audit_stmt = select(func.count()).select_from(AuditEventModel)
        if organization_id is not None:
            audit_stmt = audit_stmt.where(
                AuditEventModel.organization_id == uuid.UUID(organization_id)
            )
        audit_count = (await session.execute(audit_stmt)).scalar_one()

        generated_at = datetime.now(timezone.utc).isoformat()
        stats = {
            "generated_at": generated_at,
            "organization_id": organization_id,
            "documents": document_count,
            "notifications": notification_count,
            "audit_events": audit_count,
        }
        log.info("nightly_stats_completed", **stats)
        return stats

    return _run_async(_with_session(_stats))
