"""Unit tests for optional error-tracking integration."""

from __future__ import annotations

import pytest

from vaultforge.core import error_tracking


def test_init_error_tracking_disabled_without_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(error_tracking, "_initialized", False)
    monkeypatch.setattr(error_tracking, "_sentry_available", False)
    assert error_tracking.init_error_tracking(dsn=None, environment="test") is False
    assert error_tracking.is_error_tracking_enabled() is False


def test_capture_exception_without_sentry_does_not_raise() -> None:
    error_tracking._initialized = True
    error_tracking._sentry_available = False
    error_tracking.capture_exception(RuntimeError("boom"), path="/x")
