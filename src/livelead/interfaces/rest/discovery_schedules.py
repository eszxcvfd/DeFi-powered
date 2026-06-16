import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.application.discovery.schedule_service import (
    DiscoveryScheduleService,
    ScheduleValidationError,
)
from livelead.domain.audit.enums import AuditAction, AuditOutcome, AuditTargetType
from livelead.domain.audit.model import AuditTarget
from livelead.domain.discovery.schedule_recurrence import parse_recurrence
from livelead.infrastructure.db.models import DiscoveryScheduleRow
from livelead.interfaces.auth.tenant_context import (
    TenantContext,
    get_tenant_context,
    require_scoring_editor,
)
from livelead.interfaces.rest.deps import get_db_session
from livelead.interfaces.rest.request_context import capture_request_context

router = APIRouter(tags=["discovery-schedules"])


class RecurrenceBody(BaseModel):
    kind: str
    timezone: str = "UTC"
    hour: int = 9
    minute: int = 0
    day_of_week: int = 0
    cron_expression: str | None = None


class CreateDiscoveryScheduleBody(BaseModel):
    recurrence: RecurrenceBody
    source_ids: list[UUID] | None = None


class PatchDiscoveryScheduleBody(BaseModel):
    recurrence: RecurrenceBody | None = None
    enabled_state: str | None = None
    source_ids: list[UUID] | None = None


class DiscoveryScheduleView(BaseModel):
    id: UUID
    campaign_id: UUID
    enabled_state: str
    recurrence: dict
    recurrence_summary: str
    timezone: str
    next_run_at: datetime | None
    source_ids: list[str]
    latest_job: dict | None = None
    last_dispatch_outcome: str | None = None


async def _to_view(
    row: DiscoveryScheduleRow, svc: DiscoveryScheduleService, org_id: UUID
) -> DiscoveryScheduleView:
    spec = parse_recurrence(json.loads(row.recurrence_json))
    latest = await svc.latest_job_summary(row, org_id)
    return DiscoveryScheduleView(
        id=UUID(row.id),
        campaign_id=UUID(row.campaign_id),
        enabled_state=row.enabled_state,
        recurrence=json.loads(row.recurrence_json),
        recurrence_summary=spec.summary(),
        timezone=spec.timezone,
        next_run_at=row.next_run_at,
        source_ids=json.loads(row.source_ids_json or "[]"),
        latest_job=latest,
        last_dispatch_outcome=row.last_dispatch_outcome,
    )


async def _audit_schedule(
    request: Request | None,
    session: AsyncSession,
    tenant: TenantContext,
    *,
    action: AuditAction,
    schedule_id: str,
    campaign_id: str,
    metadata: dict,
) -> None:
    ctx = (
        capture_request_context(request, workflow="discovery_schedule")
        if request is not None
        else make_context(workflow="discovery_schedule")
    )
    audit = AuditService(session)
    await audit.emit(
        organization_id=tenant.organization_id,
        actor=make_actor_from_role(tenant.actor_role),
        action=action,
        target=AuditTarget(
            target_type=AuditTargetType.DISCOVERY_SCHEDULE,
            target_id=schedule_id,
            display=f"schedule/{schedule_id}",
        ),
        outcome=AuditOutcome.SUCCEEDED,
        context=ctx,
        metadata={"campaign_id": campaign_id, **metadata},
    )


@router.post(
    "/campaigns/{campaign_id}/discovery-schedules",
    response_model=DiscoveryScheduleView,
    status_code=201,
)
async def create_discovery_schedule(
    campaign_id: UUID,
    body: CreateDiscoveryScheduleBody,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_scoring_editor(tenant)
    svc = DiscoveryScheduleService(session)
    try:
        row = await svc.create(
            organization_id=tenant.organization_id,
            campaign_id=campaign_id,
            recurrence=body.recurrence.model_dump(exclude_none=True),
            source_ids=body.source_ids,
            actor=tenant.actor_role,
        )
    except ScheduleValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await _audit_schedule(
        request,
        session,
        tenant,
        action=AuditAction.DISCOVERY_SCHEDULE_CREATED,
        schedule_id=row.id,
        campaign_id=row.campaign_id,
        metadata={"recurrence": json.loads(row.recurrence_json)},
    )
    await session.commit()
    return await _to_view(row, svc, tenant.organization_id)


@router.get(
    "/campaigns/{campaign_id}/discovery-schedules",
    response_model=list[DiscoveryScheduleView],
)
async def list_discovery_schedules(
    campaign_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = DiscoveryScheduleService(session)
    rows = await svc.list_for_campaign(campaign_id, tenant.organization_id)
    return [await _to_view(r, svc, tenant.organization_id) for r in rows]


@router.patch("/discovery-schedules/{schedule_id}", response_model=DiscoveryScheduleView)
async def patch_discovery_schedule(
    schedule_id: UUID,
    body: PatchDiscoveryScheduleBody,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    require_scoring_editor(tenant)
    svc = DiscoveryScheduleService(session)
    row = await svc.get(schedule_id, tenant.organization_id)
    if not row:
        raise HTTPException(status_code=404, detail="schedule not found")

    try:
        row = await svc.patch(
            row,
            recurrence=body.recurrence.model_dump(exclude_none=True) if body.recurrence else None,
            enabled_state=body.enabled_state,
            source_ids=body.source_ids,
            organization_id=tenant.organization_id,
        )
    except ScheduleValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await _audit_schedule(
        request,
        session,
        tenant,
        action=AuditAction.DISCOVERY_SCHEDULE_UPDATED,
        schedule_id=row.id,
        campaign_id=row.campaign_id,
        metadata={
            "enabled_state": row.enabled_state,
            "recurrence": json.loads(row.recurrence_json),
        },
    )
    await session.commit()
    return await _to_view(row, svc, tenant.organization_id)