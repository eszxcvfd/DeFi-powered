"""Normalize discovery findings into canonical events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from livelead.domain.events.models import CanonicalEvent, EventSourceObservation


@dataclass(frozen=True, slots=True)
class MockFinding:
    title: str
    source_url: str
    description: str = ""
    organizer: str = ""
    region: str = ""


def build_canonical_from_finding(
    *,
    organization_id: UUID,
    campaign_id: UUID,
    source_id: UUID,
    finding: MockFinding,
    observed_at: datetime | None = None,
) -> tuple[CanonicalEvent, EventSourceObservation]:
    now = observed_at or datetime.now(UTC)
    event_id = uuid4()
    obs_id = uuid4()
    event = CanonicalEvent(
        id=event_id,
        organization_id=organization_id,
        campaign_id=campaign_id,
        canonical_title=finding.title,
        source_url=finding.source_url,
        observed_at=now,
        description=finding.description,
        organizer=finding.organizer,
        region=finding.region,
        starts_at=now + timedelta(days=14 + (hash(str(event_id)) % 30)),
        metadata_json={"format": "webinar" if "webinar" in finding.title.lower() else "event"},
        created_at=now,
    )
    obs = EventSourceObservation(
        id=obs_id,
        event_id=event_id,
        source_id=source_id,
        source_url=finding.source_url,
        observed_at=now,
        raw_title=finding.title,
        external_id=finding.source_url.rsplit("/", 1)[-1],
    )
    return event, obs