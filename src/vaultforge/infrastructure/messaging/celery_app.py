"""Celery application instance and beat schedule."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from vaultforge.core.config import get_settings


def create_celery_app() -> Celery:
    settings = get_settings()
    app = Celery(
        "vaultforge",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=["vaultforge.infrastructure.messaging.tasks"],
    )
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        worker_prefetch_multiplier=1,
        beat_schedule={
            "expire-document-locks": {
                "task": "vaultforge.infrastructure.messaging.tasks.expire_locks",
                "schedule": 300.0,
            },
            "nightly-stats": {
                "task": "vaultforge.infrastructure.messaging.tasks.nightly_stats",
                "schedule": crontab(hour=2, minute=0),
            },
            "process-retention-schedules": {
                "task": "vaultforge.infrastructure.messaging.tasks.process_retention_due",
                "schedule": 3600.0,
            },
            "purge-expired-shares": {
                "task": "vaultforge.infrastructure.messaging.tasks.purge_expired_shares",
                "schedule": 1800.0,
            },
            "reindex-search-stale": {
                "task": "vaultforge.infrastructure.messaging.tasks.reindex_stale_documents",
                "schedule": 7200.0,
            },
            "scan-quarantine-queue": {
                "task": "vaultforge.infrastructure.messaging.tasks.process_virus_scan_queue",
                "schedule": 120.0,
            },
            "digest-notification-email": {
                "task": "vaultforge.infrastructure.messaging.tasks.send_notification_email",
                "schedule": crontab(hour=8, minute=0),
                "kwargs": {"digest": True},
            },
            "weekly-export-cleanup": {
                "task": "vaultforge.infrastructure.messaging.tasks.queue_export_job",
                "schedule": crontab(day_of_week=0, hour=3, minute=30),
                "kwargs": {"cleanup_stale": True},
            },
        },
    )
    return app


celery_app = create_celery_app()
