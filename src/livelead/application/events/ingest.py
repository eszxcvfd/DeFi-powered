"""Ingest normalized findings with deduplication (sync worker)."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from livelead.domain.events.confidence import (
    confidence_after_merge,
    confidence_for_new_event,
    summary_confidence,
)
from livelead.domain.events.deduplication import decide_merge
from livelead.domain.events.normalize import MockFinding, build_canonical_from_finding
from livelead.infrastructure.db.models import EventRow, EventSourceObservationRow

logger = logging.getLogger("livelead.events")


def _load_confidence(row: EventRow) -> list[dict]:
    meta = json.loads(row.metadata_json or "{}")
    raw = meta.get("field_confidence", [])
    return raw if isinstance(raw, list) else []


def _save_confidence(session: Session, row: EventRow, fields: list) -> None:
    meta = json.loads(row.metadata_json or "{}")
    meta["field_confidence"] = [
        {"field": f.field, "trust": f.trust.value, "note": f.note} for f in fields
    ]
    meta["confidence_summary"] = summary_confidence(fields)
    row.metadata_json = json.dumps(meta)
    session.add(row)


def _append_merge_note(session: Session, row: EventRow, note: str) -> None:
    meta = json.loads(row.metadata_json or "{}")
    notes = meta.get("merge_notes", [])
    if not isinstance(notes, list):
        notes = []
    notes.append({"at": datetime.now(UTC).isoformat(), "note": note})
    meta["merge_notes"] = notes[-10:]
    row.metadata_json = json.dumps(meta)
    session.add(row)


def ingest_finding(
    session: Session,
    *,
    organization_id: UUID,
    campaign_id: UUID,
    source_id: UUID,
    finding: MockFinding,
    discovery_job_id: str | None = None,
) -> tuple[str, str]:
    """Returns (event_id, action) where action is created|merged|skipped_duplicate_obs."""
    campaign_key = str(campaign_id)
    candidates = session.execute(
        select(EventRow).where(
            EventRow.campaign_id == campaign_key,
            EventRow.organization_id == str(organization_id),
        )
    ).scalars().all()

    for existing in candidates:
        decision = decide_merge(
            finding_title=finding.title,
            finding_region=finding.region,
            finding_source_url=finding.source_url,
            existing_canonical_title=existing.canonical_title,
            existing_region=existing.region or "",
            existing_source_url=existing.source_url,
        )
        if not decision.should_merge:
            continue

        dup_obs = session.execute(
            select(EventSourceObservationRow.id).where(
                EventSourceObservationRow.event_id == existing.id,
                EventSourceObservationRow.source_id == str(source_id),
                EventSourceObservationRow.source_url == finding.source_url,
            )
        ).scalar_one_or_none()
        if dup_obs:
            return existing.id, "skipped_duplicate_obs"

        obs_id = str(uuid4())
        now = datetime.now(UTC)
        session.add(
            EventSourceObservationRow(
                id=obs_id,
                event_id=existing.id,
                source_id=str(source_id),
                source_url=finding.source_url,
                observed_at=now,
                raw_title=finding.title,
                external_id=finding.source_url.rsplit("/", 1)[-1],
                discovery_job_id=discovery_job_id,
            )
        )
        _append_merge_note(session, existing, decision.explanation)
        _save_confidence(session, existing, confidence_after_merge())
        logger.info(
            "event_merge_decision event_id=%s reason=%s source_id=%s",
            existing.id,
            decision.reason.value,
            source_id,
        )
        return existing.id, "merged"

    event, obs = build_canonical_from_finding(
        organization_id=organization_id,
        campaign_id=campaign_id,
        source_id=source_id,
        finding=finding,
    )
    fields = confidence_for_new_event(
        has_organizer=bool(finding.organizer),
        has_region=bool(finding.region),
        has_starts_at=True,
    )
    meta = dict(event.metadata_json)
    meta["field_confidence"] = [{"field": f.field, "trust": f.trust.value, "note": f.note} for f in fields]
    meta["confidence_summary"] = summary_confidence(fields)
    meta["merge_notes"] = []

    row = EventRow(
        id=str(event.id),
        organization_id=str(event.organization_id),
        campaign_id=str(event.campaign_id),
        canonical_title=event.canonical_title,
        source_url=event.source_url,
        observed_at=event.observed_at,
        description=event.description,
        organizer=event.organizer,
        region=event.region,
        starts_at=event.starts_at,
        metadata_json=json.dumps(meta),
        created_at=event.created_at or datetime.now(UTC),
        discovery_job_id=discovery_job_id,
    )
    session.add(row)
    session.add(
        EventSourceObservationRow(
            id=str(obs.id),
            event_id=str(obs.event_id),
            source_id=str(obs.source_id),
            source_url=obs.source_url,
            observed_at=obs.observed_at,
            raw_title=obs.raw_title,
            external_id=obs.external_id,
            discovery_job_id=discovery_job_id,
        )
    )
    logger.info("event_created event_id=%s campaign_id=%s", row.id, campaign_key)
    return row.id, "created"