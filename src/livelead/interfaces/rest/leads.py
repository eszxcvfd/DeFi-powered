from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.leads.service import CreateLeadInput, LeadService
from livelead.application.reminders.service import ReminderService
from livelead.domain.leads.models import LeadOriginKind, LeadStage
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.deps import get_db_session
from livelead.interfaces.rest.leads_schemas import (
    LeadActivitySchema,
    LeadCreateSchema,
    LeadDetailSchema,
    LeadPatchSchema,
    LeadReminderSummarySchema,
    LeadSummarySchema,
)

router = APIRouter(tags=["leads"])


async def _reminder_schema(session: AsyncSession, org_id: UUID, lead) -> LeadReminderSummarySchema:
    summary = await ReminderService(session).summary_for_lead(
        org_id, lead.id, follow_up_date=lead.follow_up_date
    )
    return LeadReminderSummarySchema(**summary)


def _summary(lead, reminder: LeadReminderSummarySchema) -> LeadSummarySchema:
    return LeadSummarySchema(
        id=lead.id,
        display_name=lead.display_name,
        company=lead.company,
        title=lead.title,
        owner=lead.owner,
        stage=lead.stage.value,
        discovery_source=lead.discovery_source,
        campaign_id=lead.campaign_id,
        event_id=lead.event_id,
        follow_up_date=lead.follow_up_date,
        updated_at=lead.updated_at,
        reminder=reminder,
    )


def _detail(lead, history: list, reminder: LeadReminderSummarySchema) -> LeadDetailSchema:
    base = _summary(lead, reminder)
    return LeadDetailSchema(
        **base.model_dump(),
        public_url=lead.public_url,
        interests=lead.interests,
        pain_points=lead.pain_points,
        lawful_basis_note=lead.lawful_basis_note,
        notes=lead.notes,
        manual_entry_note=lead.manual_entry_note,
        origin_kind=lead.origin_kind.value,
        created_by=lead.created_by,
        created_at=lead.created_at,
        recent_activity=[
            LeadActivitySchema(
                id=h.id,
                kind=h.kind.value,
                actor=h.actor,
                body=h.body,
                from_stage=h.from_stage,
                to_stage=h.to_stage,
                created_at=h.created_at,
            )
            for h in history
        ],
    )


@router.get("/leads", response_model=list[LeadSummarySchema])
async def list_leads(
    owner: str | None = Query(default=None),
    campaign_id: UUID | None = Query(default=None),
    discovery_source: str | None = Query(default=None),
    due_before: date | None = Query(default=None),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = LeadService(session)
    rem_svc = ReminderService(session)
    leads = await svc.list_leads(
        tenant.organization_id,
        owner=owner,
        campaign_id=campaign_id,
        discovery_source=discovery_source,
        due_before=due_before,
    )
    out = []
    for lead in leads:
        summary = await rem_svc.summary_for_lead(
            tenant.organization_id, lead.id, follow_up_date=lead.follow_up_date
        )
        out.append(_summary(lead, LeadReminderSummarySchema(**summary)))
    await session.commit()
    return out


@router.post("/leads", response_model=LeadDetailSchema, status_code=201)
async def create_lead(
    body: LeadCreateSchema,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    try:
        origin = LeadOriginKind(body.origin_kind)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid origin_kind") from exc
    svc = LeadService(session)
    try:
        lead = await svc.create_lead(
            tenant.organization_id,
            tenant.actor_role,
            CreateLeadInput(
                display_name=body.display_name,
                company=body.company,
                title=body.title,
                public_url=body.public_url,
                discovery_source=body.discovery_source,
                event_id=body.event_id,
                campaign_id=body.campaign_id,
                interests=body.interests,
                pain_points=body.pain_points,
                owner=body.owner,
                lawful_basis_note=body.lawful_basis_note,
                follow_up_date=body.follow_up_date,
                notes=body.notes,
                manual_entry_note=body.manual_entry_note,
                origin_kind=origin,
                email=body.email,
                external_id=body.external_id,
            ),
        )
    except ValueError as exc:
        msg = str(exc)
        code = 409 if msg.startswith("duplicate") else 400
        raise HTTPException(status_code=code, detail=msg) from exc
    history = await svc.list_activity(lead.id)
    reminder = await _reminder_schema(session, tenant.organization_id, lead)
    await session.commit()
    return _detail(lead, history, reminder)


@router.get("/leads/{lead_id}", response_model=LeadDetailSchema)
async def get_lead(
    lead_id: UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = LeadService(session)
    detail = await svc.get_detail(lead_id, tenant.organization_id)
    if not detail:
        raise HTTPException(status_code=404, detail="lead not found")
    lead, history = detail
    reminder = await _reminder_schema(session, tenant.organization_id, lead)
    await session.commit()
    return _detail(lead, history, reminder)


@router.patch("/leads/{lead_id}", response_model=LeadDetailSchema)
async def patch_lead(
    lead_id: UUID,
    body: LeadPatchSchema,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    stage = None
    if body.stage is not None:
        try:
            stage = LeadStage(body.stage)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid stage") from exc
    svc = LeadService(session)
    try:
        lead = await svc.update_lead(
            lead_id,
            tenant.organization_id,
            tenant.actor_role,
            owner=body.owner,
            notes=body.notes,
            follow_up_date=body.follow_up_date,
            stage=stage,
            activity_note=body.activity_note,
            title=body.title,
            company=body.company,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")
    history = await svc.list_activity(lead_id)
    reminder = await _reminder_schema(session, tenant.organization_id, lead)
    await session.commit()
    return _detail(lead, history, reminder)