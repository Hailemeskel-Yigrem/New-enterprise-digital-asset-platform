"""Unit tests for entity/model mappers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vaultforge.domain.assets.entities import DocumentLock, DocumentVersion, Folder
from vaultforge.domain.assets.enums import (
    FolderKind,
    VersionStatus,
)
from vaultforge.domain.identity.entities import Membership, Organization, User
from vaultforge.domain.identity.enums import MembershipStatus, OrgRole
from vaultforge.infrastructure.persistence.mappers.assets import (
    document_lock_from_model,
    document_lock_to_model,
    document_version_from_model,
    document_version_to_model,
    folder_from_model,
    folder_to_model,
    folders_from_models,
)
from vaultforge.infrastructure.persistence.mappers.identity import (
    membership_from_model,
    membership_to_model,
    organization_from_model,
    organization_to_model,
    user_from_model,
    user_to_model,
    users_from_models,
)
from vaultforge.infrastructure.persistence.models.document import (
    DocumentLockModel,
    DocumentVersionModel,
)
from vaultforge.infrastructure.persistence.models.folder import FolderModel
from vaultforge.infrastructure.persistence.models.membership import MembershipModel

NOW = datetime(2025, 9, 25, tzinfo=UTC)


def test_user_round_trip() -> None:
    entity = User(
        id=uuid.uuid4(),
        email="mapper@test.io",
        full_name="Mapper Test",
        password_hash="hash",
        created_at=NOW,
        updated_at=NOW,
    )
    model = user_to_model(entity)
    restored = user_from_model(model)
    assert restored.email == entity.email
    assert restored.full_name == entity.full_name


def test_organization_round_trip() -> None:
    entity = Organization(
        id=uuid.uuid4(),
        name="Acme",
        slug="acme",
        plan_code="enterprise",
        max_storage_gb=500,
        created_at=NOW,
        updated_at=NOW,
    )
    restored = organization_from_model(organization_to_model(entity))
    assert restored.slug == "acme"
    assert restored.max_storage_gb == 500


def test_membership_round_trip() -> None:
    entity = Membership(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=OrgRole.MANAGER,
        status=MembershipStatus.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )
    model = membership_to_model(entity)
    restored = membership_from_model(
        MembershipModel(**{k: getattr(model, k) for k in model.__dict__ if not k.startswith("_")})
    )
    assert restored.role == OrgRole.MANAGER


def test_folder_round_trip() -> None:
    entity = Folder(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        name="Contracts",
        kind=FolderKind.STANDARD,
        description="Legal",
        created_at=NOW,
        updated_at=NOW,
    )
    model = folder_to_model(entity)
    restored = folder_from_model(
        FolderModel(
            **{
                c.name: getattr(model, c.name)
                for c in FolderModel.__table__.columns
                if c.name not in {"created_at", "updated_at"}
            }
            | {"created_at": NOW, "updated_at": NOW}
        )
    )
    assert restored.name == "Contracts"


def test_document_version_round_trip() -> None:
    doc_id = uuid.uuid4()
    entity = DocumentVersion(
        id=uuid.uuid4(),
        document_id=doc_id,
        version_number=3,
        storage_key="store/key",
        checksum_sha256="deadbeef",
        content_type="application/pdf",
        size_bytes=4096,
        status=VersionStatus.CURRENT,
        created_by=uuid.uuid4(),
        comment="v3",
        created_at=NOW,
        updated_at=NOW,
    )
    model = document_version_to_model(entity)
    restored = document_version_from_model(
        DocumentVersionModel(
            id=model.id,
            document_id=model.document_id,
            version_number=model.version_number,
            storage_key=model.storage_key,
            checksum_sha256=model.checksum_sha256,
            content_type=model.content_type,
            size_bytes=model.size_bytes,
            status=model.status,
            created_by=model.created_by,
            comment=model.comment,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    assert restored.version_number == 3
    assert restored.comment == "v3"


def test_document_lock_round_trip() -> None:
    entity = DocumentLock(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        locked_by=uuid.uuid4(),
        locked_at=NOW,
        expires_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )
    model = document_lock_to_model(entity)
    restored = document_lock_from_model(
        DocumentLockModel(
            id=model.id,
            document_id=model.document_id,
            locked_by=model.locked_by,
            locked_at=model.locked_at,
            expires_at=model.expires_at,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    assert restored.document_id == entity.document_id


def test_users_from_models_batch() -> None:
    entities = [
        User(
            id=uuid.uuid4(),
            email=f"user{i}@test.io",
            full_name=f"User {i}",
            password_hash="hash",
            created_at=NOW,
            updated_at=NOW,
        )
        for i in range(3)
    ]
    models = [user_to_model(e) for e in entities]
    restored = users_from_models(models)
    assert len(restored) == 3
    assert restored[0].email == "user0@test.io"


def test_folders_from_models_batch() -> None:
    entities = [
        Folder(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            name=f"Folder {i}",
            kind=FolderKind.STANDARD,
            description="",
            created_at=NOW,
            updated_at=NOW,
        )
        for i in range(2)
    ]
    models = [folder_to_model(e) for e in entities]
    restored = folders_from_models(
        [
            FolderModel(
                id=m.id,
                organization_id=m.organization_id,
                parent_id=m.parent_id,
                name=m.name,
                kind=m.kind,
                description=m.description,
                created_at=NOW,
                updated_at=NOW,
            )
            for m in models
        ]
    )
    assert len(restored) == 2
