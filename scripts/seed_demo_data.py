"""Seed demo organization, users, folders, and sample documents."""

from __future__ import annotations

import argparse
import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from vaultforge.core.config import get_settings
from vaultforge.domain.assets.enums import FolderKind, SensitivityLabel
from vaultforge.domain.identity.enums import MembershipStatus, OrgRole
from vaultforge.infrastructure.persistence.models.document import DocumentModel, DocumentVersionModel
from vaultforge.infrastructure.persistence.models.folder import FolderModel
from vaultforge.infrastructure.persistence.models.membership import MembershipModel
from vaultforge.infrastructure.persistence.models.organization import OrganizationModel
from vaultforge.infrastructure.persistence.models.user import UserModel
from vaultforge.infrastructure.security import hash_password

DEMO_ORG_SLUG = "acme-demo"
DEMO_PASSWORD = "DemoPass123!"


async def seed(*, dry_run: bool) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    org_id = uuid.uuid5(uuid.NAMESPACE_DNS, "vaultforge.demo.org")
    owner_id = uuid.uuid5(uuid.NAMESPACE_DNS, "vaultforge.demo.owner")
    admin_id = uuid.uuid5(uuid.NAMESPACE_DNS, "vaultforge.demo.admin")
    root_folder_id = uuid.uuid5(uuid.NAMESPACE_DNS, "vaultforge.demo.root")
    contracts_folder_id = uuid.uuid5(uuid.NAMESPACE_DNS, "vaultforge.demo.contracts")
    doc_id = uuid.uuid5(uuid.NAMESPACE_DNS, "vaultforge.demo.doc")
    version_id = uuid.uuid5(uuid.NAMESPACE_DNS, "vaultforge.demo.version")

    plan = {
        "organization": OrganizationModel(
            id=org_id,
            name="Acme Demo Corp",
            slug=DEMO_ORG_SLUG,
            plan_code="enterprise",
            max_storage_gb=500,
        ),
        "users": [
            UserModel(
                id=owner_id,
                email="owner@acme-demo.test",
                full_name="Demo Owner",
                password_hash=hash_password(DEMO_PASSWORD),
                is_active=True,
                is_email_verified=True,
            ),
            UserModel(
                id=admin_id,
                email="admin@acme-demo.test",
                full_name="Demo Admin",
                password_hash=hash_password(DEMO_PASSWORD),
                is_active=True,
                is_email_verified=True,
            ),
        ],
        "memberships": [
            MembershipModel(
                id=uuid.uuid4(),
                organization_id=org_id,
                user_id=owner_id,
                role=OrgRole.OWNER.value,
                status=MembershipStatus.ACTIVE.value,
            ),
            MembershipModel(
                id=uuid.uuid4(),
                organization_id=org_id,
                user_id=admin_id,
                role=OrgRole.ADMIN.value,
                status=MembershipStatus.ACTIVE.value,
            ),
        ],
        "folders": [
            FolderModel(
                id=root_folder_id,
                organization_id=org_id,
                name="Root",
                kind=FolderKind.ROOT.value,
                description="Demo root folder",
            ),
            FolderModel(
                id=contracts_folder_id,
                organization_id=org_id,
                parent_id=root_folder_id,
                name="Contracts",
                kind=FolderKind.STANDARD.value,
                description="Sample contract documents",
            ),
        ],
        "document": DocumentModel(
            id=doc_id,
            organization_id=org_id,
            folder_id=contracts_folder_id,
            name="Master-Services-Agreement.pdf",
            status="active",
            sensitivity=SensitivityLabel.CONFIDENTIAL.value,
            tags=["contract", "legal"],
            current_version_id=version_id,
            created_by=owner_id,
        ),
        "version": DocumentVersionModel(
            id=version_id,
            document_id=doc_id,
            version_number=1,
            storage_key=f"{org_id}/{doc_id}/v1/Master-Services-Agreement.pdf",
            checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            content_type="application/pdf",
            size_bytes=0,
            status="current",
            created_by=owner_id,
            comment="Initial demo upload",
        ),
    }

    if dry_run:
        print("DRY RUN - would seed:")
        print(f"  org: {plan['organization'].slug} ({org_id})")
        print("  users: owner@acme-demo.test, admin@acme-demo.test")
        print("  folders: Root, Contracts")
        print("  document: Master-Services-Agreement.pdf")
        await engine.dispose()
        return

    async with session_factory() as session:
        existing = await session.scalar(
            select(OrganizationModel).where(OrganizationModel.slug == DEMO_ORG_SLUG)
        )
        if existing is not None:
            print(f"Demo org '{DEMO_ORG_SLUG}' already exists ({existing.id})")
            await engine.dispose()
            return

        session.add(plan["organization"])
        for user in plan["users"]:
            session.add(user)
        for membership in plan["memberships"]:
            session.add(membership)
        for folder in plan["folders"]:
            session.add(folder)
        session.add(plan["document"])
        session.add(plan["version"])
        await session.commit()
        print(f"Seeded demo org '{DEMO_ORG_SLUG}' with 2 users, 2 folders, 1 document")

    await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed VaultForge demo data")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without writing")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(seed(dry_run=args.dry_run))
