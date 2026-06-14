from datetime import date
from uuid import UUID

from livelead.domain.reminders.models import (
    FollowUpReminder,
    ReminderActionKind,
    ReminderHistoryEntry,
    ReminderState,
)
from livelead.infrastructure.db.models import FollowUpReminderRow, ReminderHistoryRow


def _parse_date(raw: str) -> date:
    return date.fromisoformat(raw)


def row_to_reminder(row: FollowUpReminderRow) -> FollowUpReminder:
    return FollowUpReminder(
        id=UUID(row.id),
        organization_id=UUID(row.organization_id),
        lead_id=UUID(row.lead_id),
        owner=row.owner or "",
        due_date=_parse_date(row.due_date),
        state=ReminderState(row.state),
        last_actor=row.last_actor or "",
        last_action_at=row.last_action_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def row_to_history(row: ReminderHistoryRow) -> ReminderHistoryEntry:
    return ReminderHistoryEntry(
        id=UUID(row.id),
        reminder_id=UUID(row.reminder_id),
        lead_id=UUID(row.lead_id),
        kind=ReminderActionKind(row.kind),
        actor=row.actor,
        note=row.note or "",
        from_due_date=row.from_due_date or "",
        to_due_date=row.to_due_date or "",
        created_at=row.created_at,
    )