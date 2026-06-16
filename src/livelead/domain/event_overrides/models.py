"""Event manual override domain types (US-031).

The slice keeps the manual-override surface narrow: a small bounded
allowlist of canonical event fields, an append-only change history,
and a projection that explains which effective canonical field values
come from a manual override versus the latest source-backed value.

The allowlist is the single source of truth for what a reviewer can
edit. The ingest path in ``application.events.ingest`` consults the
same allowlist to decide which fields are protected from later
automatic normalization, so the protection rule cannot drift from
the editable-field contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class OverrideValueKind(StrEnum):
    """Storage kind for an override value.

    The canonical event row holds two text-friendly representations
    and one timestamp-shaped field. The kind tells the projection
    layer how to render or round-trip the value.
    """

    TEXT = "text"
    URL = "url"
    TIMESTAMP = "timestamp"


class OverrideHistoryAction(StrEnum):
    """Audit-stable action names for change history rows."""

    UPSERTED = "upserted"
    CLEARED = "cleared"
    DENIED = "denied"
    PROTECTED_SKIPPED = "protected_skipped"


# ----------------------------------------------------------------------
# Field allowlist
# ----------------------------------------------------------------------
ALLOWED_OVERRIDE_FIELDS: frozenset[str] = frozenset(
    {
        "canonical_title",
        "description",
        "organizer",
        "region",
        "starts_at",
        "source_url",
    }
)

_FIELD_KIND: dict[str, OverrideValueKind] = {
    "canonical_title": OverrideValueKind.TEXT,
    "description": OverrideValueKind.TEXT,
    "organizer": OverrideValueKind.TEXT,
    "region": OverrideValueKind.TEXT,
    "source_url": OverrideValueKind.URL,
    "starts_at": OverrideValueKind.TIMESTAMP,
}


def is_allowed_override_field(field: str) -> bool:
    return field in ALLOWED_OVERRIDE_FIELDS


def value_kind_for(field: str) -> OverrideValueKind:
    return _FIELD_KIND.get(field, OverrideValueKind.TEXT)


def parse_override_value(field: str, raw: Any) -> str:
    """Normalize an override payload into the stored string form.

    Returns the string that should be persisted in
    ``EventManualOverrideRow.override_value`` and the event row.
    Raises ``ValueError`` for shapes the editable-field contract
    rejects.
    """

    if raw is None:
        return ""
    if field == "starts_at":
        if not isinstance(raw, str):
            raise ValueError("starts_at must be an ISO-8601 string or null")
        candidate = raw.strip()
        if not candidate:
            return ""
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError as exc:
            raise ValueError("starts_at must be an ISO-8601 timestamp") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=parsed.astimezone().tzinfo)  # noqa: UP017 - safe local
        return parsed.astimezone().isoformat()  # noqa: UP017
    if field == "source_url":
        if not isinstance(raw, str):
            raise ValueError("source_url must be a string")
        candidate = raw.strip()
        if not candidate:
            return ""
        if not (candidate.startswith("http://") or candidate.startswith("https://")):
            raise ValueError("source_url must start with http:// or https://")
        return candidate
    if field in {"canonical_title", "description", "organizer", "region"}:
        if not isinstance(raw, str):
            raise ValueError(f"{field} must be a string")
        return raw.strip()
    raise ValueError(f"unsupported override field: {field}")


def format_override_value(field: str, stored: str) -> Any:
    """Project a stored override value back to the API shape.

    Text and URL fields return the raw string. ``starts_at`` returns
    a ``datetime`` parsed from the stored ISO string. An empty
    string round-trips to ``None`` for the timestamp field so the UI
    can show "no override" without an extra branch.
    """

    if stored == "":
        return None
    if field == "starts_at":
        candidate = stored
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        return datetime.fromisoformat(candidate)
    return stored


# ----------------------------------------------------------------------
# Domain dataclasses
# ----------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class EventManualOverride:
    id: UUID
    organization_id: UUID
    event_id: UUID
    field: str
    source_backed_value: str
    override_value: str
    value_kind: OverrideValueKind
    note: str
    actor_id: str
    actor_role: str
    created_at: datetime
    updated_at: datetime

    def to_payload(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "override_value": format_override_value(self.field, self.override_value),
            "source_backed_value": format_override_value(self.field, self.source_backed_value),
            "value_kind": self.value_kind.value,
            "note": self.note,
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "updated_at": self.updated_at.isoformat().replace("+00:00", "Z"),
        }


@dataclass(frozen=True, slots=True)
class EventChangeHistoryEntry:
    id: UUID
    organization_id: UUID
    event_id: UUID
    action: OverrideHistoryAction
    field: str
    value_kind: OverrideValueKind
    prior_value: str
    new_value: str
    source_backed_value: str
    actor_id: str
    actor_role: str
    reason: str
    created_at: datetime

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "action": self.action.value,
            "field": self.field,
            "value_kind": self.value_kind.value,
            "prior_value": format_override_value(self.field, self.prior_value),
            "new_value": format_override_value(self.field, self.new_value),
            "source_backed_value": format_override_value(
                self.field, self.source_backed_value
            ),
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "reason": self.reason,
            "created_at": self.created_at.isoformat().replace("+00:00", "Z"),
        }


@dataclass(frozen=True, slots=True)
class FieldProvenance:
    """Per-field provenance for one canonical event."""

    field: str
    effective_value: Any
    source_value: Any
    is_overridden: bool
    actor_id: str = ""
    actor_role: str = ""
    updated_at: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "effective_value": self.effective_value,
            "source_value": self.source_value,
            "is_overridden": self.is_overridden,
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True, slots=True)
class EventOverrideUpdateResult:
    event_id: UUID
    applied_fields: list[str]
    skipped_fields: list[tuple[str, str]]  # (field, reason)
    history: list[EventChangeHistoryEntry]
    overrides: list[EventManualOverride]


@dataclass(frozen=True, slots=True)
class EventOverrideClearResult:
    event_id: UUID
    field: str
    restored_value: Any
    history: list[EventChangeHistoryEntry]


__all__ = [
    "ALLOWED_OVERRIDE_FIELDS",
    "EventChangeHistoryEntry",
    "EventManualOverride",
    "EventOverrideClearResult",
    "EventOverrideUpdateResult",
    "FieldProvenance",
    "OverrideHistoryAction",
    "OverrideValueKind",
    "format_override_value",
    "is_allowed_override_field",
    "parse_override_value",
    "value_kind_for",
]
