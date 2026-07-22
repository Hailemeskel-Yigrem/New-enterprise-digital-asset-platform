"""Unit tests for signature hash binding."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from vaultforge.core.exceptions import ConflictError
from vaultforge.domain.signatures.entities import (
    SignatureRequest,
    Signer,
    compute_signature_hash,
)
from vaultforge.domain.signatures.enums import SignatureRequestStatus, SignerStatus


def test_compute_signature_hash_is_deterministic() -> None:
    checksum = "abc123" * 10 + "abcd"
    signer_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    signed_at = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)

    first = compute_signature_hash(checksum, signer_id, signed_at)
    second = compute_signature_hash(checksum, signer_id, signed_at)
    assert first == second
    assert len(first) == 64


def test_compute_signature_hash_changes_with_checksum() -> None:
    signer_id = uuid.uuid4()
    signed_at = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    first = compute_signature_hash("checksum-a", signer_id, signed_at)
    second = compute_signature_hash("checksum-b", signer_id, signed_at)
    assert first != second


def test_signer_sign_binds_document_checksum() -> None:
    signer = Signer(user_id=uuid.uuid4())
    checksum = "deadbeef" * 8
    signature_hash = signer.sign(checksum)

    assert signer.status == SignerStatus.SIGNED
    assert signer.signature_hash == signature_hash
    assert signer.signed_at is not None


def test_signature_request_requires_sequential_signing() -> None:
    first_user = uuid.uuid4()
    second_user = uuid.uuid4()
    request = SignatureRequest(
        document_checksum="checksum-value",
        signers=[
            Signer(user_id=first_user, order=1),
            Signer(user_id=second_user, order=2),
        ],
    )

    with pytest.raises(ConflictError, match="sign in order"):
        request.sign_as(second_user)

    request.sign_as(first_user)
    assert request.status == SignatureRequestStatus.PARTIALLY_SIGNED

    request.sign_as(second_user)
    assert request.status == SignatureRequestStatus.COMPLETED
