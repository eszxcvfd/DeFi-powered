"""Event persistence."""

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.events.models import CanonicalEvent, EventSourceObservation
from livelead.infrastructure.db.event_mappers import row_to_event, row_to_observation
from livelead.infrastructure.db.models import EventRow, EventSourceObservationRow


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_organization(
        self,
        organization_id: UUID,
        *,
        q: str | None = None,
        limit: int = 100,
    ) -> list[CanonicalEvent]:
        stmt = select(EventRow).where(EventRow.organization_id == str(organization_id))
        if q and q.strip():
            like = f"%{q.strip().lower()}%"
            stmt = stmt.where(func.lower(EventRow.canonical_title).like(like))
        stmt = stmt.order_by(EventRow.observed_at.desc()).limit(max(1, min(limit, 500)))
        result = await self._session.execute(stmt)
        return [row_to_event(r) for r in result.scalars().all()]

    async def list_for_campaign(
        self,
        campaign_id: UUID,
        organization_id: UUID,
        *,
        discovery_job_id: UUID | None = None,
        source_id: UUID | None = None,
        q: str | None = None,
    ) -> list[CanonicalEvent]:
        stmt = select(EventRow).where(
            EventRow.campaign_id == str(campaign_id),
            EventRow.organization_id == str(organization_id),
        )
        if discovery_job_id:
            stmt = stmt.where(EventRow.discovery_job_id == str(discovery_job_id))
        if source_id:
            stmt = stmt.where(
                EventRow.id.in_(
                    select(EventSourceObservationRow.event_id).where(
                        EventSourceObservationRow.source_id == str(source_id)
                    )
                )
            )
        if q and q.strip():
            like = f"%{q.strip().lower()}%"
            stmt = stmt.where(func.lower(EventRow.canonical_title).like(like))
        stmt = stmt.order_by(EventRow.observed_at.desc())
        result = await self._session.execute(stmt)
        return [row_to_event(r) for r in result.scalars().all()]

    async def observation_counts(self, event_ids: list[UUID]) -> dict[UUID, int]:
        if not event_ids:
            return {}
        ids = [str(i) for i in event_ids]
        result = await self._session.execute(
            select(EventSourceObservationRow.event_id, func.count())
            .where(EventSourceObservationRow.event_id.in_(ids))
            .group_by(EventSourceObservationRow.event_id)
        )
        return {UUID(row[0]): int(row[1]) for row in result.all()}

    async def distinct_source_ids(self, event_id: UUID) -> list[UUID]:
        result = await self._session.execute(
            select(EventSourceObservationRow.source_id)
            .where(EventSourceObservationRow.event_id == str(event_id))
            .distinct()
        )
        return [UUID(s) for s in result.scalars().all()]

    async def get(self, event_id: UUID, organization_id: UUID) -> CanonicalEvent | None:
        result = await self._session.execute(
            select(EventRow).where(
                EventRow.id == str(event_id),
                EventRow.organization_id == str(organization_id),
            )
        )
        row = result.scalar_one_or_none()
        return row_to_event(row) if row else None

    async def get_row(self, event_id: UUID, organization_id: UUID) -> EventRow | None:
        result = await self._session.execute(
            select(EventRow).where(
                EventRow.id == str(event_id),
                EventRow.organization_id == str(organization_id),
            )
        )
        return result.scalar_one_or_none()

    async def list_observations(self, event_id: UUID) -> list[EventSourceObservation]:
        result = await self._session.execute(
            select(EventSourceObservationRow)
            .where(EventSourceObservationRow.event_id == str(event_id))
            .order_by(EventSourceObservationRow.observed_at.desc())
        )
        return [row_to_observation(r) for r in result.scalars().all()]

    async def add_event_with_observation(
        self,
        event: CanonicalEvent,
        observation: EventSourceObservation,
    ) -> CanonicalEvent:
        from livelead.domain.events.confidence import confidence_for_new_event, summary_confidence

        meta = dict(event.metadata_json)
        if "field_confidence" not in meta:
            fields = confidence_for_new_event(
                has_organizer=bool(event.organizer),
                has_region=bool(event.region),
                has_starts_at=event.starts_at is not None,
            )
            meta["field_confidence"] = [
                {"field": f.field, "trust": f.trust.value, "note": f.note} for f in fields
            ]
            meta["confidence_summary"] = summary_confidence(fields)
            meta.setdefault("merge_notes", [])
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
        )
        obs_row = EventSourceObservationRow(
            id=str(observation.id),
            event_id=str(observation.event_id),
            source_id=str(observation.source_id),
            source_url=observation.source_url,
            observed_at=observation.observed_at,
            raw_title=observation.raw_title,
            external_id=observation.external_id,
        )
        self._session.add(row)
        self._session.add(obs_row)
        await self._session.flush()
        return row_to_event(row)

    async def exists_by_source_url(self, campaign_id: UUID, source_url: str) -> bool:
        result = await self._session.execute(
            select(EventRow.id).where(
                EventRow.campaign_id == str(campaign_id),
                EventRow.source_url == source_url,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_locked_field_values(
        self, organization_id: UUID, event_id: UUID, fields: list[str]
    ) -> dict[str, str]:
        """Return the current override values for any field in ``fields``.

        Used by the ingest path to skip writes for protected fields
        during rediscovery. Returns an empty dict when no fields are
        protected.
        """

        if not fields:
            return {}
        from livelead.infrastructure.db.models import EventManualOverrideRow

        result = await self._session.execute(
            select(EventManualOverrideRow.field, EventManualOverrideRow.override_value).where(
                and_(
                    EventManualOverrideRow.organization_id == str(organization_id),
                    EventManualOverrideRow.event_id == str(event_id),
                    EventManualOverrideRow.field.in_(fields),
                )
            )
        )
        return {row[0]: row[1] for row in result.all()}


def provenance_from_metadata_json(raw: str) -> dict:
    meta = json.loads(raw or "{}")
    return {
        "confidence_summary": meta.get("confidence_summary", "medium"),
        "field_confidence": meta.get("field_confidence", []),
        "merge_notes": meta.get("merge_notes", []),
    }
