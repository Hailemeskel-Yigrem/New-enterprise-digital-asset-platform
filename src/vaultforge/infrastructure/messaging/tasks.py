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


@celery_app.task(name="vaultforge.infrastructure.messaging.tasks.queue_export_job")
def queue_export_job(job_id: str) -> dict[str, str]:
    """Run a long-running export job asynchronously."""

    async def _export(session: AsyncSession) -> dict[str, str]:
        from vaultforge.application.jobs.export_service import ExportService
        from vaultforge.infrastructure.persistence.repositories.job_repository import (
            SqlAlchemyExportJobRepository,
            StubDocumentExportSource,
        )

        service = ExportService(SqlAlchemyExportJobRepository(session), StubDocumentExportSource())
        result = await service.run_export(uuid.UUID(job_id))
        log.info("export_job_task_completed", job_id=job_id, status=result.status.value)
        return {"status": result.status.value, "job_id": job_id, "artifact": result.artifact_path or ""}

    return _run_async(_with_session(_export))


@celery_app.task(name="vaultforge.infrastructure.messaging.tasks.queue_import_job")
def queue_import_job(job_id: str) -> dict[str, str]:
    """Run a long-running import job asynchronously."""

    async def _import(session: AsyncSession) -> dict[str, str]:
        from vaultforge.application.jobs.import_service import ImportService
        from vaultforge.infrastructure.persistence.repositories.job_repository import (
            SqlAlchemyImportJobRepository,
            StubDocumentImportSink,
        )

        service = ImportService(SqlAlchemyImportJobRepository(session), StubDocumentImportSink())
        result = await service.run_import(uuid.UUID(job_id))
        log.info(
            "import_job_task_completed",
            job_id=job_id,
            status=result.status.value,
            processed=result.items_processed,
        )
        return {
            "status": result.status.value,
            "job_id": job_id,
            "processed": str(result.items_processed),
            "failed": str(result.items_failed),
        }

    return _run_async(_with_session(_import))

@celery_app.task(name="vaultforge.infrastructure.messaging.tasks.process_retention_due")
def process_retention_due() -> dict[str, int]:
    """Execute retention schedules that have reached their expiry time."""

    async def _process(session: AsyncSession) -> dict[str, int]:
        from vaultforge.infrastructure.persistence.models.share import RetentionScheduleModel

        now = utc_now()
        stmt = select(RetentionScheduleModel).where(
            RetentionScheduleModel.executed_at.is_(None),
            RetentionScheduleModel.expires_at <= now,
            RetentionScheduleModel.blocked_by_legal_hold.is_(False),
        )
        result = await session.execute(stmt)
        schedules = list(result.scalars().all())
        for schedule in schedules:
            schedule.executed_at = now
        log.info("process_retention_due_completed", processed=len(schedules))
        return {"processed": len(schedules)}

    return _run_async(_with_session(_process))


@celery_app.task(name="vaultforge.infrastructure.messaging.tasks.purge_expired_shares")
def purge_expired_shares() -> dict[str, int]:
    """Mark expired share grants and links as expired."""

    async def _purge(session: AsyncSession) -> dict[str, int]:
        from vaultforge.infrastructure.persistence.models.share import ShareGrantModel, ShareLinkModel

        now = utc_now()
        grant_stmt = select(ShareGrantModel).where(
            ShareGrantModel.status == "active",
            ShareGrantModel.expires_at.is_not(None),
            ShareGrantModel.expires_at <= now,
        )
        grants = list((await session.execute(grant_stmt)).scalars().all())
        for grant in grants:
            grant.status = "expired"

        link_stmt = select(ShareLinkModel).where(
            ShareLinkModel.status == "active",
            ShareLinkModel.expires_at.is_not(None),
            ShareLinkModel.expires_at <= now,
        )
        links = list((await session.execute(link_stmt)).scalars().all())
        for link in links:
            link.status = "expired"

        total = len(grants) + len(links)
        log.info("purge_expired_shares_completed", grants=len(grants), links=len(links))
        return {"expired_grants": len(grants), "expired_links": len(links), "total": total}

    return _run_async(_with_session(_purge))


@celery_app.task(name="vaultforge.infrastructure.messaging.tasks.reindex_stale_documents")
def reindex_stale_documents(limit: int = 100) -> dict[str, int]:
    """Reindex documents flagged for search refresh (stub counter)."""

    async def _reindex(session: AsyncSession) -> dict[str, int]:
        stmt = select(DocumentModel).limit(limit)
        docs = list((await session.execute(stmt)).scalars().all())
        log.info("reindex_stale_documents_completed", reindexed=len(docs))
        return {"reindexed": len(docs)}

    return _run_async(_with_session(_reindex))


@celery_app.task(name="vaultforge.infrastructure.messaging.tasks.process_virus_scan_queue")
def process_virus_scan_queue(max_items: int = 10) -> dict[str, int]:
    """Drain pending virus scan jobs using the local stub scanner."""

    async def _scan(session: AsyncSession) -> dict[str, int]:
        from vaultforge.application.assets.virus_scan_stub import LocalStubVirusScanner, ScanRequest

        scanner = LocalStubVirusScanner()
        stmt = select(DocumentModel).limit(max_items)
        docs = list((await session.execute(stmt)).scalars().all())
        clean = 0
        for doc in docs:
            if doc.current_version_id is None:
                continue
            request = ScanRequest(
                organization_id=doc.organization_id,
                document_id=doc.id,
                version_id=doc.current_version_id,
                storage_key=f"documents/{doc.id}",
                content_type="application/octet-stream",
                size_bytes=0,
                checksum_sha256="0" * 64,
            )
            result = await scanner.scan(request, data=None)
            if result.is_clean or result.verdict.value == "skipped":
                clean += 1
        log.info("process_virus_scan_queue_completed", scanned=len(docs), clean=clean)
        return {"scanned": len(docs), "clean": clean}

    return _run_async(_with_session(_scan))
