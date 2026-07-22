"""Retention policy, schedule, and legal hold application service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from vaultforge.application.retention.schemas import (
    LegalHoldCreateRequest,
    LegalHoldResponse,
    LegalHoldUpdateRequest,
    ResourceHoldCheckResponse,
    RetentionDueQuery,
    RetentionPolicyCreateRequest,
    RetentionPolicyResponse,
    RetentionPolicyUpdateRequest,
    RetentionScheduleResponse,
    ScheduleResourceRequest,
)
from vaultforge.core.exceptions import ConflictError, NotFoundError, ValidationError
from vaultforge.domain.common import utc_now
from vaultforge.domain.retention.entities import LegalHold, RetentionPolicy, RetentionSchedule
from vaultforge.domain.retention.enums import RetentionScope
from vaultforge.domain.retention.repositories import (
    LegalHoldRepository,
    RetentionPolicyRepository,
    RetentionScheduleQuery,
    RetentionScheduleRepository,
)


@dataclass(slots=True)
class RetentionService:
    policies: RetentionPolicyRepository
    schedules: RetentionScheduleRepository
    legal_holds: LegalHoldRepository

    async def create_policy(
        self,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: RetentionPolicyCreateRequest,
    ) -> RetentionPolicyResponse:
        policy = RetentionPolicy(
            organization_id=organization_id,
            name=payload.name,
            description=payload.description,
            scope=payload.scope,
            scope_ref_id=payload.scope_ref_id,
            trigger=payload.trigger,
            retention_days=payload.retention_days,
            action=payload.action,
            created_by=actor_id,
            priority=payload.priority,
        )
        saved = await self.policies.add(policy)
        return RetentionPolicyResponse.model_validate(saved)

    async def update_policy(
        self,
        organization_id: uuid.UUID,
        policy_id: uuid.UUID,
        payload: RetentionPolicyUpdateRequest,
    ) -> RetentionPolicyResponse:
        policy = await self._get_policy(organization_id, policy_id)
        if payload.name is not None:
            policy.name = payload.name
        if payload.description is not None:
            policy.description = payload.description
        if payload.retention_days is not None:
            policy.retention_days = payload.retention_days
        if payload.action is not None:
            policy.action = payload.action
        if payload.priority is not None:
            policy.priority = payload.priority
        policy.touch()
        saved = await self.policies.update(policy)
        return RetentionPolicyResponse.model_validate(saved)

    async def disable_policy(
        self,
        organization_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> RetentionPolicyResponse:
        policy = await self._get_policy(organization_id, policy_id)
        policy.disable()
        saved = await self.policies.update(policy)
        return RetentionPolicyResponse.model_validate(saved)

    async def list_policies(self, organization_id: uuid.UUID) -> list[RetentionPolicyResponse]:
        policies = await self.policies.list_for_organization(organization_id)
        return [RetentionPolicyResponse.model_validate(p) for p in policies]

    async def schedule_resource(
        self,
        organization_id: uuid.UUID,
        policy_id: uuid.UUID,
        payload: ScheduleResourceRequest,
    ) -> RetentionScheduleResponse:
        policy = await self._get_policy(organization_id, policy_id)
        existing = await self.schedules.get_for_resource(
            organization_id, payload.resource_type, payload.resource_id
        )
        if existing is not None and existing.executed_at is None:
            raise ConflictError("Resource already has an active retention schedule")

        reference = payload.reference_time or utc_now()
        expires_at = policy.compute_expiry(reference)
        blocked = await self._is_blocked_by_hold(
            organization_id, payload.resource_id, payload.folder_id
        )
        schedule = RetentionSchedule(
            organization_id=organization_id,
            policy_id=policy.id,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            reference_time=reference,
            expires_at=expires_at,
            action=policy.action,
            blocked_by_legal_hold=blocked,
        )
        saved = await self.schedules.add(schedule)
        return RetentionScheduleResponse.model_validate(saved)

    async def list_due_schedules(
        self,
        organization_id: uuid.UUID,
        query: RetentionDueQuery,
    ) -> list[RetentionScheduleResponse]:
        criteria = RetentionScheduleQuery(
            organization_id=organization_id,
            due_only=True,
            limit=query.limit,
        )
        schedules = await self.schedules.query(criteria)
        due = [s for s in schedules if s.is_due()]
        return [RetentionScheduleResponse.model_validate(s) for s in due]

    async def execute_schedule(
        self,
        organization_id: uuid.UUID,
        schedule_id: uuid.UUID,
    ) -> RetentionScheduleResponse:
        criteria = RetentionScheduleQuery(organization_id=organization_id, limit=500)
        schedules = await self.schedules.query(criteria)
        schedule = next((s for s in schedules if s.id == schedule_id), None)
        if schedule is None:
            raise NotFoundError("Retention schedule not found")
        if not schedule.is_due():
            raise ValidationError("Schedule is not due for execution")
        schedule.mark_executed()
        saved = await self.schedules.update(schedule)
        return RetentionScheduleResponse.model_validate(saved)

    async def create_legal_hold(
        self,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: LegalHoldCreateRequest,
    ) -> LegalHoldResponse:
        hold = LegalHold(
            organization_id=organization_id,
            name=payload.name,
            description=payload.description,
            matter_id=payload.matter_id,
            created_by=actor_id,
            resource_ids=list(payload.resource_ids),
            folder_ids=list(payload.folder_ids),
            custodian_ids=list(payload.custodian_ids),
        )
        saved = await self.legal_holds.add(hold)
        await self._block_schedules_for_hold(saved)
        return LegalHoldResponse.model_validate(saved)

    async def update_legal_hold(
        self,
        organization_id: uuid.UUID,
        hold_id: uuid.UUID,
        payload: LegalHoldUpdateRequest,
    ) -> LegalHoldResponse:
        hold = await self._get_hold(organization_id, hold_id)
        if not hold.is_active():
            raise ValidationError("Cannot update a released legal hold")
        if payload.name is not None:
            hold.name = payload.name
        if payload.description is not None:
            hold.description = payload.description
        if payload.resource_ids is not None:
            hold.resource_ids = list(payload.resource_ids)
        if payload.folder_ids is not None:
            hold.folder_ids = list(payload.folder_ids)
        if payload.custodian_ids is not None:
            hold.custodian_ids = list(payload.custodian_ids)
        hold.touch()
        saved = await self.legal_holds.update(hold)
        await self._block_schedules_for_hold(saved)
        return LegalHoldResponse.model_validate(saved)

    async def release_legal_hold(
        self,
        organization_id: uuid.UUID,
        hold_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> LegalHoldResponse:
        hold = await self._get_hold(organization_id, hold_id)
        hold.release(actor_id)
        saved = await self.legal_holds.update(hold)
        await self._unblock_schedules_for_hold(saved)
        return LegalHoldResponse.model_validate(saved)

    async def list_legal_holds(self, organization_id: uuid.UUID) -> list[LegalHoldResponse]:
        holds = await self.legal_holds.list_active(organization_id)
        return [LegalHoldResponse.model_validate(h) for h in holds]

    async def check_resource_hold(
        self,
        organization_id: uuid.UUID,
        resource_id: uuid.UUID,
        folder_id: uuid.UUID | None = None,
    ) -> ResourceHoldCheckResponse:
        holds = await self.legal_holds.find_covering_resource(
            organization_id, resource_id, folder_id
        )
        active = [h for h in holds if h.is_active()]
        return ResourceHoldCheckResponse(
            resource_id=resource_id,
            folder_id=folder_id,
            under_hold=len(active) > 0,
            hold_ids=[h.id for h in active],
        )

    async def resolve_applicable_policy(
        self,
        organization_id: uuid.UUID,
        scope: RetentionScope,
        scope_ref_id: uuid.UUID | None,
    ) -> RetentionPolicy | None:
        policies = await self.policies.find_applicable(organization_id, scope, scope_ref_id)
        if not policies:
            org_policies = await self.policies.find_applicable(
                organization_id, RetentionScope.ORGANIZATION, None
            )
            policies = list(org_policies)
        if not policies:
            return None
        return sorted(policies, key=lambda p: p.priority)[0]

    async def _is_blocked_by_hold(
        self,
        organization_id: uuid.UUID,
        resource_id: uuid.UUID,
        folder_id: uuid.UUID | None,
    ) -> bool:
        holds = await self.legal_holds.find_covering_resource(
            organization_id, resource_id, folder_id
        )
        return any(h.is_active() for h in holds)

    async def _block_schedules_for_hold(self, hold: LegalHold) -> None:
        criteria = RetentionScheduleQuery(organization_id=hold.organization_id, limit=1000)
        schedules = await self.schedules.query(criteria)
        for schedule in schedules:
            if schedule.executed_at is not None:
                continue
            if hold.covers_resource(schedule.resource_id):
                schedule.block_for_legal_hold()
                await self.schedules.update(schedule)

    async def _unblock_schedules_for_hold(self, hold: LegalHold) -> None:
        criteria = RetentionScheduleQuery(organization_id=hold.organization_id, limit=1000)
        schedules = await self.schedules.query(criteria)
        for schedule in schedules:
            if not schedule.blocked_by_legal_hold:
                continue
            still_blocked = await self._is_blocked_by_hold(
                hold.organization_id, schedule.resource_id, None
            )
            if not still_blocked:
                schedule.unblock_legal_hold()
                await self.schedules.update(schedule)

    async def _get_policy(
        self, organization_id: uuid.UUID, policy_id: uuid.UUID
    ) -> RetentionPolicy:
        policy = await self.policies.get_by_id(organization_id, policy_id)
        if policy is None:
            raise NotFoundError("Retention policy not found")
        return policy

    async def _get_hold(self, organization_id: uuid.UUID, hold_id: uuid.UUID) -> LegalHold:
        hold = await self.legal_holds.get_by_id(organization_id, hold_id)
        if hold is None:
            raise NotFoundError("Legal hold not found")
        return hold
