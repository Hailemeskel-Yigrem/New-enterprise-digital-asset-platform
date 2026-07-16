"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the VaultForge API and workers."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "VaultForge"
    app_env: str = "development"
    app_debug: bool = False
    app_secret_key: str = Field(..., min_length=16)
    app_api_prefix: str = "/api/v1"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = Field(
        default="postgresql+asyncpg://vaultforge:vaultforge@localhost:5432/vaultforge"
    )
    redis_url: str = "redis://localhost:6379/0"

    celery_broker_url: str = "amqp://vaultforge:vaultforge@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/1"

    jwt_secret_key: str = Field(..., min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 14

    storage_backend: str = "local"
    storage_local_path: str = "./storage"
    storage_max_upload_mb: int = 100

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:3000"])

    oauth_issuer_base: str = "http://localhost:8000"
    oauth_default_client_id: str = "vaultforge-web"
    oauth_default_client_secret: str = "vaultforge-web-secret"
    oauth_redirect_uris: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000/oauth/callback"]
    )
    oauth_google_client_id: str = ""
    oauth_google_client_secret: str | None = None
    oauth_google_redirect_uris: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000/oauth/google/callback"]
    )

    rate_limit_enabled: bool = True
    rate_limit_global_requests: int = 300
    rate_limit_global_window: int = 60
    rate_limit_auth_requests: int = 20
    rate_limit_auth_window: int = 60
    rate_limit_oauth_requests: int = 30
    rate_limit_oauth_window: int = 60
    rate_limit_export_requests: int = 5
    rate_limit_export_window: int = 300

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("oauth_redirect_uris", "oauth_google_redirect_uris", mode="before")
    @classmethod
    def split_oauth_uris(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.storage_max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


def validate_production_secrets(settings: Settings) -> None:
    """Fail fast when production is configured with weak secrets."""
    if not settings.is_production:
        return
    weak = ("change-me", "secret", "password")
    for value in (settings.app_secret_key, settings.jwt_secret_key):
        lowered = value.lower()
        if any(token in lowered for token in weak) or len(value) < 32:
            raise ValueError("Production secrets must be strong random values (32+ chars)")


def clear_settings_cache() -> None:
    get_settings.cache_clear()

