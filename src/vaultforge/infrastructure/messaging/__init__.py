"""Celery messaging infrastructure."""

from vaultforge.infrastructure.messaging.celery_app import celery_app, create_celery_app

__all__ = ["celery_app", "create_celery_app"]
