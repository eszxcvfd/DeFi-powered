from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LeadActivitySchema(BaseModel):
    id: UUID
    kind: str
    actor: str
    body: str = ""
    from_stage: str = ""
    to_stage: str = ""
    created_at: datetime
    outcome_type: str = ""
    occurred_at: datetime | None = None
    linked_content_draft_id: str | None = None


class LeadReminderSummarySchema(BaseModel):
    has_reminder: bool = False
    state: str | None = None
    due_date: str | None = None
    reminder_id: str | None = None


class LatestLeadOutcomeSchema(BaseModel):
    outcome_type: str
    occurred_at: datetime
    actor: str
    activity_id: UUID
    linked_content_draft_id: UUID | None = None
    notes: str = ""


class LeadSummarySchema(BaseModel):
    id: UUID
    display_name: str
    company: str = ""
    title: str = ""
    owner: str = ""
    stage: str
    discovery_source: str = ""
    campaign_id: UUID | None = None
    event_id: UUID | None = None
    follow_up_date: date | None = None
    updated_at: datetime
    reminder: LeadReminderSummarySchema = Field(default_factory=LeadReminderSummarySchema)
    event_title: str = ""
    region: str = ""
    latest_outcome: LatestLeadOutcomeSchema | None = None


class LeadDetailSchema(LeadSummarySchema):
    public_url: str = ""
    interests: str = ""
    pain_points: str = ""
    lawful_basis_note: str = ""
    notes: str = ""
    manual_entry_note: str = ""
    origin_kind: str
    created_by: str
    created_at: datetime
    recent_activity: list[LeadActivitySchema] = Field(default_factory=list)


class LeadCreateSchema(BaseModel):
    display_name: str
    company: str = ""
    title: str = ""
    public_url: str = ""
    discovery_source: str = ""
    event_id: UUID | None = None
    campaign_id: UUID | None = None
    interests: str = ""
    pain_points: str = ""
    owner: str = ""
    lawful_basis_note: str = ""
    follow_up_date: date | None = None
    notes: str = ""
    manual_entry_note: str = ""
    origin_kind: str = "event"
    email: str = ""
    external_id: str = ""


class LeadPatchSchema(BaseModel):
    owner: str | None = None
    notes: str | None = None
    follow_up_date: date | None = None
    stage: str | None = None
    activity_note: str | None = None
    title: str | None = None
    company: str | None = None


class RecordLeadOutcomeSchema(BaseModel):
    outcome_type: str
    occurred_at: datetime | None = None
    notes: str = ""
    linked_content_draft_id: UUID | None = None
    linked_event_id: UUID | None = None


class EventLeadLinkSchema(BaseModel):
    linked_count: int = 0
    linked_lead_ids: list[str] = Field(default_factory=list)
    has_linked_lead: bool = False
