"""SQLAlchemy sharing and retention repositories."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.domain.retention.entities import LegalHold, RetentionPolicy, RetentionSchedule
from vaultforge.domain.retention.enums import RetentionPolicyStatus, RetentionScope
from vaultforge.domain.retention.repositories import RetentionScheduleQuery
from vaultforge.domain.sharing.entities import (
    AccessControlEntry,
    ShareGrant,
    ShareInvitation,
    ShareLink,
)
from vaultforge.domain.sharing.enums import (
    SharePermission,
    ShareResourceType,
    ShareStatus,
    ShareTargetType,
)
from vaultforge.domain.sharing.repositories import ShareQueryCriteria
from vaultforge.infrastructure.persistence.models.share import (
    AccessControlEntryModel,
    LegalHoldModel,
    RetentionPolicyModel,
    RetentionScheduleModel,
    ShareGrantModel,
    ShareInvitationModel,
    ShareLinkModel,
)


def _grant_to_entity(model: ShareGrantModel) -> ShareGrant:
    return ShareGrant(
        id=model.id,
        organization_id=model.organization_id,
        resource_type=ShareResourceType(model.resource_type),
        resource_id=model.resource_id,
        target_type=ShareTargetType(model.target_type),
        target_id=model.target_id,
        target_email=model.target_email,
        permission=SharePermission(model.permission),
        granted_by=model.granted_by,
        status=ShareStatus(model.status),
        expires_at=model.expires_at,
        revoked_at=model.revoked_at,
        revoked_by=model.revoked_by,
        message=model.message,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_grant(model: ShareGrantModel, grant: ShareGrant) -> None:
    model.status = grant.status.value
    model.expires_at = grant.expires_at
    model.revoked_at = grant.revoked_at
    model.revoked_by = grant.revoked_by
    model.message = grant.message
    model.updated_at = grant.updated_at


def _link_to_entity(model: ShareLinkModel) -> ShareLink:
    return ShareLink(
        id=model.id,
        organization_id=model.organization_id,
        resource_type=ShareResourceType(model.resource_type),
        resource_id=model.resource_id,
        token=model.token,
        permission=SharePermission(model.permission),
        created_by=model.created_by,
        status=ShareStatus(model.status),
        password_hash=model.password_hash,
        max_uses=model.max_uses,
        use_count=model.use_count,
        expires_at=model.expires_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_link(model: ShareLinkModel, link: ShareLink) -> None:
    model.status = link.status.value
    model.use_count = link.use_count
    model.updated_at = link.updated_at


def _invitation_to_entity(model: ShareInvitationModel) -> ShareInvitation:
    return ShareInvitation(
        id=model.id,
        organization_id=model.organization_id,
        resource_type=ShareResourceType(model.resource_type),
        resource_id=model.resource_id,
        email=model.email,
        permission=SharePermission(model.permission),
        invited_by=model.invited_by,
        status=ShareStatus(model.status),
        token=model.token,
        accepted_by=model.accepted_by,
        accepted_at=model.accepted_at,
        expires_at=model.expires_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_invitation(model: ShareInvitationModel, invitation: ShareInvitation) -> None:
    model.status = invitation.status.value
    model.accepted_by = invitation.accepted_by
    model.accepted_at = invitation.accepted_at
    model.updated_at = invitation.updated_at


def _acl_to_entity(model: AccessControlEntryModel) -> AccessControlEntry:
    return AccessControlEntry(
        id=model.id,
        organization_id=model.organization_id,
        resource_type=ShareResourceType(model.resource_type),
        resource_id=model.resource_id,
        principal_type=model.principal_type,  # type: ignore[arg-type]
        principal_id=model.principal_id,
        permission=SharePermission(model.permission),
        effect=model.effect,  # type: ignore[arg-type]
        inherited=model.inherited,
        source_folder_id=model.source_folder_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _policy_to_entity(model: RetentionPolicyModel) -> RetentionPolicy:
    return RetentionPolicy(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        description=model.description,
        scope=RetentionScope(model.scope),
        scope_ref_id=model.scope_ref_id,
        trigger=model.trigger,  # type: ignore[arg-type]
        retention_days=model.retention_days,
        action=model.action,  # type: ignore[arg-type]
        status=RetentionPolicyStatus(model.status),
        created_by=model.created_by,
        priority=model.priority,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_policy(model: RetentionPolicyModel, policy: RetentionPolicy) -> None:
    model.name = policy.name
    model.description = policy.description
    model.retention_days = policy.retention_days
    model.action = policy.action.value
    model.status = policy.status.value
    model.priority = policy.priority
    model.updated_at = policy.updated_at


def _schedule_to_entity(model: RetentionScheduleModel) -> RetentionSchedule:
    return RetentionSchedule(
        id=model.id,
        organization_id=model.organization_id,
        policy_id=model.policy_id,
        resource_type=model.resource_type,
        resource_id=model.resource_id,
        reference_time=model.reference_time,
        expires_at=model.expires_at,
        action=model.action,  # type: ignore[arg-type]
        executed_at=model.executed_at,
        blocked_by_legal_hold=model.blocked_by_legal_hold,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_schedule(model: RetentionScheduleModel, schedule: RetentionSchedule) -> None:
    model.executed_at = schedule.executed_at
    model.blocked_by_legal_hold = schedule.blocked_by_legal_hold
    model.updated_at = schedule.updated_at


def _hold_to_entity(model: LegalHoldModel) -> LegalHold:
    return LegalHold(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        description=model.description,
        matter_id=model.matter_id,
        status=model.status,  # type: ignore[arg-type]
        created_by=model.created_by,
        released_by=model.released_by,
        released_at=model.released_at,
        resource_ids=list(model.resource_ids or []),
        folder_ids=list(model.folder_ids or []),
        custodian_ids=list(model.custodian_ids or []),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_hold(model: LegalHoldModel, hold: LegalHold) -> None:
    model.name = hold.name
    model.description = hold.description
    model.matter_id = hold.matter_id
    model.status = hold.status.value
    model.released_by = hold.released_by
    model.released_at = hold.released_at
    model.resource_ids = hold.resource_ids
    model.folder_ids = hold.folder_ids
    model.custodian_ids = hold.custodian_ids
    model.updated_at = hold.updated_at


class SqlAlchemyShareGrantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, grant: ShareGrant) -> ShareGrant:
        model = ShareGrantModel(
            id=grant.id,
            organization_id=grant.organization_id,
            resource_type=grant.resource_type.value,
            resource_id=grant.resource_id,
            target_type=grant.target_type.value,
            target_id=grant.target_id,
            target_email=grant.target_email,
            permission=grant.permission.value,
            granted_by=grant.granted_by,
            status=grant.status.value,
            expires_at=grant.expires_at,
            revoked_at=grant.revoked_at,
            revoked_by=grant.revoked_by,
            message=grant.message,
            created_at=grant.created_at,
            updated_at=grant.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _grant_to_entity(model)

    async def update(self, grant: ShareGrant) -> ShareGrant:
        model = await self._session.get(ShareGrantModel, grant.id)
        if model is None:
            raise ValueError("Share grant not found")
        _apply_grant(model, grant)
        await self._session.flush()
        return _grant_to_entity(model)

    async def get_by_id(self, organization_id: uuid.UUID, grant_id: uuid.UUID) -> ShareGrant | None:
        stmt = select(ShareGrantModel).where(
            ShareGrantModel.id == grant_id,
            ShareGrantModel.organization_id == organization_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _grant_to_entity(model) if model else None

    async def query(self, criteria: ShareQueryCriteria) -> Sequence[ShareGrant]:
        stmt = select(ShareGrantModel).where(
            ShareGrantModel.organization_id == criteria.organization_id
        )
        if criteria.resource_type is not None:
            stmt = stmt.where(ShareGrantModel.resource_type == criteria.resource_type.value)
        if criteria.resource_id is not None:
            stmt = stmt.where(ShareGrantModel.resource_id == criteria.resource_id)
        if criteria.target_id is not None:
            stmt = stmt.where(ShareGrantModel.target_id == criteria.target_id)
        if criteria.status is not None:
            stmt = stmt.where(ShareGrantModel.status == criteria.status.value)
        stmt = stmt.order_by(ShareGrantModel.created_at.desc())
        stmt = stmt.limit(criteria.limit).offset(criteria.offset)
        result = await self._session.execute(stmt)
        return [_grant_to_entity(m) for m in result.scalars().all()]

    async def list_for_resource(
        self,
        organization_id: uuid.UUID,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
    ) -> Sequence[ShareGrant]:
        criteria = ShareQueryCriteria(
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
            status=None,
        )
        return await self.query(criteria)

    async def list_for_target(
        self,
        organization_id: uuid.UUID,
        target_id: uuid.UUID,
    ) -> Sequence[ShareGrant]:
        criteria = ShareQueryCriteria(
            organization_id=organization_id,
            target_id=target_id,
            status=ShareStatus.ACTIVE,
        )
        return await self.query(criteria)


class SqlAlchemyShareLinkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, link: ShareLink) -> ShareLink:
        model = ShareLinkModel(
            id=link.id,
            organization_id=link.organization_id,
            resource_type=link.resource_type.value,
            resource_id=link.resource_id,
            token=link.token,
            permission=link.permission.value,
            created_by=link.created_by,
            status=link.status.value,
            password_hash=link.password_hash,
            max_uses=link.max_uses,
            use_count=link.use_count,
            expires_at=link.expires_at,
            created_at=link.created_at,
            updated_at=link.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _link_to_entity(model)

    async def update(self, link: ShareLink) -> ShareLink:
        model = await self._session.get(ShareLinkModel, link.id)
        if model is None:
            raise ValueError("Share link not found")
        _apply_link(model, link)
        await self._session.flush()
        return _link_to_entity(model)

    async def get_by_token(self, token: str) -> ShareLink | None:
        stmt = select(ShareLinkModel).where(ShareLinkModel.token == token)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _link_to_entity(model) if model else None

    async def get_by_id(self, organization_id: uuid.UUID, link_id: uuid.UUID) -> ShareLink | None:
        stmt = select(ShareLinkModel).where(
            ShareLinkModel.id == link_id,
            ShareLinkModel.organization_id == organization_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _link_to_entity(model) if model else None

    async def list_for_resource(
        self,
        organization_id: uuid.UUID,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
    ) -> Sequence[ShareLink]:
        stmt = select(ShareLinkModel).where(
            ShareLinkModel.organization_id == organization_id,
            ShareLinkModel.resource_type == resource_type.value,
            ShareLinkModel.resource_id == resource_id,
        )
        result = await self._session.execute(stmt)
        return [_link_to_entity(m) for m in result.scalars().all()]


class SqlAlchemyShareInvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, invitation: ShareInvitation) -> ShareInvitation:
        model = ShareInvitationModel(
            id=invitation.id,
            organization_id=invitation.organization_id,
            resource_type=invitation.resource_type.value,
            resource_id=invitation.resource_id,
            email=invitation.email,
            permission=invitation.permission.value,
            invited_by=invitation.invited_by,
            status=invitation.status.value,
            token=invitation.token,
            accepted_by=invitation.accepted_by,
            accepted_at=invitation.accepted_at,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
            updated_at=invitation.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _invitation_to_entity(model)

    async def update(self, invitation: ShareInvitation) -> ShareInvitation:
        model = await self._session.get(ShareInvitationModel, invitation.id)
        if model is None:
            raise ValueError("Share invitation not found")
        _apply_invitation(model, invitation)
        await self._session.flush()
        return _invitation_to_entity(model)

    async def get_by_token(self, token: str) -> ShareInvitation | None:
        stmt = select(ShareInvitationModel).where(ShareInvitationModel.token == token)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _invitation_to_entity(model) if model else None

    async def get_by_id(
        self, organization_id: uuid.UUID, invitation_id: uuid.UUID
    ) -> ShareInvitation | None:
        stmt = select(ShareInvitationModel).where(
            ShareInvitationModel.id == invitation_id,
            ShareInvitationModel.organization_id == organization_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _invitation_to_entity(model) if model else None


class SqlAlchemyAccessControlRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_resource(
        self,
        organization_id: uuid.UUID,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
        entries: list[AccessControlEntry],
    ) -> list[AccessControlEntry]:
        await self._session.execute(
            delete(AccessControlEntryModel).where(
                AccessControlEntryModel.organization_id == organization_id,
                AccessControlEntryModel.resource_type == resource_type.value,
                AccessControlEntryModel.resource_id == resource_id,
            )
        )
        models = [
            AccessControlEntryModel(
                id=entry.id,
                organization_id=organization_id,
                resource_type=resource_type.value,
                resource_id=resource_id,
                principal_type=entry.principal_type.value,
                principal_id=entry.principal_id,
                permission=entry.permission.value,
                effect=entry.effect.value,
                inherited=entry.inherited,
                source_folder_id=entry.source_folder_id,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
            )
            for entry in entries
        ]
        self._session.add_all(models)
        await self._session.flush()
        return [_acl_to_entity(m) for m in models]

    async def list_for_resource(
        self,
        organization_id: uuid.UUID,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
    ) -> Sequence[AccessControlEntry]:
        stmt = select(AccessControlEntryModel).where(
            AccessControlEntryModel.organization_id == organization_id,
            AccessControlEntryModel.resource_type == resource_type.value,
            AccessControlEntryModel.resource_id == resource_id,
        )
        result = await self._session.execute(stmt)
        return [_acl_to_entity(m) for m in result.scalars().all()]

    async def list_effective_permissions(
        self,
        organization_id: uuid.UUID,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
        principal_id: uuid.UUID,
    ) -> SharePermission | None:
        entries = await self.list_for_resource(organization_id, resource_type, resource_id)
        user_entries = [e for e in entries if e.principal_id == principal_id]
        if not user_entries:
            return None
        from vaultforge.domain.sharing.enums import PERMISSION_RANK

        best: SharePermission | None = None
        for entry in user_entries:
            if entry.effect.value == "deny":
                continue
            if best is None or PERMISSION_RANK[entry.permission] > PERMISSION_RANK[best]:
                best = entry.permission
        return best


class SqlAlchemyRetentionPolicyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, policy: RetentionPolicy) -> RetentionPolicy:
        model = RetentionPolicyModel(
            id=policy.id,
            organization_id=policy.organization_id,
            name=policy.name,
            description=policy.description,
            scope=policy.scope.value,
            scope_ref_id=policy.scope_ref_id,
            trigger=policy.trigger.value,
            retention_days=policy.retention_days,
            action=policy.action.value,
            status=policy.status.value,
            created_by=policy.created_by,
            priority=policy.priority,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _policy_to_entity(model)

    async def update(self, policy: RetentionPolicy) -> RetentionPolicy:
        model = await self._session.get(RetentionPolicyModel, policy.id)
        if model is None:
            raise ValueError("Retention policy not found")
        _apply_policy(model, policy)
        await self._session.flush()
        return _policy_to_entity(model)

    async def get_by_id(
        self, organization_id: uuid.UUID, policy_id: uuid.UUID
    ) -> RetentionPolicy | None:
        stmt = select(RetentionPolicyModel).where(
            RetentionPolicyModel.id == policy_id,
            RetentionPolicyModel.organization_id == organization_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _policy_to_entity(model) if model else None

    async def list_for_organization(self, organization_id: uuid.UUID) -> Sequence[RetentionPolicy]:
        stmt = select(RetentionPolicyModel).where(
            RetentionPolicyModel.organization_id == organization_id
        )
        result = await self._session.execute(stmt)
        return [_policy_to_entity(m) for m in result.scalars().all()]

    async def find_applicable(
        self,
        organization_id: uuid.UUID,
        scope: RetentionScope,
        scope_ref_id: uuid.UUID | None,
    ) -> Sequence[RetentionPolicy]:
        stmt = select(RetentionPolicyModel).where(
            RetentionPolicyModel.organization_id == organization_id,
            RetentionPolicyModel.status == RetentionPolicyStatus.ACTIVE.value,
            RetentionPolicyModel.scope == scope.value,
        )
        if scope_ref_id is not None:
            stmt = stmt.where(RetentionPolicyModel.scope_ref_id == scope_ref_id)
        result = await self._session.execute(stmt)
        return [_policy_to_entity(m) for m in result.scalars().all()]


class SqlAlchemyRetentionScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, schedule: RetentionSchedule) -> RetentionSchedule:
        model = RetentionScheduleModel(
            id=schedule.id,
            organization_id=schedule.organization_id,
            policy_id=schedule.policy_id,
            resource_type=schedule.resource_type,
            resource_id=schedule.resource_id,
            reference_time=schedule.reference_time,
            expires_at=schedule.expires_at,
            action=schedule.action.value,
            executed_at=schedule.executed_at,
            blocked_by_legal_hold=schedule.blocked_by_legal_hold,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _schedule_to_entity(model)

    async def update(self, schedule: RetentionSchedule) -> RetentionSchedule:
        model = await self._session.get(RetentionScheduleModel, schedule.id)
        if model is None:
            raise ValueError("Retention schedule not found")
        _apply_schedule(model, schedule)
        await self._session.flush()
        return _schedule_to_entity(model)

    async def query(self, criteria: RetentionScheduleQuery) -> Sequence[RetentionSchedule]:
        stmt = select(RetentionScheduleModel).where(
            RetentionScheduleModel.organization_id == criteria.organization_id
        )
        if criteria.resource_id is not None:
            stmt = stmt.where(RetentionScheduleModel.resource_id == criteria.resource_id)
        if criteria.due_only:
            from vaultforge.domain.common import utc_now

            stmt = stmt.where(
                RetentionScheduleModel.executed_at.is_(None),
                RetentionScheduleModel.blocked_by_legal_hold.is_(False),
                RetentionScheduleModel.expires_at <= utc_now(),
            )
        stmt = stmt.limit(criteria.limit).offset(criteria.offset)
        result = await self._session.execute(stmt)
        return [_schedule_to_entity(m) for m in result.scalars().all()]

    async def get_for_resource(
        self,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
    ) -> RetentionSchedule | None:
        stmt = select(RetentionScheduleModel).where(
            RetentionScheduleModel.organization_id == organization_id,
            RetentionScheduleModel.resource_type == resource_type,
            RetentionScheduleModel.resource_id == resource_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _schedule_to_entity(model) if model else None


class SqlAlchemyLegalHoldRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, hold: LegalHold) -> LegalHold:
        model = LegalHoldModel(
            id=hold.id,
            organization_id=hold.organization_id,
            name=hold.name,
            description=hold.description,
            matter_id=hold.matter_id,
            status=hold.status.value,
            created_by=hold.created_by,
            released_by=hold.released_by,
            released_at=hold.released_at,
            resource_ids=hold.resource_ids,
            folder_ids=hold.folder_ids,
            custodian_ids=hold.custodian_ids,
            created_at=hold.created_at,
            updated_at=hold.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _hold_to_entity(model)

    async def update(self, hold: LegalHold) -> LegalHold:
        model = await self._session.get(LegalHoldModel, hold.id)
        if model is None:
            raise ValueError("Legal hold not found")
        _apply_hold(model, hold)
        await self._session.flush()
        return _hold_to_entity(model)

    async def get_by_id(self, organization_id: uuid.UUID, hold_id: uuid.UUID) -> LegalHold | None:
        stmt = select(LegalHoldModel).where(
            LegalHoldModel.id == hold_id,
            LegalHoldModel.organization_id == organization_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _hold_to_entity(model) if model else None

    async def list_active(self, organization_id: uuid.UUID) -> Sequence[LegalHold]:
        stmt = select(LegalHoldModel).where(
            LegalHoldModel.organization_id == organization_id,
            LegalHoldModel.status == "active",
        )
        result = await self._session.execute(stmt)
        return [_hold_to_entity(m) for m in result.scalars().all()]

    async def find_covering_resource(
        self,
        organization_id: uuid.UUID,
        resource_id: uuid.UUID,
        folder_id: uuid.UUID | None = None,
    ) -> Sequence[LegalHold]:
        holds = await self.list_active(organization_id)
        return [hold for hold in holds if hold.covers_resource(resource_id, folder_id)]
