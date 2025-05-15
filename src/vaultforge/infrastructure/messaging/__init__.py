"""Celery messaging infrastructure."""

from __future__ import annotations

from celery import Celery

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
                "schedule": 86400.0,
            },
        },
    )
    return app


celery_app = create_celery_app()
