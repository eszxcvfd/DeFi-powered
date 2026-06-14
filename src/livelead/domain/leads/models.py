"""Lead pipeline domain types (US-012)."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID


class LeadStage(StrEnum):
    NEWLY_DISCOVERED = "newly_discovered"
    WATCHED = "watched"
    CONNECTED = "connected"
    MESSAGE_SENT = "message_sent"
    RESPONDED = "responded"
    MEETING_SCHEDULED = "meeting_scheduled"
    IN_DISCUSSION = "in_discussion"
    OPPORTUNITY = "opportunity"
    NOT_FIT = "not_fit"


class LeadOriginKind(StrEnum):
    EVENT = "event"
    MANUAL = "manual"


class LeadActivityKind(StrEnum):
    CREATED = "created"
    NOTE = "note"
    STAGE_CHANGED = "stage_changed"
    FIELD_UPDATED = "field_updated"


@dataclass(frozen=True, slots=True)
class LeadRecord:
    id: UUID
    organization_id: UUID
    campaign_id: UUID | None
    display_name: str
    company: str
    title: str
    public_url: str
    discovery_source: str
    event_id: UUID | None
    interests: str
    pain_points: str
    owner: str
    stage: LeadStage
    lawful_basis_note: str
    follow_up_date: date | None
    notes: str
    manual_entry_note: str
    origin_kind: LeadOriginKind
    email_hash: str
    external_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class LeadActivityEntry:
    id: UUID
    lead_id: UUID
    kind: LeadActivityKind
    actor: str
    body: str
    from_stage: str
    to_stage: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class LeadDuplicateMatch:
    matched_lead_id: UUID
    reason: str