"""Optional error-tracking integration (Sentry when SENTRY_DSN is configured)."""

from __future__ import annotations

from typing import Any

from vaultforge.core.logging import get_logger

log = get_logger("vaultforge.error_tracking")

_initialized = False
_sentry_available = False


def init_error_tracking(*, dsn: str | None, environment: str, release: str | None = None) -> bool:
    """Initialize Sentry when a DSN is present. Returns True if tracking is active."""
    global _initialized, _sentry_available
    if _initialized:
        return _sentry_available
    _initialized = True

    if not dsn:
        log.info("error_tracking_disabled", reason="SENTRY_DSN not set")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        log.warning("error_tracking_unavailable", reason="sentry-sdk not installed")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=0.1 if environment == "production" else 0.0,
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(level=None, event_level=None),
        ],
    )
    _sentry_available = True
    log.info("error_tracking_enabled", provider="sentry", environment=environment)
    return True


def capture_exception(exc: BaseException, **context: Any) -> None:
    """Report an exception to the configured error tracker (no-op when disabled)."""
    if not _sentry_available:
        log.error(
            "captured_exception_locally",
            error=str(exc),
            error_type=type(exc).__name__,
            **context,
        )
        return

    import sentry_sdk

    with sentry_sdk.push_scope() as scope:
        for key, value in context.items():
            scope.set_extra(key, value)
        sentry_sdk.capture_exception(exc)


def is_error_tracking_enabled() -> bool:
    return _sentry_available
