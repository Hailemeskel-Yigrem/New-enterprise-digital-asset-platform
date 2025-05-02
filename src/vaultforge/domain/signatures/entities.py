"""Digital signature aggregates."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from vaultforge.core.exceptions import AuthorizationError, ConflictError, ValidationError
from vaultforge.domain.common import Entity, utc_now
from vaultforge.domain.signatures.enums import SignatureRequestStatus, SignerStatus


def compute_signature_hash(
    document_checksum: str,
    signer_id: uuid.UUID,
    signed_at: datetime,
) -> str:
    """Bind a signature to a document version via deterministic hash."""
    payload = f"{document_checksum}:{signer_id}:{signed_at.isoformat()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class Signer(Entity):
    request_id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: uuid.UUID = field(default_factory=uuid.uuid4)
    order: int = 1
    status: SignerStatus = SignerStatus.PENDING
    signature_hash: str | None = None
    signed_at: datetime | None = None
    declined_at: datetime | None = None
    decline_reason: str = ""

    def sign(self, document_checksum: str) -> str:
        if self.status != SignerStatus.PENDING:
            raise ConflictError("Signer has already acted on this request")
        signed_at = utc_now()
        self.signature_hash = compute_signature_hash(document_checksum, self.user_id, signed_at)
        self.signed_at = signed_at
        self.status = SignerStatus.SIGNED
        self.touch()
        return self.signature_hash

    def decline(self, *, reason: str) -> None:
        if self.status != SignerStatus.PENDING:
            raise ConflictError("Signer has already acted on this request")
        if not reason.strip():
            raise ValidationError("Decline reason is required")
        self.status = SignerStatus.DECLINED
        self.declined_at = utc_now()
        self.decline_reason = reason.strip()
        self.touch()


@dataclass(slots=True)
class SignatureRequest(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    document_id: uuid.UUID = field(default_factory=uuid.uuid4)
    document_version_id: uuid.UUID = field(default_factory=uuid.uuid4)
    document_checksum: str = ""
    title: str = ""
    message: str = ""
    status: SignatureRequestStatus = SignatureRequestStatus.PENDING
    created_by: uuid.UUID = field(default_factory=uuid.uuid4)
    completed_at: datetime | None = None
    signers: list[Signer] = field(default_factory=list)

    def ordered_signers(self) -> list[Signer]:
        return sorted(self.signers, key=lambda item: item.order)

    def next_pending_signer(self) -> Signer | None:
        for signer in self.ordered_signers():
            if signer.status == SignerStatus.PENDING:
                return signer
        return None

    def sign_as(self, user_id: uuid.UUID) -> str:
        self._ensure_open()
        signer = self._find_signer(user_id)
        if signer is None:
            raise AuthorizationError("User is not a signer on this request")
        pending = self.next_pending_signer()
        if pending is None:
            raise ConflictError("All signers have already acted")
        if pending.user_id != user_id:
            raise ConflictError("Signers must sign in order")
        signature_hash = signer.sign(self.document_checksum)
        self._refresh_status()
        self.touch()
        return signature_hash

    def decline_as(self, user_id: uuid.UUID, *, reason: str) -> None:
        self._ensure_open()
        signer = self._find_signer(user_id)
        if signer is None:
            raise AuthorizationError("User is not a signer on this request")
        signer.decline(reason=reason)
        self.status = SignatureRequestStatus.DECLINED
        self.completed_at = utc_now()
        self.touch()

    def complete_if_ready(self) -> None:
        if all(signer.status == SignerStatus.SIGNED for signer in self.signers):
            self.status = SignatureRequestStatus.COMPLETED
            self.completed_at = utc_now()
            self.touch()

    def _refresh_status(self) -> None:
        signed_count = sum(1 for signer in self.signers if signer.status == SignerStatus.SIGNED)
        if signed_count == len(self.signers):
            self.status = SignatureRequestStatus.COMPLETED
            self.completed_at = utc_now()
        elif signed_count > 0:
            self.status = SignatureRequestStatus.PARTIALLY_SIGNED

    def _find_signer(self, user_id: uuid.UUID) -> Signer | None:
        for signer in self.signers:
            if signer.user_id == user_id:
                return signer
        return None

    def _ensure_open(self) -> None:
        if self.status in {
            SignatureRequestStatus.COMPLETED,
            SignatureRequestStatus.DECLINED,
            SignatureRequestStatus.CANCELLED,
            SignatureRequestStatus.EXPIRED,
        }:
            raise ConflictError("Signature request is closed")
