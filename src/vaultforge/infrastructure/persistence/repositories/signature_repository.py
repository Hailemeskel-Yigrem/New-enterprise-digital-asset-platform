"""SQLAlchemy signature repositories."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vaultforge.domain.signatures.entities import SignatureRequest, Signer
from vaultforge.domain.signatures.enums import SignatureRequestStatus, SignerStatus
from vaultforge.domain.signatures.repositories import SignatureRequestRepository, SignerRepository
from vaultforge.infrastructure.persistence.models.signature import SignerModel, SignatureRequestModel


def _request_to_entity(model: SignatureRequestModel) -> SignatureRequest:
    return SignatureRequest(
        id=model.id,
        organization_id=model.organization_id,
        document_id=model.document_id,
        document_version_id=model.document_version_id,
        document_checksum=model.document_checksum,
        title=model.title,
        message=model.message,
        status=SignatureRequestStatus(model.status),
        created_by=model.created_by,
        completed_at=model.completed_at,
        signers=[_signer_to_entity(signer) for signer in model.signers],
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_request(model: SignatureRequestModel, request: SignatureRequest) -> None:
    model.document_id = request.document_id
    model.document_version_id = request.document_version_id
    model.document_checksum = request.document_checksum
    model.title = request.title
    model.message = request.message
    model.status = request.status.value
    model.completed_at = request.completed_at
    model.updated_at = request.updated_at


def _signer_to_entity(model: SignerModel) -> Signer:
    return Signer(
        id=model.id,
        request_id=model.request_id,
        user_id=model.user_id,
        order=model.order,
        status=SignerStatus(model.status),
        signature_hash=model.signature_hash,
        signed_at=model.signed_at,
        declined_at=model.declined_at,
        decline_reason=model.decline_reason,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_signer(model: SignerModel, signer: Signer) -> None:
    model.status = signer.status.value
    model.signature_hash = signer.signature_hash
    model.signed_at = signer.signed_at
    model.declined_at = signer.declined_at
    model.decline_reason = signer.decline_reason
    model.updated_at = signer.updated_at


class SqlAlchemySignatureRequestRepository(SignatureRequestRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, organization_id: uuid.UUID, request_id: uuid.UUID
    ) -> SignatureRequest | None:
        stmt = (
            select(SignatureRequestModel)
            .where(
                SignatureRequestModel.id == request_id,
                SignatureRequestModel.organization_id == organization_id,
            )
            .options(selectinload(SignatureRequestModel.signers))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _request_to_entity(model) if model else None

    async def add(self, request: SignatureRequest) -> SignatureRequest:
        model = SignatureRequestModel(
            id=request.id,
            organization_id=request.organization_id,
            document_id=request.document_id,
            document_version_id=request.document_version_id,
            document_checksum=request.document_checksum,
            title=request.title,
            message=request.message,
            status=request.status.value,
            created_by=request.created_by,
            completed_at=request.completed_at,
            created_at=request.created_at,
            updated_at=request.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _request_to_entity(model)

    async def update(self, request: SignatureRequest) -> SignatureRequest:
        model = await self._session.get(SignatureRequestModel, request.id)
        if model is None:
            raise ValueError("Signature request not found")
        _apply_request(model, request)
        await self._session.flush()
        return _request_to_entity(model)

    async def list_for_document(
        self, organization_id: uuid.UUID, document_id: uuid.UUID
    ) -> list[SignatureRequest]:
        stmt = (
            select(SignatureRequestModel)
            .where(
                SignatureRequestModel.organization_id == organization_id,
                SignatureRequestModel.document_id == document_id,
            )
            .options(selectinload(SignatureRequestModel.signers))
            .order_by(SignatureRequestModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [_request_to_entity(model) for model in result.scalars().all()]


class SqlAlchemySignerRepository(SignerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_request(self, request_id: uuid.UUID) -> list[Signer]:
        stmt = (
            select(SignerModel)
            .where(SignerModel.request_id == request_id)
            .order_by(SignerModel.order)
        )
        result = await self._session.execute(stmt)
        return [_signer_to_entity(model) for model in result.scalars().all()]

    async def add_many(self, signers: list[Signer]) -> list[Signer]:
        models = [
            SignerModel(
                id=signer.id,
                request_id=signer.request_id,
                user_id=signer.user_id,
                order=signer.order,
                status=signer.status.value,
                signature_hash=signer.signature_hash,
                signed_at=signer.signed_at,
                declined_at=signer.declined_at,
                decline_reason=signer.decline_reason,
                created_at=signer.created_at,
                updated_at=signer.updated_at,
            )
            for signer in signers
        ]
        self._session.add_all(models)
        await self._session.flush()
        return [_signer_to_entity(model) for model in models]

    async def update(self, signer: Signer) -> Signer:
        model = await self._session.get(SignerModel, signer.id)
        if model is None:
            raise ValueError("Signer not found")
        _apply_signer(model, signer)
        await self._session.flush()
        return _signer_to_entity(model)
