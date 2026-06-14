"""Follow-up reminder application service (US-013)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.reminders.classification import (
    classify_reminder_state,
    may_complete,
    may_reschedule,
)
from livelead.domain.reminders.models import FollowUpReminder, ReminderActionKind, ReminderState
from livelead.infrastructure.db.repositories.leads import LeadRepository
from livelead.infrastructure.db.repositories.reminders import (
    ReminderHistoryRepository,
    ReminderRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ReminderQueueItem:
    reminder: FollowUpReminder
    lead_display_name: str
    lead_company: str
    lead_stage: str


class ReminderService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._reminders = ReminderRepository(session)
        self._history = ReminderHistoryRepository(session)
        self._leads = LeadRepository(session)

    async def sync_from_lead(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        owner: str,
        follow_up_date: date | None,
        actor: str,
    ) -> FollowUpReminder | None:
        if follow_up_date is None:
            active = await self._reminders.get_active_for_lead(lead_id, organization_id)
            if active and may_complete(active.state):
                await self._reminders.save_state(
                    active.id, organization_id, state=ReminderState.COMPLETED, actor=actor
                )
                await self._history.append(
                    reminder_id=active.id,
                    lead_id=lead_id,
                    kind=ReminderActionKind.COMPLETED.value,
                    actor=actor,
                    note="Follow-up date cleared",
                    from_due_date=active.due_date.isoformat(),
                    to_due_date="",
                )
            return None

        existing = await self._reminders.get_active_for_lead(lead_id, organization_id)
        rem = await self._reminders.upsert_for_lead(
            organization_id=organization_id,
            lead_id=lead_id,
            owner=owner,
            due_date=follow_up_date,
            actor=actor,
        )
        kind = ReminderActionKind.REFRESHED if existing else ReminderActionKind.CREATED
        await self._history.append(
            reminder_id=rem.id,
            lead_id=lead_id,
            kind=kind.value,
            actor=actor,
            note="Synced from lead follow-up date",
            from_due_date=existing.due_date.isoformat() if existing else "",
            to_due_date=follow_up_date.isoformat(),
        )
        logger.info("reminder_sync lead_id=%s reminder_id=%s state=%s", lead_id, rem.id, rem.state.value)
        return rem

    async def summary_for_lead(
        self,
        organization_id: UUID,
        lead_id: UUID,
        *,
        follow_up_date: date | None,
        today: date | None = None,
    ) -> dict:
        if not follow_up_date:
            return {"has_reminder": False, "state": None, "due_date": None, "reminder_id": None}
        active = await self._reminders.get_active_for_lead(lead_id, organization_id)
        if not active:
            state = classify_reminder_state(follow_up_date, today=today)
            return {
                "has_reminder": True,
                "state": state.value,
                "due_date": follow_up_date.isoformat(),
                "reminder_id": None,
            }
        live = classify_reminder_state(active.due_date, today=today)
        return {
            "has_reminder": True,
            "state": live.value if active.state != ReminderState.COMPLETED else active.state.value,
            "due_date": active.due_date.isoformat(),
            "reminder_id": str(active.id),
        }

    async def list_due_queue(
        self,
        organization_id: UUID,
        *,
        owner: str | None = None,
        today: date | None = None,
    ) -> list[ReminderQueueItem]:
        ref = today or date.today()
        raw = await self._reminders.list_open_for_org(organization_id, owner=owner)
        out: list[ReminderQueueItem] = []
        for rem in raw:
            live = classify_reminder_state(rem.due_date, today=ref)
            if live not in (ReminderState.DUE, ReminderState.OVERDUE):
                continue
            lead = await self._leads.get(rem.lead_id, organization_id)
            if not lead:
                continue
            out.append(
                ReminderQueueItem(
                    reminder=rem,
                    lead_display_name=lead.display_name,
                    lead_company=lead.company,
                    lead_stage=lead.stage.value,
                )
            )
        return sorted(out, key=lambda i: i.reminder.due_date)

    async def list_in_app_alerts(self, organization_id: UUID, *, today: date | None = None) -> list[dict]:
        queue = await self.list_due_queue(organization_id, today=today)
        return [
            {
                "reminder_id": str(item.reminder.id),
                "lead_id": str(item.reminder.lead_id),
                "lead_display_name": item.lead_display_name,
                "due_date": item.reminder.due_date.isoformat(),
                "state": classify_reminder_state(item.reminder.due_date, today=today or date.today()).value,
                "owner": item.reminder.owner,
            }
            for item in queue
        ]

    async def complete(self, reminder_id: UUID, organization_id: UUID, actor: str, note: str = "") -> FollowUpReminder:
        rem = await self._reminders.get(reminder_id, organization_id)
        if not rem:
            raise ValueError("reminder not found")
        if not may_complete(rem.state):
            raise ValueError("reminder cannot be completed")
        updated = await self._reminders.save_state(
            reminder_id, organization_id, state=ReminderState.COMPLETED, actor=actor
        )
        assert updated
        await self._history.append(
            reminder_id=reminder_id,
            lead_id=rem.lead_id,
            kind=ReminderActionKind.COMPLETED.value,
            actor=actor,
            note=note or "Reminder completed",
            from_due_date=rem.due_date.isoformat(),
            to_due_date="",
        )
        logger.info("reminder_complete reminder_id=%s lead_id=%s actor=%s", reminder_id, rem.lead_id, actor)
        return updated

    async def get_lead_for_reminder(self, lead_id: UUID, organization_id: UUID):
        return await self._leads.get(lead_id, organization_id)

    async def reschedule(
        self,
        reminder_id: UUID,
        organization_id: UUID,
        actor: str,
        new_due_date: date,
        note: str = "",
    ) -> FollowUpReminder:
        rem = await self._reminders.get(reminder_id, organization_id)
        if not rem:
            raise ValueError("reminder not found")
        if not may_reschedule(rem.state):
            raise ValueError("reminder cannot be rescheduled")
        state = classify_reminder_state(new_due_date)
        updated = await self._reminders.save_state(
            reminder_id,
            organization_id,
            state=state,
            due_date=new_due_date,
            actor=actor,
        )
        assert updated
        await self._leads.save_fields(rem.lead_id, organization_id, follow_up_date=new_due_date.isoformat())
        await self._history.append(
            reminder_id=reminder_id,
            lead_id=rem.lead_id,
            kind=ReminderActionKind.RESCHEDULED.value,
            actor=actor,
            note=note or "Reminder rescheduled",
            from_due_date=rem.due_date.isoformat(),
            to_due_date=new_due_date.isoformat(),
        )
        logger.info(
            "reminder_reschedule reminder_id=%s lead_id=%s actor=%s due=%s",
            reminder_id,
            rem.lead_id,
            actor,
            new_due_date.isoformat(),
        )
        return updated