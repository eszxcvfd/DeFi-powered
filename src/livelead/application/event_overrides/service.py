"""Event manual override application service (US-031).

The service owns:

- Field-allowlist validation and authorization gating.
- Reading and writing the canonical event row alongside override
  records so a reviewer can never see a half-applied edit.
- Building the per-field provenance projection that event detail
  responses use to mark overridden fields.
- Producing a protected-field set that the ingest path consults so
  later rediscovery cannot silently overwrite a manual correction.
- Emitting audit and structured log evidence for every successful
  edit, clear, denied edit, and protected-field skip.

The service never mutates source observations. It does not own the
read-model refresh for derived views (score, reminder, watchlist);
those subscribe to change-history rows on their own cadence.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from livelead.application.audit.audit_service import (
    AuditService,
    make_actor_from_role,
    make_context,
)
from livelead.domain.audit.enums import (
    AuditAction,
    AuditOutcome,
    AuditTargetType,
)
from livelead.domain.audit.model import AuditTarget
from livelead.domain.event_overrides.models import (
    ALLOWED_OVERRIDE_FIELDS,
    EventChangeHistoryEntry,
    EventManualOverride,
    EventOverrideClearResult,
    EventOverrideUpdateResult,
    FieldProvenance,
    OverrideHistoryAction,
    OverrideValueKind,
    format_override_value,
    is_allowed_override_field,
    parse_override_value,
    value_kind_for,
)
from livelead.domain.identity import Role
from livelead.infrastructure.db.models import EventRow
from livelead.infrastructure.db.repositories.event_overrides import (
    EventChangeHistoryRepository,
    EventManualOverrideRepository,
)
from livelead.infrastructure.db.repositories.events import EventRepository

logger = logging.getLogger("livelead.event_overrides")


class EventOverrideError(ValueError):
    """Caller-facing validation failure for the override surface.

    Routes convert this to a 400 or 422 response. The message is
    safe to surface to the user.
    """


class EventOverrideDenied(PermissionError):
    """Caller-facing authorization failure.

    Routes convert this to a 403 response. A denied edit must still
    emit a ``denied`` audit row so governance can review attempts.
    """


@dataclass(frozen=True, slots=True)
class _FieldWrite:
    field: str
    value: str
    note: str
    prior_effective: str
    prior_canonical: str
    prior_override: str | None
    kind: OverrideValueKind


# ----------------------------------------------------------------------
# Authorization
# ----------------------------------------------------------------------
_EDIT_ROLES: frozenset[Role] = frozenset(
    {Role.OWNER, Role.ADMIN, Role.ANALYST}
)


def can_edit_canonical_event(role: Role | None) -> bool:
    return role in _EDIT_ROLES


# ----------------------------------------------------------------------
# Service
# ----------------------------------------------------------------------
class EventOverrideService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = EventRepository(session)
        self._overrides = EventManualOverrideRepository(session)
        self._history = EventChangeHistoryRepository(session)
        self._audit = AuditService(session)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    async def list_history(
        self,
        organization_id: UUID,
        event_id: UUID,
        *,
        limit: int = 100,
    ) -> list[EventChangeHistoryEntry]:
        event = await self._events.get(event_id, organization_id)
        if not event:
            raise EventOverrideError("event not found")
        return await self._history.list_for_event(organization_id, event_id, limit=limit)

    async def list_overrides(
        self, organization_id: UUID, event_id: UUID
    ) -> list[EventManualOverride]:
        return await self._overrides.list_for_event(organization_id, event_id)

    async def list_protected_fields(
        self, organization_id: UUID, event_id: UUID
    ) -> set[str]:
        return await self._overrides.list_protected_fields(organization_id, event_id)

    async def project_field_provenance(
        self, organization_id: UUID, event_id: UUID
    ) -> list[FieldProvenance]:
        """Build the per-field provenance view for event detail.

        Only the allowlisted fields appear in the projection. The
        projection is stable: callers can rely on the same set of
        fields for the same event.
        """

        overrides = await self._overrides.list_for_event(organization_id, event_id)
        override_by_field = {o.field: o for o in overrides}
        event = await self._events.get(event_id, organization_id)
        if not event:
            return []
        out: list[FieldProvenance] = []
        for field in sorted(ALLOWED_OVERRIDE_FIELDS):
            source_value = _read_canonical_field(event, field)
            override = override_by_field.get(field)
            if override is not None:
                out.append(
                    FieldProvenance(
                        field=field,
                        effective_value=format_override_value(field, override.override_value),
                        source_value=format_override_value(field, override.source_backed_value),
                        is_overridden=True,
                        actor_id=override.actor_id,
                        actor_role=override.actor_role,
                        updated_at=override.updated_at.isoformat().replace("+00:00", "Z"),
                    )
                )
            else:
                out.append(
                    FieldProvenance(
                        field=field,
                        effective_value=format_override_value(field, source_value),
                        source_value=format_override_value(field, source_value),
                        is_overridden=False,
                    )
                )
        return out

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------
    async def update_event_fields(
        self,
        *,
        organization_id: UUID,
        actor_id: str,
        actor_role: Role,
        event_id: UUID,
        updates: dict[str, Any],
        request_id: str = "",
        reason: str = "",
    ) -> EventOverrideUpdateResult:
        """Apply one or more manual-override writes to a canonical event.

        Each field in ``updates`` is validated against the allowlist
        and the value kind. The canonical event row is updated in
        the same transaction as the override row so a reviewer
        never sees a half-applied edit. The function returns the
        history rows written for this call so the route can render
        a tight response.
        """

        if not updates:
            raise EventOverrideError("no fields provided")
        if not can_edit_canonical_event(actor_role):
            await self._emit_audit(
                action=AuditAction.EVENT_OVERRIDE_DENIED,
                organization_id=organization_id,
                actor_id=actor_id,
                actor_role=actor_role,
                event_id=event_id,
                field=",".join(sorted(updates.keys())),
                outcome=AuditOutcome.DENIED,
                request_id=request_id,
                metadata={"reason": "role cannot edit canonical events"},
            )
            raise EventOverrideDenied(
                "this role cannot edit canonical events"
            )

        event_row = await self._events.get_row(event_id, organization_id)
        if not event_row:
            raise EventOverrideError("event not found")

        prepared: list[_FieldWrite] = []
        skipped_reasons: list[tuple[str, str]] = []
        for field, raw in updates.items():
            if not is_allowed_override_field(field):
                reason = f"unsupported field: {field}"
                skipped_reasons.append((str(field), reason))
                await self._record_field_skipped(
                    organization_id=organization_id,
                    event_id=event_id,
                    field=str(field),
                    actor_id=actor_id,
                    actor_role=actor_role,
                    reason=reason,
                )
                continue
            try:
                normalized = parse_override_value(field, raw)
            except ValueError as exc:
                skipped_reasons.append((field, str(exc)))
                await self._record_field_skipped(
                    organization_id=organization_id,
                    event_id=event_id,
                    field=field,
                    actor_id=actor_id,
                    actor_role=actor_role,
                    reason=str(exc),
                )
                continue
            if normalized == "":
                # Treat empty payloads as clear-override. The
                # caller can use the explicit clear endpoint when
                # they want the history record to be unambiguous.
                reason = "empty override payload; use clear endpoint"
                skipped_reasons.append((field, reason))
                await self._record_field_skipped(
                    organization_id=organization_id,
                    event_id=event_id,
                    field=field,
                    actor_id=actor_id,
                    actor_role=actor_role,
                    reason=reason,
                )
                continue
            prior_canonical = _read_canonical_field(event_row, field)
            prior_override = await self._overrides.get(organization_id, event_id, field)
            prior_effective = (
                prior_override.override_value
                if prior_override is not None
                else prior_canonical
            )
            prepared.append(
                _FieldWrite(
                    field=field,
                    value=normalized,
                    note=reason[:500],
                    prior_effective=prior_effective,
                    prior_canonical=prior_canonical,
                    prior_override=prior_override.override_value
                    if prior_override
                    else None,
                    kind=value_kind_for(field),
                )
            )

        if not prepared:
            # Build a descriptive error so the caller can see which
            # fields were rejected. The first skipped reason
            # is included verbatim so the UI can show the
            # validation message.
            skipped_summary = ", ".join(
                f"{f}: {r}" for f, r in skipped_reasons[:3]
            )
            raise EventOverrideError(
                f"no valid fields provided ({skipped_summary or 'all fields invalid'})"
            )

        # Persist override rows and history. The canonical event row
        # is updated for each prepared write so the event detail
        # response sees the new value immediately.
        applied: list[EventManualOverride] = []
        history: list[EventChangeHistoryEntry] = []
        for write in prepared:
            source_value = write.prior_canonical
            override = await self._overrides.upsert(
                organization_id=organization_id,
                event_id=event_id,
                field=write.field,
                source_backed_value=source_value,
                override_value=write.value,
                value_kind=write.kind,
                note=write.note,
                actor_id=actor_id,
                actor_role=actor_role.value,
            )
            _write_canonical_field(event_row, write.field, write.value)
            entry = await self._history.append(
                organization_id=organization_id,
                event_id=event_id,
                action=OverrideHistoryAction.UPSERTED,
                field=write.field,
                value_kind=write.kind,
                prior_value=write.prior_effective,
                new_value=write.value,
                source_backed_value=source_value,
                actor_id=actor_id,
                actor_role=actor_role.value,
                reason=write.note,
            )
            applied.append(override)
            history.append(entry)
            await self._emit_audit(
                action=AuditAction.EVENT_OVERRIDE_UPSERTED,
                organization_id=organization_id,
                actor_id=actor_id,
                actor_role=actor_role,
                event_id=event_id,
                field=write.field,
                outcome=AuditOutcome.SUCCEEDED,
                request_id=request_id,
                metadata={
                    "field": write.field,
                    "prior_effective": write.prior_effective,
                    "new_value": write.value,
                },
            )
        self._session.add(event_row)
        await self._session.flush()
        return EventOverrideUpdateResult(
            event_id=event_id,
            applied_fields=[w.field for w in prepared],
            skipped_fields=[],
            history=history,
            overrides=applied,
        )

    async def clear_override(
        self,
        *,
        organization_id: UUID,
        actor_id: str,
        actor_role: Role,
        event_id: UUID,
        field: str,
        request_id: str = "",
        reason: str = "",
    ) -> EventOverrideClearResult:
        if not can_edit_canonical_event(actor_role):
            await self._emit_audit(
                action=AuditAction.EVENT_OVERRIDE_DENIED,
                organization_id=organization_id,
                actor_id=actor_id,
                actor_role=actor_role,
                event_id=event_id,
                field=field,
                outcome=AuditOutcome.DENIED,
                request_id=request_id,
                metadata={"reason": "role cannot clear overrides"},
            )
            raise EventOverrideDenied("this role cannot clear overrides")
        if not is_allowed_override_field(field):
            raise EventOverrideError(f"unsupported field: {field}")

        override = await self._overrides.get(organization_id, event_id, field)
        if not override:
            raise EventOverrideError("override not found")

        event_row = await self._events.get_row(event_id, organization_id)
        if not event_row:
            raise EventOverrideError("event not found")
        restored = override.source_backed_value
        _write_canonical_field(event_row, field, restored)
        self._session.add(event_row)
        await self._overrides.delete(organization_id, event_id, field)
        entry = await self._history.append(
            organization_id=organization_id,
            event_id=event_id,
            action=OverrideHistoryAction.CLEARED,
            field=field,
            value_kind=override.value_kind,
            prior_value=override.override_value,
            new_value=restored,
            source_backed_value=override.source_backed_value,
            actor_id=actor_id,
            actor_role=actor_role.value,
            reason=reason[:500],
        )
        await self._emit_audit(
            action=AuditAction.EVENT_OVERRIDE_CLEARED,
            organization_id=organization_id,
            actor_id=actor_id,
            actor_role=actor_role,
            event_id=event_id,
            field=field,
            outcome=AuditOutcome.SUCCEEDED,
            request_id=request_id,
            metadata={
                "field": field,
                "restored_value": restored,
            },
        )
        await self._session.flush()
        return EventOverrideClearResult(
            event_id=event_id,
            field=field,
            restored_value=format_override_value(field, restored),
            history=[entry],
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    async def _record_field_skipped(
        self,
        *,
        organization_id: UUID,
        event_id: UUID,
        field: str,
        actor_id: str,
        actor_role: Role,
        reason: str,
    ) -> None:
        await self._history.append(
            organization_id=organization_id,
            event_id=event_id,
            action=OverrideHistoryAction.DENIED,
            field=field,
            value_kind=value_kind_for(field) if is_allowed_override_field(field) else OverrideValueKind.TEXT,
            prior_value="",
            new_value="",
            source_backed_value="",
            actor_id=actor_id,
            actor_role=actor_role.value,
            reason=reason[:500],
        )
        logger.info(
            "event_override_skipped org=%s event=%s field=%s actor=%s reason=%s",
            organization_id,
            event_id,
            field,
            actor_id,
            reason,
        )

    async def _emit_audit(
        self,
        *,
        action: AuditAction,
        organization_id: UUID,
        actor_id: str,
        actor_role: Role,
        event_id: UUID,
        field: str,
        outcome: AuditOutcome,
        request_id: str,
        metadata: dict,
    ) -> None:
        try:
            target = AuditTarget(
                target_type=AuditTargetType.EVENT,
                target_id=str(event_id),
                display=f"event {event_id} field {field}",
            )
            await self._audit.emit(
                organization_id=organization_id,
                actor=make_actor_from_role(actor_role.value, actor_id or actor_role.value),
                action=action,
                target=target,
                outcome=outcome,
                context=make_context(
                    request_id=request_id,
                    workflow="event_overrides",
                ),
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("event_override_audit_failed err=%s", exc)


# ----------------------------------------------------------------------
# Field access helpers
# ----------------------------------------------------------------------
def _read_canonical_field(event: Any, field: str) -> str:
    """Return the canonical event row's stored value for ``field``.

    The function accepts both a domain ``CanonicalEvent`` and an
    ORM ``EventRow``; the read path uses the same attribute names.
    """

    if field == "starts_at":
        value = getattr(event, "starts_at", None)
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)
    value = getattr(event, field, "")
    return "" if value is None else str(value)


def _write_canonical_field(event_row: EventRow, field: str, stored: str) -> None:
    """Apply a stored override string to the canonical event row.

    The stored string is the same shape that
    ``parse_override_value`` produces and that the row's column
    expects, so a direct assignment is safe.
    """

    if field == "starts_at":
        if stored == "":
            event_row.starts_at = None
            return
        candidate = stored
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        parsed = datetime.fromisoformat(candidate)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        event_row.starts_at = parsed
        return
    setattr(event_row, field, stored)


__all__ = [
    "EventOverrideClearResult",
    "EventOverrideDenied",
    "EventOverrideError",
    "EventOverrideService",
    "EventOverrideUpdateResult",
    "can_edit_canonical_event",
]
