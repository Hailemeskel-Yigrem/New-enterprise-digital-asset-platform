"""Virus scanning interface and local development stub."""

from __future__ import annotations

import hashlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum

from vaultforge.core.logging import get_logger

log = get_logger(__name__)


class ScanVerdict(StrEnum):
    CLEAN = "clean"
    INFECTED = "infected"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(slots=True)
class ScanRequest:
    organization_id: uuid.UUID
    document_id: uuid.UUID
    version_id: uuid.UUID
    storage_key: str
    content_type: str
    size_bytes: int
    checksum_sha256: str


@dataclass(slots=True)
class ScanResult:
    verdict: ScanVerdict
    scanner: str
    scanned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    threat_name: str | None = None
    detail: str = ""
    duration_ms: int = 0

    @property
    def is_clean(self) -> bool:
        return self.verdict == ScanVerdict.CLEAN

    @property
    def blocked(self) -> bool:
        return self.verdict == ScanVerdict.INFECTED


class VirusScanner(ABC):
    """Abstract virus scanner used before persisting uploaded binaries."""

    @abstractmethod
    async def scan(self, request: ScanRequest, *, data: bytes | None = None) -> ScanResult:
        raise NotImplementedError


class LocalStubVirusScanner(VirusScanner):
    """Development stub that flags EICAR test strings and logs all scans."""

    SCANNER_NAME = "local-stub"

    INFECTED_MARKERS = (
        b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE",
        b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR",
    )

    async def scan(self, request: ScanRequest, *, data: bytes | None = None) -> ScanResult:
        started = datetime.now(timezone.utc)
        log.info(
            "virus_scan_started",
            document_id=str(request.document_id),
            version_id=str(request.version_id),
            size_bytes=request.size_bytes,
        )

        if data is None:
            return ScanResult(
                verdict=ScanVerdict.SKIPPED,
                scanner=self.SCANNER_NAME,
                detail="No payload provided; checksum-only validation",
                duration_ms=0,
            )

        for marker in self.INFECTED_MARKERS:
            if marker in data:
                duration = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
                log.warning(
                    "virus_scan_infected",
                    document_id=str(request.document_id),
                    marker=marker.decode("ascii", errors="replace")[:32],
                )
                return ScanResult(
                    verdict=ScanVerdict.INFECTED,
                    scanner=self.SCANNER_NAME,
                    threat_name="EICAR-Test-File",
                    detail="Test virus signature detected",
                    duration_ms=duration,
                )

        digest = hashlib.sha256(data).hexdigest()
        if digest != request.checksum_sha256:
            duration = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
            return ScanResult(
                verdict=ScanVerdict.ERROR,
                scanner=self.SCANNER_NAME,
                detail="Checksum mismatch during scan",
                duration_ms=duration,
            )

        duration = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        log.info(
            "virus_scan_clean",
            document_id=str(request.document_id),
            duration_ms=duration,
        )
        return ScanResult(
            verdict=ScanVerdict.CLEAN,
            scanner=self.SCANNER_NAME,
            duration_ms=duration,
        )


def get_default_scanner() -> VirusScanner:
    """Return the configured scanner implementation."""
    return LocalStubVirusScanner()

@dataclass(slots=True)
class QueuedScan:
    request: ScanRequest
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ScanQueue:
    """In-memory scan queue used by the local stub and integration tests."""

    def __init__(self) -> None:
        self._pending: list[QueuedScan] = []

    def enqueue(self, request: ScanRequest) -> None:
        self._pending.append(QueuedScan(request=request))
        log.info("virus_scan_enqueued", version_id=str(request.version_id))

    def pop_next(self) -> QueuedScan | None:
        if not self._pending:
            return None
        return self._pending.pop(0)

    @property
    def depth(self) -> int:
        return len(self._pending)


class QueuedStubVirusScanner(LocalStubVirusScanner):
    """Scanner that records requests in a queue before processing."""

    def __init__(self, queue: ScanQueue | None = None) -> None:
        self._queue = queue or ScanQueue()

    @property
    def queue(self) -> ScanQueue:
        return self._queue

    async def scan(self, request: ScanRequest, *, data: bytes | None = None) -> ScanResult:
        self._queue.enqueue(request)
        return await super().scan(request, data=data)


def get_scanner_with_queue() -> QueuedStubVirusScanner:
    return QueuedStubVirusScanner()

class NoOpVirusScanner(VirusScanner):
    """Scanner that always returns clean — used in trusted upload pipelines."""

    SCANNER_NAME = "noop"

    async def scan(self, request: ScanRequest, *, data: bytes | None = None) -> ScanResult:
        return ScanResult(
            verdict=ScanVerdict.SKIPPED,
            scanner=self.SCANNER_NAME,
            detail="Scanning disabled by configuration",
        )


class FailClosedVirusScanner(VirusScanner):
    """Scanner that rejects uploads when payload is missing (fail-closed mode)."""

    SCANNER_NAME = "fail-closed"

    async def scan(self, request: ScanRequest, *, data: bytes | None = None) -> ScanResult:
        if data is None:
            return ScanResult(
                verdict=ScanVerdict.ERROR,
                scanner=self.SCANNER_NAME,
                detail="Payload required in fail-closed mode",
            )
        return ScanResult(verdict=ScanVerdict.CLEAN, scanner=self.SCANNER_NAME)


def select_scanner(mode: str = "stub") -> VirusScanner:
    """Factory for scanner implementations based on deployment mode."""
    if mode == "noop":
        return NoOpVirusScanner()
    if mode == "fail-closed":
        return FailClosedVirusScanner()
    if mode == "queued-stub":
        return get_scanner_with_queue()
    return get_default_scanner()
