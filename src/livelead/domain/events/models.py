"""Canonical event types — no framework imports."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EventSourceObservation:
    id: UUID
    event_id: UUID
    source_id: UUID
    source_url: str
    observed_at: datetime
    raw_title: str
    external_id: str | None = None
    discovery_job_id: str | None = None


@dataclass(frozen=True, slots=True)
class CanonicalEvent:
    id: UUID
    organization_id: UUID
    campaign_id: UUID
    canonical_title: str
    source_url: str
    observed_at: datetime
    description: str = ""
    organizer: str = ""
    region: str = ""
    starts_at: datetime | None = None
    metadata_json: dict[str, str] = field(default_factory=dict)
    discovery_job_id: str | None = None
    confidence_summary: str = "medium"
    created_at: datetime | None = None