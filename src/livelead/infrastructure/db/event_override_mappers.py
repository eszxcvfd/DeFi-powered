"""Map event override ORM rows to domain dataclasses (US-031)."""

from __future__ import annotations

from uuid import UUID

from livelead.domain.event_overrides.models import (
    EventChangeHistoryEntry,
    EventManualOverride,
    OverrideHistoryAction,
    OverrideValueKind,
)
from livelead.infrastructure.db.models import EventChangeHistoryRow, EventManualOverrideRow


def row_to_override(row: EventManualOverrideRow) -> EventManualOverride:
    return EventManualOverride(
        id=UUID(row.id),
        organization_id=UUID(row.organization_id),
        event_id=UUID(row.event_id),
        field=row.field,
        source_backed_value=row.source_backed_value or "",
        override_value=row.override_value or "",
        value_kind=OverrideValueKind(row.value_kind or "text"),
        note=row.note or "",
        actor_id=row.actor_id or "",
        actor_role=row.actor_role or "",
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def row_to_history(row: EventChangeHistoryRow) -> EventChangeHistoryEntry:
    return EventChangeHistoryEntry(
        id=UUID(row.id),
        organization_id=UUID(row.organization_id),
        event_id=UUID(row.event_id),
        action=OverrideHistoryAction(row.action),
        field=row.field,
        value_kind=OverrideValueKind(row.value_kind or "text"),
        prior_value=row.prior_value or "",
        new_value=row.new_value or "",
        source_backed_value=row.source_backed_value or "",
        actor_id=row.actor_id or "",
        actor_role=row.actor_role or "",
        reason=row.reason or "",
        created_at=row.created_at,
    )


__all__ = ["row_to_history", "row_to_override"]
