"""Digital signature application service."""

from __future__ import annotations

import uuid

from vaultforge.application.signatures.schemas import (
    SignatureRequestCreateRequest,
    SignatureRequestResponse,
    SignDocumentResponse,
    SignerResponse,
)
from vaultforge.core.exceptions import NotFoundError, ValidationError
from vaultforge.domain.assets.repositories import DocumentRepository, DocumentVersionRepository
from vaultforge.domain.signatures.entities import SignatureRequest, Signer
from vaultforge.domain.signatures.enums import SignatureRequestStatus
from vaultforge.domain.signatures.repositories import SignatureRequestRepository, SignerRepository


class SignatureService:
    def __init__(
        self,
        request_repo: SignatureRequestRepository,
        signer_repo: SignerRepository,
        document_repo: DocumentRepository,
        version_repo: DocumentVersionRepository,
    ) -> None:
        self._requests = request_repo
        self._signers = signer_repo
        self._documents = document_repo
        self._versions = version_repo

    async def create_request(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: SignatureRequestCreateRequest,
    ) -> SignatureRequestResponse:
        document = await self._documents.get_by_id(organization_id, payload.document_id)
        if document is None:
            raise NotFoundError("Document not found")

        version = await self._versions.get_by_id(payload.document_version_id)
        if version is None or version.document_id != payload.document_id:
            raise NotFoundError("Document version not found")

        orders = [signer.order for signer in payload.signers]
        if len(orders) != len(set(orders)):
            raise ValidationError("Signer orders must be unique")

        request = SignatureRequest(
            organization_id=organization_id,
            document_id=payload.document_id,
            document_version_id=payload.document_version_id,
            document_checksum=version.checksum_sha256,
            title=payload.title.strip(),
            message=payload.message.strip(),
            status=SignatureRequestStatus.PENDING,
            created_by=user_id,
        )
        saved_request = await self._requests.add(request)

        signers = [
            Signer(
                request_id=saved_request.id,
                user_id=definition.user_id,
                order=definition.order,
            )
            for definition in sorted(payload.signers, key=lambda item: item.order)
        ]
        saved_signers = list(await self._signers.add_many(signers))
        saved_request.signers = saved_signers
        return self._to_response(saved_request)

    async def sign(
        self,
        organization_id: uuid.UUID,
        request_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> SignDocumentResponse:
        request = await self._require_request(organization_id, request_id)
        signature_hash = request.sign_as(user_id)
        request.complete_if_ready()
        await self._persist_request(request)
        return SignDocumentResponse(
            request_id=request.id,
            signature_hash=signature_hash,
            status=request.status,
        )

    async def decline(
        self,
        organization_id: uuid.UUID,
        request_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        reason: str,
    ) -> SignatureRequestResponse:
        request = await self._require_request(organization_id, request_id)
        request.decline_as(user_id, reason=reason)
        await self._persist_request(request)
        return self._to_response(request)

    async def complete(
        self,
        organization_id: uuid.UUID,
        request_id: uuid.UUID,
    ) -> SignatureRequestResponse:
        request = await self._require_request(organization_id, request_id)
        request.complete_if_ready()
        if request.status != SignatureRequestStatus.COMPLETED:
            raise ValidationError("Signature request is not fully signed")
        await self._persist_request(request)
        return self._to_response(request)

    async def get_request(
        self,
        organization_id: uuid.UUID,
        request_id: uuid.UUID,
    ) -> SignatureRequestResponse:
        request = await self._require_request(organization_id, request_id)
        return self._to_response(request)

    async def list_for_document(
        self,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> list[SignatureRequestResponse]:
        requests = await self._requests.list_for_document(organization_id, document_id)
        responses: list[SignatureRequestResponse] = []
        for request in requests:
            request.signers = list(await self._signers.list_for_request(request.id))
            responses.append(self._to_response(request))
        return responses

    async def _require_request(
        self, organization_id: uuid.UUID, request_id: uuid.UUID
    ) -> SignatureRequest:
        request = await self._requests.get_by_id(organization_id, request_id)
        if request is None:
            raise NotFoundError("Signature request not found")
        request.signers = list(await self._signers.list_for_request(request.id))
        return request

    async def _persist_request(self, request: SignatureRequest) -> None:
        await self._requests.update(request)
        for signer in request.signers:
            await self._signers.update(signer)

    def _to_response(self, request: SignatureRequest) -> SignatureRequestResponse:
        return SignatureRequestResponse(
            id=request.id,
            organization_id=request.organization_id,
            document_id=request.document_id,
            document_version_id=request.document_version_id,
            document_checksum=request.document_checksum,
            title=request.title,
            message=request.message,
            status=request.status,
            created_by=request.created_by,
            completed_at=request.completed_at,
            signers=[SignerResponse.model_validate(signer) for signer in request.ordered_signers()],
            created_at=request.created_at,
            updated_at=request.updated_at,
        )
