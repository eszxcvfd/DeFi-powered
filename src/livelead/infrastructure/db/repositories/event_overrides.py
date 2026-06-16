"""Event override persistence (US-031).

The repository owns every read and write for
``event_manual_overrides`` and ``event_change_history``. All
methods take ``organization_id`` first so tenant isolation is
mandatory at the data layer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from livelead.domain.event_overrides.models import (
    ALLOWED_OVERRIDE_FIELDS,
    EventChangeHistoryEntry,
    EventManualOverride,
    OverrideHistoryAction,
    OverrideValueKind,
    parse_override_value,
    value_kind_for,
)
from livelead.infrastructure.db.event_override_mappers import row_to_history, row_to_override
from livelead.infrastructure.db.models import (
    EventChangeHistoryRow,
    EventManualOverrideRow,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _serialize_text(value: str) -> str:
    return value or ""


def _serialize_timestamp(value: str) -> str:
    if not value:
        return ""
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=parsed.tzinfo)
    return parsed.isoformat()


def _coerce_for_storage(field: str, raw: str) -> str:
    """Normalize the override string for storage.

    The HTTP layer already ran ``parse_override_value`` so the input
    is a clean string. This helper only re-normalizes the timestamp
    path to keep the canonical event row and the override row in
    the same shape.
    """

    if value_kind_for(field) is OverrideValueKind.TIMESTAMP:
        return _serialize_timestamp(raw)
    return _serialize_text(raw)


class EventManualOverrideRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self, organization_id: UUID, event_id: UUID, field: str
    ) -> EventManualOverride | None:
        result = await self._session.execute(
            select(EventManualOverrideRow).where(
                and_(
                    EventManualOverrideRow.organization_id == str(organization_id),
                    EventManualOverrideRow.event_id == str(event_id),
                    EventManualOverrideRow.field == field,
                )
            )
        )
        row = result.scalar_one_or_none()
        return row_to_override(row) if row else None

    async def list_for_event(
        self, organization_id: UUID, event_id: UUID
    ) -> list[EventManualOverride]:
        result = await self._session.execute(
            select(EventManualOverrideRow)
            .where(
                and_(
                    EventManualOverrideRow.organization_id == str(organization_id),
                    EventManualOverrideRow.event_id == str(event_id),
                )
            )
            .order_by(EventManualOverrideRow.field.asc())
        )
        return [row_to_override(r) for r in result.scalars().all()]

    async def list_protected_fields(
        self, organization_id: UUID, event_id: UUID
    ) -> set[str]:
        result = await self._session.execute(
            select(EventManualOverrideRow.field).where(
                and_(
                    EventManualOverrideRow.organization_id == str(organization_id),
                    EventManualOverrideRow.event_id == str(event_id),
                )
            )
        )
        return {row[0] for row in result.all()}

    async def upsert(
        self,
        *,
        organization_id: UUID,
        event_id: UUID,
        field: str,
        source_backed_value: str,
        override_value: str,
        value_kind: OverrideValueKind,
        note: str,
        actor_id: str,
        actor_role: str,
    ) -> EventManualOverride:
        if field not in ALLOWED_OVERRIDE_FIELDS:
            raise ValueError(f"unsupported override field: {field}")
        normalized_source = _coerce_for_storage(field, source_backed_value)
        normalized_override = _coerce_for_storage(field, override_value)
        now = _now()
        existing = await self.get(organization_id, event_id, field)
        if existing:
            result = await self._session.execute(
                select(EventManualOverrideRow).where(
                    EventManualOverrideRow.id == str(existing.id)
                )
            )
            row = result.scalar_one()
            # The source-backed baseline only changes when the
            # existing override was already in place. If a
            # downstream rediscovery ran while the override was
            # active, the canonical row may have moved on, but
            # the override still records what we want to restore
            # to. The caller (service layer) decides what
            # "source-backed" means for this write.
            row.override_value = normalized_override
            row.note = note[:500]
            row.actor_id = actor_id
            row.actor_role = actor_role
            row.updated_at = now
            self._session.add(row)
            await self._session.flush()
            return row_to_override(row)
        row = EventManualOverrideRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            event_id=str(event_id),
            field=field,
            source_backed_value=normalized_source,
            override_value=normalized_override,
            value_kind=value_kind.value,
            note=note[:500],
            actor_id=actor_id,
            actor_role=actor_role,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_override(row)

    async def delete(
        self, organization_id: UUID, event_id: UUID, field: str
    ) -> bool:
        result = await self._session.execute(
            select(EventManualOverrideRow).where(
                and_(
                    EventManualOverrideRow.organization_id == str(organization_id),
                    EventManualOverrideRow.event_id == str(event_id),
                    EventManualOverrideRow.field == field,
                )
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self._session.delete(row)
        await self._session.flush()
        return True


class EventChangeHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        organization_id: UUID,
        event_id: UUID,
        action: OverrideHistoryAction,
        field: str,
        value_kind: OverrideValueKind,
        prior_value: str,
        new_value: str,
        source_backed_value: str,
        actor_id: str,
        actor_role: str,
        reason: str = "",
    ) -> EventChangeHistoryEntry:
        row = EventChangeHistoryRow(
            id=str(uuid4()),
            organization_id=str(organization_id),
            event_id=str(event_id),
            action=action.value,
            field=field,
            value_kind=value_kind.value,
            prior_value=_coerce_for_storage(field, prior_value),
            new_value=_coerce_for_storage(field, new_value),
            source_backed_value=_coerce_for_storage(field, source_backed_value),
            actor_id=actor_id,
            actor_role=actor_role,
            reason=reason[:500],
            created_at=_now(),
        )
        self._session.add(row)
        await self._session.flush()
        return row_to_history(row)

    async def list_for_event(
        self,
        organization_id: UUID,
        event_id: UUID,
        *,
        limit: int = 100,
    ) -> list[EventChangeHistoryEntry]:
        result = await self._session.execute(
            select(EventChangeHistoryRow)
            .where(
                and_(
                    EventChangeHistoryRow.organization_id == str(organization_id),
                    EventChangeHistoryRow.event_id == str(event_id),
                )
            )
            .order_by(desc(EventChangeHistoryRow.created_at), desc(EventChangeHistoryRow.id))
            .limit(max(1, min(int(limit), 500)))
        )
        return [row_to_history(r) for r in result.scalars().all()]


__all__ = [
    "EventChangeHistoryRepository",
    "EventManualOverrideRepository",
]


# Re-export for downstream use without an extra import path.
_ = (parse_override_value, Iterable)  # silence linters; Iterable typing retained
