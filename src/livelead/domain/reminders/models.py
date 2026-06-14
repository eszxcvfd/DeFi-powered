"""Follow-up reminder domain types (US-013)."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID


class ReminderState(StrEnum):
    SCHEDULED = "scheduled"
    DUE = "due"
    OVERDUE = "overdue"
    COMPLETED = "completed"
    RESCHEDULED = "rescheduled"


class ReminderActionKind(StrEnum):
    CREATED = "created"
    REFRESHED = "refreshed"
    COMPLETED = "completed"
    RESCHEDULED = "rescheduled"
    DISMISSED = "dismissed"


@dataclass(frozen=True, slots=True)
class FollowUpReminder:
    id: UUID
    organization_id: UUID
    lead_id: UUID
    owner: str
    due_date: date
    state: ReminderState
    last_actor: str
    last_action_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ReminderHistoryEntry:
    id: UUID
    reminder_id: UUID
    lead_id: UUID
    kind: ReminderActionKind
    actor: str
    note: str
    from_due_date: str
    to_due_date: str
    created_at: datetime