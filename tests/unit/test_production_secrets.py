"""Production secret validation tests."""

import pytest

from vaultforge.core.config import Settings, validate_production_secrets


def test_dev_allows_weak_secrets(monkeypatch) -> None:
    monkeypatch.setenv("APP_SECRET_KEY", "change-me-in-production-use-a-long-random-string")
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me-jwt-secret-use-long-random-value")
    monkeypatch.setenv("APP_ENV", "development")
    settings = Settings()  # type: ignore[call-arg]
    validate_production_secrets(settings)


def test_prod_rejects_weak_secrets(monkeypatch) -> None:
    monkeypatch.setenv("APP_SECRET_KEY", "change-me-in-production-use-a-long-random-string")
    monkeypatch.setenv("JWT_SECRET_KEY", "change-me-jwt-secret-use-long-random-value")
    monkeypatch.setenv("APP_ENV", "production")
    settings = Settings()  # type: ignore[call-arg]
    with pytest.raises(ValueError):
        validate_production_secrets(settings)
