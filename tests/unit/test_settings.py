"""Settings parsing tests."""

from __future__ import annotations

from vaultforge.core.config import Settings


def test_cors_origins_split_from_csv(monkeypatch) -> None:
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret-key-32chars-minimum!!")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key-32chars-min!!")
    monkeypatch.setenv("CORS_ORIGINS", "http://a.local, http://b.local")
    settings = Settings()  # type: ignore[call-arg]
    assert settings.cors_origins == ["http://a.local", "http://b.local"]
