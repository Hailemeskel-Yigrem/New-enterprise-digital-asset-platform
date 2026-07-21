"""S3-compatible storage backend with optional boto3."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import cast

from vaultforge.core.exceptions import NotFoundError, ValidationError

try:
    import boto3
    from botocore.exceptions import ClientError

    _BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    ClientError = Exception
    _BOTO3_AVAILABLE = False


@dataclass(frozen=True, slots=True)
class S3StorageConfig:
    bucket: str
    region: str = "us-east-1"
    endpoint_url: str | None = None
    access_key_id: str | None = None
    secret_access_key: str | None = None
    prefix: str = ""

    def __post_init__(self) -> None:
        if not self.bucket.strip():
            raise ValidationError("S3 bucket is required")


class S3StorageBackend:
    """Async wrapper around boto3 S3 client."""

    def __init__(self, config: S3StorageConfig) -> None:
        self._config = config
        if not _BOTO3_AVAILABLE:
            raise RuntimeError("boto3 is not installed. Install with: pip install boto3")
        session_kwargs: dict[str, str] = {"region_name": config.region}
        if config.access_key_id and config.secret_access_key:
            session_kwargs["aws_access_key_id"] = config.access_key_id
            session_kwargs["aws_secret_access_key"] = config.secret_access_key
        self._client = boto3.client("s3", endpoint_url=config.endpoint_url, **session_kwargs)

    def _full_key(self, key: str) -> str:
        normalized = key.lstrip("/")
        if ".." in normalized.split("/"):
            raise ValidationError("Invalid storage key")
        prefix = self._config.prefix.strip("/")
        return f"{prefix}/{normalized}" if prefix else normalized

    async def put(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> None:
        full_key = self._full_key(key)

        def _upload() -> None:
            self._client.put_object(
                Bucket=self._config.bucket,
                Key=full_key,
                Body=data,
                ContentType=content_type,
            )

        await asyncio.to_thread(_upload)

    async def get(self, key: str) -> bytes:
        full_key = self._full_key(key)

        def _download() -> bytes:
            try:
                response = self._client.get_object(Bucket=self._config.bucket, Key=full_key)
                return cast(bytes, response["Body"].read())
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code in ("NoSuchKey", "404"):
                    raise NotFoundError(f"S3 object not found: {key}") from exc
                raise

        return await asyncio.to_thread(_download)

    async def delete(self, key: str) -> None:
        full_key = self._full_key(key)

        def _delete() -> None:
            self._client.delete_object(Bucket=self._config.bucket, Key=full_key)

        await asyncio.to_thread(_delete)

    async def exists(self, key: str) -> bool:
        full_key = self._full_key(key)

        def _head() -> bool:
            try:
                self._client.head_object(Bucket=self._config.bucket, Key=full_key)
                return True
            except ClientError:
                return False

        return await asyncio.to_thread(_head)


class InMemoryS3Fallback:
    """Fallback when boto3 unavailable - for tests/dev."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def put(
        self, key: str, data: bytes, *, content_type: str = "application/octet-stream"
    ) -> None:
        del content_type
        self._objects[key] = data

    async def get(self, key: str) -> bytes:
        if key not in self._objects:
            raise NotFoundError(f"Object not found: {key}")
        return self._objects[key]

    async def delete(self, key: str) -> None:
        self._objects.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self._objects


def create_s3_backend(config: S3StorageConfig) -> S3StorageBackend | InMemoryS3Fallback:
    if _BOTO3_AVAILABLE:
        return S3StorageBackend(config)
    return InMemoryS3Fallback()
