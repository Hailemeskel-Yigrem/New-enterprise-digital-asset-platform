"""Repository interfaces for digital signatures."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Sequence

from vaultforge.domain.signatures.entities import SignatureRequest, Signer


class SignatureRequestRepository(ABC):
    @abstractmethod
    async def get_by_id(
        self, organization_id: uuid.UUID, request_id: uuid.UUID
    ) -> SignatureRequest | None: ...

    @abstractmethod
    async def add(self, request: SignatureRequest) -> SignatureRequest: ...

    @abstractmethod
    async def update(self, request: SignatureRequest) -> SignatureRequest: ...

    @abstractmethod
    async def list_for_document(
        self, organization_id: uuid.UUID, document_id: uuid.UUID
    ) -> Sequence[SignatureRequest]: ...


class SignerRepository(ABC):
    @abstractmethod
    async def list_for_request(self, request_id: uuid.UUID) -> Sequence[Signer]: ...

    @abstractmethod
    async def add_many(self, signers: Sequence[Signer]) -> Sequence[Signer]: ...

    @abstractmethod
    async def update(self, signer: Signer) -> Signer: ...
