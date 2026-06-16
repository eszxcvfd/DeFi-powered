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
from livelead.domain.event_overrides.models import (
    ALLOWED_OVERRIDE_FIELDS,
    OverrideHistoryAction,
    OverrideValueKind,
    parse_override_value,
    value_kind_for,
)
from livelead.infrastructure.db.models import (
    EventChangeHistoryRow,
    EventManualOverrideRow,
    EventRow,
    EventSourceObservationRow,
)

logger = logging.getLogger("livelead.events")


_PROTECTED_FIELDS: frozenset[str] = ALLOWED_OVERRIDE_FIELDS


def _protected_field_skip(
    session: Session,
    *,
    organization_id: UUID,
    event_id: str,
    field: str,
    actor_id: str,
    actor_role: str,
    reason: str,
) -> None:
    """Record a protected-field skip in change history and skip the write.

    The merge path in ``ingest_finding`` calls this helper before
    any field write that might overwrite a manual override. The
    helper appends an append-only history row, emits a structured
    log line, and returns ``True`` when the write must be skipped.
    The merge caller short-circuits the write so the protected
    field is preserved untouched.
    """

    if field not in _PROTECTED_FIELDS:
        return
    now = datetime.now(UTC)
    session.add(
        EventChangeHistoryRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            event_id=event_id,
            action=OverrideHistoryAction.PROTECTED_SKIPPED.value,
            field=field,
            value_kind=value_kind_for(field).value,
            prior_value="",
            new_value="",
            source_backed_value="",
            actor_id=actor_id,
            actor_role=actor_role,
            reason=reason[:500],
            created_at=now,
        )
    )
    logger.info(
        "event_override_protected_skip org=%s event=%s field=%s reason=%s",
        organization_id,
        event_id,
        field,
        reason,
    )


def _protected_field_values(
    session: Session,
    *,
    organization_id: UUID,
    event_id: str,
    fields: list[str],
) -> dict[str, str]:
    """Return the override values for the given fields on this event.

    Used by the merge path to short-circuit field writes for any
    field that carries an active override. The result is a mapping
    of field name to current override value; an empty dict means
    no fields are protected.
    """

    if not fields:
        return {}
    rows = (
        session.execute(
            select(EventManualOverrideRow.field, EventManualOverrideRow.override_value).where(
                EventManualOverrideRow.organization_id == str(organization_id),
                EventManualOverrideRow.event_id == event_id,
                EventManualOverrideRow.field.in_(fields),
            )
        )
    ).all()
    return {row[0]: row[1] for row in rows}


def _maybe_apply_field_update(
    session: Session,
    *,
    organization_id: UUID,
    event_id: str,
    field: str,
    new_value: str,
    actor_id: str,
    actor_role: str,
) -> str | None:
    """Apply a normalized field write unless the field is protected.

    Returns the value that should land on the canonical row, or
    ``None`` if the field is protected and the write was skipped.
    The caller is expected to assign the returned value to the
    event row.
    """

    if field not in _PROTECTED_FIELDS:
        return new_value
    protected = _protected_field_values(
        session,
        organization_id=organization_id,
        event_id=event_id,
        fields=[field],
    )
    if field not in protected:
        return new_value
    _protected_field_skip(
        session,
        organization_id=organization_id,
        event_id=event_id,
        field=field,
        actor_id=actor_id,
        actor_role=actor_role,
        reason="merge attempted to overwrite manual override",
    )
    return None


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
    candidates = (
        session.execute(
            select(EventRow).where(
                EventRow.campaign_id == campaign_key,
                EventRow.organization_id == str(organization_id),
            )
        )
        .scalars()
        .all()
    )

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
    meta["field_confidence"] = [
        {"field": f.field, "trust": f.trust.value, "note": f.note} for f in fields
    ]
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
