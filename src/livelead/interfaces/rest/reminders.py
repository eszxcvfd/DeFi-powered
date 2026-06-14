from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.reminders.service import ReminderService
from livelead.domain.reminders.classification import classify_reminder_state
from livelead.interfaces.auth.tenant_context import TenantContext, get_tenant_context
from livelead.interfaces.rest.deps import get_db_session
from livelead.interfaces.rest.reminders_schemas import (
    InAppReminderAlertSchema,
    ReminderActionSchema,
    ReminderQueueItemSchema,
    ReminderRescheduleSchema,
)

router = APIRouter(tags=["reminders"])


@router.get("/reminders/queue", response_model=list[ReminderQueueItemSchema])
async def reminder_queue(
    owner: str | None = Query(default=None),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ReminderService(session)
    items = await svc.list_due_queue(tenant.organization_id, owner=owner)
    await session.commit()
    return [
        ReminderQueueItemSchema(
            id=item.reminder.id,
            lead_id=item.reminder.lead_id,
            lead_display_name=item.lead_display_name,
            lead_company=item.lead_company,
            lead_stage=item.lead_stage,
            owner=item.reminder.owner,
            due_date=item.reminder.due_date,
            state=classify_reminder_state(item.reminder.due_date).value,
            last_actor=item.reminder.last_actor,
            last_action_at=item.reminder.last_action_at,
        )
        for item in items
    ]


@router.get("/reminders/alerts", response_model=list[InAppReminderAlertSchema])
async def reminder_alerts(
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ReminderService(session)
    alerts = await svc.list_in_app_alerts(tenant.organization_id)
    await session.commit()
    return [InAppReminderAlertSchema(**a) for a in alerts]


@router.post("/reminders/{reminder_id}/complete", response_model=ReminderQueueItemSchema)
async def complete_reminder(
    reminder_id: UUID,
    body: ReminderActionSchema,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ReminderService(session)
    try:
        updated = await svc.complete(reminder_id, tenant.organization_id, tenant.actor_role, body.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    lead = await svc.get_lead_for_reminder(updated.lead_id, tenant.organization_id)
    await session.commit()
    return ReminderQueueItemSchema(
        id=updated.id,
        lead_id=updated.lead_id,
        lead_display_name=lead.display_name if lead else "",
        lead_company=lead.company if lead else "",
        lead_stage=lead.stage.value if lead else "",
        owner=updated.owner,
        due_date=updated.due_date,
        state=updated.state.value,
        last_actor=updated.last_actor,
        last_action_at=updated.last_action_at,
    )


@router.post("/reminders/{reminder_id}/reschedule", response_model=ReminderQueueItemSchema)
async def reschedule_reminder(
    reminder_id: UUID,
    body: ReminderRescheduleSchema,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
):
    svc = ReminderService(session)
    try:
        updated = await svc.reschedule(
            reminder_id,
            tenant.organization_id,
            tenant.actor_role,
            body.due_date,
            body.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    lead = await svc.get_lead_for_reminder(updated.lead_id, tenant.organization_id)
    await session.commit()
    return ReminderQueueItemSchema(
        id=updated.id,
        lead_id=updated.lead_id,
        lead_display_name=lead.display_name if lead else "",
        lead_company=lead.company if lead else "",
        lead_stage=lead.stage.value if lead else "",
        owner=updated.owner,
        due_date=updated.due_date,
        state=updated.state.value,
        last_actor=updated.last_actor,
        last_action_at=updated.last_action_at,
    )