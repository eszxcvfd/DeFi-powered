from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class ReminderQueueItemSchema(BaseModel):
    id: UUID
    lead_id: UUID
    lead_display_name: str
    lead_company: str = ""
    lead_stage: str
    owner: str
    due_date: date
    state: str
    last_actor: str = ""
    last_action_at: datetime | None = None


class ReminderActionSchema(BaseModel):
    note: str = ""


class ReminderRescheduleSchema(BaseModel):
    due_date: date
    note: str = ""


class InAppReminderAlertSchema(BaseModel):
    reminder_id: str
    lead_id: str
    lead_display_name: str
    due_date: str
    state: str
    owner: str


class LeadReminderSummarySchema(BaseModel):
    has_reminder: bool = False
    state: str | None = None
    due_date: str | None = None
    reminder_id: str | None = None
