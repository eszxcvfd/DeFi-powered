from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.reminders.classification import classify_reminder_state
from livelead.domain.reminders.models import FollowUpReminder, ReminderHistoryEntry, ReminderState
from livelead.infrastructure.db.models import FollowUpReminderRow, ReminderHistoryRow
from livelead.infrastructure.db.reminder_mappers import row_to_history, row_to_reminder


class ReminderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_for_lead(
        self, lead_id: UUID, organization_id: UUID
    ) -> FollowUpReminder | None:
        result = await self._session.execute(
            select(FollowUpReminderRow).where(
                FollowUpReminderRow.lead_id == str(lead_id),
                FollowUpReminderRow.organization_id == str(organization_id),
                FollowUpReminderRow.state != ReminderState.COMPLETED.value,
            )
        )
        rows = result.scalars().all()
        if not rows:
            return None
        # Prefer most recently updated open reminder
        row = sorted(rows, key=lambda r: r.updated_at, reverse=True)[0]
        return row_to_reminder(row)

    async def get(self, reminder_id: UUID, organization_id: UUID) -> FollowUpReminder | None:
        result = await self._session.execute(
            select(FollowUpReminderRow).where(
                FollowUpReminderRow.id == str(reminder_id),
                FollowUpReminderRow.organization_id == str(organization_id),
            )
        )
        row = result.scalars().first()
        return row_to_reminder(row) if row else None

    async def list_open_for_org(
        self, organization_id: UUID, *, owner: str | None = None
    ) -> list[FollowUpReminder]:
        result = await self._session.execute(
            select(FollowUpReminderRow).where(
                FollowUpReminderRow.organization_id == str(organization_id),
                FollowUpReminderRow.state != ReminderState.COMPLETED.value,
            )
        )
        items: list[FollowUpReminder] = []
        for row in result.scalars().all():
            if owner and row.owner != owner:
                continue
            live_state = classify_reminder_state(date.fromisoformat(row.due_date))
            if row.state != live_state.value:
                row.state = live_state.value
                row.updated_at = datetime.now(UTC)
                self._session.add(row)
            items.append(row_to_reminder(row))
        await self._session.flush()
        return items

    async def upsert_for_lead(
        self,
        *,
        organization_id: UUID,
        lead_id: UUID,
        owner: str,
        due_date: date,
        actor: str,
    ) -> FollowUpReminder:
        existing = await self.get_active_for_lead(lead_id, organization_id)
        state = classify_reminder_state(due_date)
        now = datetime.now(UTC)
        if existing:
            result = await self._session.execute(
                select(FollowUpReminderRow).where(FollowUpReminderRow.id == str(existing.id))
            )
            row = result.scalars().one()
            row.due_date = due_date.isoformat()
            row.owner = owner or row.owner
            row.state = state.value
            row.last_actor = actor
            row.last_action_at = now
            row.updated_at = now
            self._session.add(row)
            await self._session.flush()
            return row_to_reminder(row)

        row = FollowUpReminderRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            lead_id=str(lead_id),
            owner=owner,
            due_date=due_date.isoformat(),
            state=state.value,
            last_actor=actor,
            last_action_at=now,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_reminder(row)

    async def save_state(
        self,
        reminder_id: UUID,
        organization_id: UUID,
        *,
        state: ReminderState,
        due_date: date | None = None,
        actor: str,
    ) -> FollowUpReminder | None:
        result = await self._session.execute(
            select(FollowUpReminderRow).where(
                FollowUpReminderRow.id == str(reminder_id),
                FollowUpReminderRow.organization_id == str(organization_id),
            )
        )
        row = result.scalars().first()
        if not row:
            return None
        now = datetime.now(UTC)
        row.state = state.value
        row.last_actor = actor
        row.last_action_at = now
        row.updated_at = now
        if due_date is not None:
            row.due_date = due_date.isoformat()
        self._session.add(row)
        await self._session.flush()
        return row_to_reminder(row)


class ReminderHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        reminder_id: UUID,
        lead_id: UUID,
        kind: str,
        actor: str,
        note: str = "",
        from_due_date: str = "",
        to_due_date: str = "",
    ) -> ReminderHistoryEntry:
        now = datetime.now(UTC)
        row = ReminderHistoryRow(
            id=str(uuid4()),
            reminder_id=str(reminder_id),
            lead_id=str(lead_id),
            kind=kind,
            actor=actor,
            note=note,
            from_due_date=from_due_date,
            to_due_date=to_due_date,
            created_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_history(row)
